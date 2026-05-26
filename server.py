#!/usr/bin/env python3
"""
Short-Term Stock Picker Web UI
启动后访问 http://localhost:8080
"""

import sys
import io
import os
import json
import csv
import glob
import subprocess
import threading
import time
import re
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, unquote

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

ROOT = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.join(ROOT, 'scripts')
PORT = 8080

# ---- shared state ----
_state = {
    'proc': None,
    'status': 'idle',       # idle | running | done | error
    'message': '',
    'percent': 0,
    'output_lines': [],
    'csv_filename': '',
}
_lock = threading.Lock()


def _bump(percent, message):
    with _lock:
        _state['percent'] = percent
        _state['message'] = message
        _state['output_lines'].append(message)


def _run_script():
    try:
        _bump(1, '启动脚本...')

        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        env['PYTHONUNBUFFERED'] = '1'
        proc = subprocess.Popen(
            [sys.executable, os.path.join(SCRIPTS_DIR, 'pick_stocks.py')],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace',
            cwd=ROOT,
            env=env,
        )
        with _lock:
            _state['proc'] = proc

        for line in proc.stdout:
            line = line.strip()
            if not line:
                continue
            with _lock:
                _state['output_lines'].append(line)

            # 解析进度
            if '检查近20个交易日' in line:
                _bump(3, line)
            elif '已检查' in line and '交易日' in line:
                m = re.search(r'(\d+)/(\d+)', line)
                if m:
                    pct = 3 + int(m.group(1)) / int(m.group(2)) * 37
                    _bump(int(pct), line)
            elif '开始技术面' in line:
                _bump(42, line)
            elif '已分析' in line and '符合条件' in line:
                m = re.search(r'(\d+)/(\d+)', line)
                if m:
                    pct = 42 + int(m.group(1)) / int(m.group(2)) * 50
                    _bump(int(pct), line)
            elif '筛选完成' in line:
                _bump(93, line)
            elif '结果已保存到' in line:
                _bump(97, line)
                m = re.search(r'[\w\-]+\.csv', line)
                if m:
                    with _lock:
                        _state['csv_filename'] = m.group(0)

        proc.wait()
        if proc.returncode == 0:
            _bump(100, '完成')
            with _lock:
                _state['status'] = 'done'
        else:
            _bump(100, f'脚本异常退出 (code={proc.returncode})')
            with _lock:
                _state['status'] = 'error'

    except Exception as e:
        _bump(0, f'运行失败: {e}')
        with _lock:
            _state['status'] = 'error'
    finally:
        with _lock:
            _state['proc'] = None


# ---- HTTP Handler ----
class Handler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        pass  # 静默日志

    def _send_json(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html, code=200):
        body = html.encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path, ct):
        with open(path, 'rb') as f:
            body = f.read()
        self.send_response(200)
        self.send_header('Content-Type', ct)
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        p = urlparse(self.path)

        if p.path == '/' or p.path == '/index.html':
            self._send_html(HTML)
        elif p.path == '/api/progress':
            with _lock:
                self._send_json({
                    'status': _state['status'],
                    'percent': _state['percent'],
                    'message': _state['message'],
                    'output_lines': _state['output_lines'][-50:],
                    'csv_filename': _state['csv_filename'],
                })
        elif p.path == '/api/history':
            files = []
            for f in glob.glob(os.path.join(ROOT, '*-result.csv')):
                st = os.stat(f)
                files.append({
                    'name': os.path.basename(f),
                    'size': st.st_size,
                    'mtime': datetime.fromtimestamp(st.st_mtime).strftime('%Y-%m-%d %H:%M'),
                })
            files.sort(key=lambda x: x['mtime'], reverse=True)
            self._send_json(files)
        elif p.path.startswith('/api/csv/'):
            fname = unquote(p.path[len('/api/csv/'):])
            fpath = os.path.join(ROOT, fname)
            # 安全检查
            if not os.path.realpath(fpath).startswith(os.path.realpath(ROOT)):
                self._send_json({'error': 'invalid path'}, 403)
                return
            if not os.path.exists(fpath):
                self._send_json({'error': 'not found'}, 404)
                return
            try:
                rows = []
                with open(fpath, 'r', encoding='utf-8-sig') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        rows.append(row)
                self._send_json({'columns': list(rows[0].keys()) if rows else [], 'rows': rows})
            except Exception as e:
                self._send_json({'error': str(e)}, 500)
        else:
            self._send_json({'error': 'not found'}, 404)

    def do_POST(self):
        p = urlparse(self.path)
        if p.path == '/api/run':
            with _lock:
                if _state['status'] == 'running':
                    self._send_json({'error': '脚本正在运行中'}, 409)
                    return
                _state['status'] = 'running'
                _state['percent'] = 0
                _state['message'] = ''
                _state['output_lines'] = []
                _state['csv_filename'] = ''

            threading.Thread(target=_run_script, daemon=True).start()
            self._send_json({'status': 'started'})
        else:
            self._send_json({'error': 'not found'}, 404)


# ---- HTML ----
HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>短线强势股筛选</title>
<style>
:root {
  --bg: #0d1117;
  --surface: #161b22;
  --border: #30363d;
  --text: #e6edf3;
  --text-dim: #8b949e;
  --accent: #f0b429;
  --green: #2ea043;
  --red: #f85149;
  --blue: #58a6ff;
  --radius: 8px;
}
*{margin:0;padding:0;box-sizing:border-box;}
body{
  font-family: -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;
  background: var(--bg);
  color: var(--text);
  height: 100vh;
  overflow: hidden;
}
#app{
  display: grid;
  grid-template-columns: 300px 1fr;
  grid-template-rows: 48px 1fr;
  height: 100vh;
  gap: 1px;
  background: var(--border);
}
#header{
  grid-column: 1/-1;
  background: var(--surface);
  display:flex;
  align-items:center;
  padding:0 20px;
  gap:12px;
  border-bottom:1px solid var(--border);
}
#header h1{font-size:16px;font-weight:600;color:var(--accent);}
#header .sub{font-size:12px;color:var(--text-dim);}
.panel{
  background: var(--surface);
  display:flex;
  flex-direction:column;
  overflow:hidden;
}
.panel-header{
  padding:12px 16px;
  font-size:13px;
  font-weight:600;
  color:var(--text-dim);
  text-transform:uppercase;
  letter-spacing:.5px;
  border-bottom:1px solid var(--border);
  flex-shrink:0;
}
.panel-body{
  flex:1;
  overflow-y:auto;
  padding:12px;
}

#btn-run{
  width:100%;
  padding:10px 16px;
  border:none;
  border-radius:var(--radius);
  font-size:14px;
  font-weight:600;
  cursor:pointer;
  transition:all .15s;
  background: var(--accent);
  color: #0d1117;
}
#btn-run:hover{filter:brightness(1.1);}
#btn-run:disabled{opacity:.5;cursor:not-allowed;}
#btn-run.running{background:var(--red);}

#progress-wrap{margin-top:10px;}
#progress-bar{
  height:6px;
  background:var(--border);
  border-radius:3px;
  overflow:hidden;
}
#progress-fill{
  height:100%;
  background:var(--accent);
  width:0%;
  transition:width .3s;
}
#progress-text{
  font-size:12px;
  color:var(--text-dim);
  margin-top:6px;
  white-space:nowrap;
  overflow:hidden;
  text-overflow:ellipsis;
}

#history-list{list-style:none;max-height:190px;overflow-y:auto;}
#history-list li{
  padding:10px 12px;
  border-radius:6px;
  cursor:pointer;
  font-size:13px;
  display:flex;
  justify-content:space-between;
  align-items:center;
  transition:background .1s;
}
#history-list li:hover{background:rgba(255,255,255,.04);}
#history-list li.active{background:rgba(240,180,41,.1);border:1px solid var(--accent);}
#history-list li .fname{font-weight:500;}
#history-list li .ftime{font-size:11px;color:var(--text-dim);}

#table-wrap{overflow:auto;flex:1;}
table{
  width:100%;
  border-collapse:collapse;
  font-size:13px;
  white-space:nowrap;
}
thead{position:sticky;top:0;z-index:1;}
th{
  background:var(--surface);
  padding:8px 12px;
  text-align:left;
  font-weight:600;
  color:var(--text-dim);
  border-bottom:2px solid var(--border);
  position:sticky;
  top:0;
}
td{
  padding:6px 12px;
  border-bottom:1px solid rgba(48,54,61,.5);
}
tbody tr:hover{background:rgba(255,255,255,.03);}
.stock-name{
  color:var(--blue);
  cursor:pointer;
  font-weight:500;
}
.stock-name:hover{text-decoration:underline;color:var(--accent);}
.cell-up{color:var(--red);}
.cell-down{color:var(--green);}
.empty-state{
  display:flex;
  align-items:center;
  justify-content:center;
  height:100%;
  color:var(--text-dim);
  font-size:14px;
}

/* ---- modal / 弹窗 ---- */
#modal-overlay{
  display:none;
  position:fixed;
  inset:0;
  background:rgba(0,0,0,.7);
  z-index:1000;
  align-items:center;
  justify-content:center;
}
#modal-overlay.show{display:flex;}
#modal-box{
  background:var(--surface);
  border:1px solid var(--border);
  border-radius:12px;
  width:90vw;
  height:88vh;
  display:flex;
  flex-direction:column;
  overflow:hidden;
}
#modal-header{
  display:flex;
  align-items:center;
  justify-content:space-between;
  padding:12px 20px;
  border-bottom:1px solid var(--border);
  flex-shrink:0;
}
#modal-header h2{font-size:15px;color:var(--text);}
#modal-header .code{font-size:13px;color:var(--text-dim);margin-left:8px;}
#modal-close{
  background:none;border:none;
  color:var(--text-dim);
  font-size:22px;
  cursor:pointer;
  padding:4px 8px;
  border-radius:4px;
  line-height:1;
}
#modal-close:hover{color:var(--text);background:rgba(255,255,255,.08);}
#modal-iframe{
  flex:1;
  width:100%;
  border:none;
}
#iframe-fallback{
  display:none;
  flex:1;
  align-items:center;
  justify-content:center;
  flex-direction:column;
  gap:16px;
  color:var(--text-dim);
  padding:40px;
}
#iframe-fallback a{
  color:var(--accent);
  font-size:15px;
}

/* output log */
#output-log{
  font-family:"Cascadia Code","Fira Code",monospace;
  font-size:11px;
  color:var(--text-dim);
  max-height:200px;
  overflow-y:auto;
  margin-top:8px;
  white-space:pre-wrap;
  word-break:break-all;
  line-height:1.4;
}

::-webkit-scrollbar{width:6px;height:6px;}
::-webkit-scrollbar-track{background:transparent;}
::-webkit-scrollbar-thumb{background:var(--border);border-radius:3px;}
::-webkit-scrollbar-thumb:hover{background:#484f58;}
.placeholder{color:var(--text-dim);font-size:13px;text-align:center;padding:20px;}
</style>
</head>
<body>
<div id="app">

<div id="header">
  <h1>📈 短线强势股筛选</h1>
  <span class="sub">Short-Term Stock Picker</span>
</div>

<!-- Left Panel -->
<div class="panel" id="left-panel">
  <div class="panel-header">控制面板</div>
  <div class="panel-body">
    <button id="btn-run" onclick="runScript()">▶ 开始筛选</button>
    <div id="progress-wrap">
      <div id="progress-bar"><div id="progress-fill"></div></div>
      <div id="progress-text">就绪</div>
    </div>
    <div style="margin-top:16px;font-size:12px;color:var(--text-dim);">📂 历史记录</div>
    <ul id="history-list"></ul>
    <div id="output-log"></div>
  </div>
</div>

<!-- Center Panel -->
<div class="panel" id="center-panel">
  <div class="panel-header" id="table-title">数据预览</div>
  <div class="panel-body" style="padding:0;">
    <div id="table-wrap">
      <div class="empty-state" id="center-empty">← 点击历史记录中的 CSV 文件查看数据</div>
      <table id="data-table" style="display:none;"><thead></thead><tbody></tbody></table>
    </div>
  </div>
</div>

</div>

<!-- Modal Overlay -->
<div id="modal-overlay" onclick="closeModal(event)">
  <div id="modal-box" onclick="event.stopPropagation()">
    <div id="modal-header">
      <div>
        <h2 id="modal-title" style="display:inline;">—</h2>
        <span class="code" id="modal-code"></span>
      </div>
      <button id="modal-close" onclick="closeModal()">&times;</button>
    </div>
    <iframe id="modal-iframe" src="" sandbox="allow-scripts allow-same-origin allow-popups allow-forms"></iframe>
    <div id="iframe-fallback">
      <p>⚠️ 百度股市通暂不支持内嵌显示</p>
      <a id="fallback-link" href="#" target="_blank" rel="noopener">🔗 在新标签页中打开 →</a>
    </div>
  </div>
</div>

<script>
const $ = (s) => document.querySelector(s);
const $$ = (s) => document.querySelectorAll(s);

let pollTimer = null;

loadHistory();

// ---- Script Control ----
async function runScript(){
  const btn = $('#btn-run');
  btn.disabled = true;
  btn.textContent = '⏳ 启动中...';
  btn.classList.add('running');
  try {
    const r = await fetch('/api/run', {method:'POST'});
    if (!r.ok){ alert('脚本已在运行中'); btn.disabled=false; btn.textContent='▶ 开始筛选'; btn.classList.remove('running'); return; }
    startPolling();
  } catch(e){
    btn.disabled = false;
    btn.textContent = '▶ 开始筛选';
    btn.classList.remove('running');
  }
}

function startPolling(){
  if (pollTimer) clearInterval(pollTimer);
  pollTimer = setInterval(pollProgress, 500);
}

function stopPolling(){
  if (pollTimer){ clearInterval(pollTimer); pollTimer = null; }
}

async function pollProgress(){
  try {
    const r = await fetch('/api/progress');
    const s = await r.json();
    $('#progress-fill').style.width = s.percent + '%';
    $('#progress-text').textContent = s.percent + '% - ' + s.message;
    const log = $('#output-log');
    log.textContent = s.output_lines.slice(-15).join('\n');
    log.scrollTop = log.scrollHeight;
    const btn = $('#btn-run');
    if (s.status === 'running'){
      btn.textContent = '⏹ 运行中...';
      btn.disabled = true;
      btn.classList.add('running');
    } else {
      stopPolling();
      btn.textContent = '▶ 开始筛选';
      btn.disabled = false;
      btn.classList.remove('running');
      if (s.status === 'done'){
        $('#progress-text').textContent = '✅ 完成 - ' + (s.csv_filename || '');
      }
      loadHistory();
      if (s.csv_filename){
        setTimeout(() => loadCsv(s.csv_filename), 300);
      }
    }
  } catch(e){}
}

// ---- History ----
async function loadHistory(){
  try {
    const r = await fetch('/api/history');
    const files = await r.json();
    const ul = $('#history-list');
    ul.innerHTML = '';
    if (files.length === 0){
      ul.innerHTML = '<div class="placeholder">暂无历史记录</div>';
      return;
    }
    files.forEach(f => {
      const li = document.createElement('li');
      li.innerHTML = `<span class="fname">${f.name}</span><span class="ftime">${f.mtime}</span>`;
      li.onclick = () => {
        $$('#history-list li').forEach(el => el.classList.remove('active'));
        li.classList.add('active');
        loadCsv(f.name);
      };
      ul.appendChild(li);
    });
  } catch(e){}
}

// ---- CSV Data ----
async function loadCsv(filename){
  $('#table-title').textContent = '📋 ' + filename;
  $('#center-empty').style.display = 'none';
  try {
    const r = await fetch('/api/csv/' + encodeURIComponent(filename));
    const data = await r.json();
    if (data.error){ alert(data.error); return; }
    renderTable(data.columns, data.rows);
  } catch(e){ console.error(e); }
}

function renderTable(cols, rows){
  const table = $('#data-table');
  table.style.display = '';
  let thead = '<tr>';
  cols.forEach(c => { thead += `<th>${c}</th>`; });
  thead += '</tr>';
  table.querySelector('thead').innerHTML = thead;
  let tbody = '';
  rows.forEach(row => {
    tbody += '<tr>';
    cols.forEach(col => {
      let val = row[col] || '';
      let cls = '';
      if (col === '名称'){
        cls = 'stock-name';
        tbody += `<td class="${cls}" onclick="openStockModal('${esc(row['代码']||'')}','${esc(val)}')" title="点击查看百度股市通行情">${val}</td>`;
        return;
      }
      if (typeof val === 'string' && (val.startsWith('+') || val.includes('↑'))) cls = 'cell-up';
      else if (typeof val === 'string' && (val.startsWith('-') || val.includes('↓'))) cls = 'cell-down';
      if (typeof val === 'string' && val.length > 20) val = val.substring(0,18) + '..';
      tbody += `<td class="${cls}">${val}</td>`;
    });
    tbody += '</tr>';
  });
  table.querySelector('tbody').innerHTML = tbody;
}

function esc(s){ return (s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }

// ---- Modal / 弹窗 ----
function openStockModal(code, name){
  code = code.trim();
  if (!code) return;
  const url = 'https://gushitong.baidu.com/stock/ab-' + code;
  $('#modal-title').textContent = name;
  $('#modal-code').textContent = code;
  $('#modal-iframe').src = url;
  $('#modal-iframe').style.display = '';
  $('#iframe-fallback').style.display = 'none';
  $('#fallback-link').href = url;
  $('#modal-overlay').classList.add('show');
  // iframe load error fallback
  var timer = setTimeout(function(){
    $('#iframe-fallback').style.display = 'flex';
  }, 5000);
  $('#modal-iframe').onload = function(){ clearTimeout(timer); };
  $('#modal-iframe').onerror = function(){
    clearTimeout(timer);
    $('#modal-iframe').style.display = 'none';
    $('#iframe-fallback').style.display = 'flex';
  };
}

function closeModal(ev){
  if (ev && ev.target !== $('#modal-overlay')) return;
  $('#modal-overlay').classList.remove('show');
  $('#modal-iframe').src = '';
}

document.addEventListener('keydown', function(e){
  if (e.key === 'Escape') closeModal();
  if (e.key === 'r' && e.ctrlKey){ e.preventDefault(); runScript(); }
});
</script>
</body>
</html>"""


def main():
    sys.stdout.flush()
    import socket
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    lines = [
        "=" * 50,
        f"  Web UI 启动成功",
        f"  本地访问 : http://localhost:{PORT}",
        f"  局域网   : http://{local_ip}:{PORT}",
        f"  启动时间 : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"  按 Ctrl+C 停止",
        "=" * 50,
    ]
    for line in lines:
        print(line, flush=True)
    server = HTTPServer(('0.0.0.0', PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nWeb UI 已停止", flush=True)
        server.server_close()


if __name__ == '__main__':
    main()
