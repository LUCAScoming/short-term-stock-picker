# Short-Term Stock Picker

短线强势股筛选工具，基于 AKShare 开放数据，筛选 A 股短线强势标的。

## 项目结构

```
scripts/pick_stocks.py   # 核心选股脚本（涨停+技术面+资金面）
scripts/hot_sectors.py   # 热门放量板块筛选
server.py                # Web 管理界面（http://localhost:8080）
```

## 常用命令

```bash
python scripts/pick_stocks.py   # 命令行运行选股
python scripts/hot_sectors.py   # 命令行运行板块筛选
python server.py                # 启动 Web UI
```

## 注意事项

- commit message 使用中文
- Windows 终端编码问题：用 `sys.stdout.reconfigure(encoding='utf-8')`，不要用 `io.TextIOWrapper` 包裹（会造成双重缓冲）
- 本机 requests 库无法直连东方财富 push 服务器，需要 monkey-patch 替换为 urllib.request（见 `pick_stocks.py` 头部）
- 所有 `print` 用英文/数字，避免 emoji 在 subprocess 中 GBK 报错；如果要用 emoji，确保已 reconfigure stdout
