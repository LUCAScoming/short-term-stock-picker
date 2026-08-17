#!/usr/bin/env python3
"""
短线选股脚本 - 技术面+资金面综合筛选 (优化版)
"""

import sys
import io
import json as _json
import time
import random as _random
import urllib.request as _urllib_req
import urllib.parse as _urllib_parse
from datetime import datetime, timedelta
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
import argparse

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

import akshare as ak
import pandas as pd


# ---- monkey-patch: 用 urllib 替代 requests (绕过本机代理问题) ----
class _UrllibResponse:
    def __init__(self, resp):
        self._resp = resp
        self._body = resp.read()
        self.status_code = resp.getcode()
        self.text = self._body.decode('utf-8', errors='replace')

    def json(self):
        return _json.loads(self.text)

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f'HTTP {self.status_code}')


def _patched_request_with_retry(url, params=None, timeout=15,
                                max_retries=3, base_delay=1.0,
                                random_delay_range=(0.5, 1.5)):
    qs = _urllib_parse.urlencode(params) if params else ''
    full_url = f"{url}?{qs}" if qs else url
    last_exc = None
    for attempt in range(max_retries):
        try:
            req = _urllib_req.Request(full_url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            with _urllib_req.urlopen(req, timeout=timeout) as resp:
                return _UrllibResponse(resp)
        except Exception as e:
            last_exc = e
            if attempt < max_retries - 1:
                time.sleep(base_delay * (2 ** attempt) + _random.uniform(*random_delay_range))
    raise last_exc


# 替换 akshare 内部所有引用点
import akshare.utils.func  # noqa: E402
akshare.utils.func.request_with_retry = _patched_request_with_retry
akshare.utils.request.request_with_retry = _patched_request_with_retry
# ---- end monkey-patch ----

# ---- monkey-patch: 给 requests.get 注入默认超时 ----
# akshare 的 stock_zh_a_daily / stock_zt_pool_em 内部直接 requests.get(url) 且不传 timeout，
# 一旦网络慢/挂起会永久阻塞。这里给 get 补默认超时，避免脚本卡死。
import requests as _requests

_orig_requests_get = _requests.get
_orig_session_get = _requests.Session.get


def _patched_requests_get(url, params=None, **kwargs):
    kwargs.setdefault('timeout', 15)
    return _orig_requests_get(url, params=params, **kwargs)


def _patched_session_get(self, url, **kwargs):
    kwargs.setdefault('timeout', 15)
    return _orig_session_get(self, url, **kwargs)


_requests.get = _patched_requests_get
_requests.Session.get = _patched_session_get
# ---- end requests monkey-patch ----

MARKET_CAP_MIN = 5000000000   # 50亿
MARKET_CAP_MAX = 20000000000  # 200亿


def get_trade_dates(n=25):
    dates = []
    d = datetime.now()
    while len(dates) < n:
        if d.weekday() < 5:
            dates.append(d.strftime('%Y%m%d'))
        d -= timedelta(days=1)
    return dates

def get_all_limit_up_stocks(trade_dates):
    """获取近20日涨停股，同时计算首板距今天数、连板天数"""
    all_data = {}
    recent20 = trade_dates[:20]

    print(f"📊 检查近20个交易日涨停情况...")

    for i, date in enumerate(recent20):
        try:
            df = ak.stock_zt_pool_em(date=date)
            if df is not None and len(df) > 0:
                for _, row in df.iterrows():
                    code = str(row['代码']).zfill(6)
                    name = row['名称']

                    if code not in all_data:
                        all_data[code] = {
                            'name': name,
                            'count': 0,
                            'dates': [],
                        }

                    all_data[code]['count'] += 1
                    all_data[code]['dates'].append(date)

                    if all_data[code]['count'] == 1:
                        circ_mv = row.get('流通市值', 0)
                        total_mv = row.get('总市值', 0)
                        all_data[code]['market_cap'] = circ_mv if circ_mv > 0 else total_mv
                        all_data[code]['industry'] = row.get('所属行业', '')

            if (i + 1) % 5 == 0:
                print(f"  已检查 {i+1}/20 个交易日... 累计 {len(all_data)} 只")
            time.sleep(0.2)
        except Exception:
            continue

    # 计算每只股票的首次涨停距今天数 & 连板天数
    for code, info in all_data.items():
        dates_set = set(info['dates'])

        # 首次涨停距今天数（recent20[0]=最近, recent20[19]=最早）
        earliest = min(dates_set)
        info['first_days_ago'] = recent20.index(earliest)

        # 连板天数：从最近一个涨停日往前数连续天数
        consecutive = 0
        most_recent = None
        for d in recent20:
            if d in dates_set:
                most_recent = d
                break
        if most_recent:
            start = recent20.index(most_recent)
            for j in range(start, min(start + 10, 20)):
                if recent20[j] in dates_set:
                    consecutive += 1
                else:
                    break
        info['consecutive'] = consecutive

        # 涨停时间衰减得分：近期涨停权重高，远期指数衰减（问题8修复）
        # recent20[0]=最近交易日，距今天数越大权重越低，0.9^days_ago
        decay_factor = 0.9
        decay_score = 0.0
        for d in dates_set:
            days_ago = recent20.index(d)
            decay_score += (decay_factor ** days_ago) * 10
        info['limit_up_decay_score'] = round(decay_score, 1)

    print(f"📈 近20日共有 {len(all_data)} 只股票涨停过")
    return all_data

def get_stock_hist_data(code):
    """获取股票历史数据，10秒超时防止单票卡死"""
    try:
        if code.startswith(('600', '601', '603', '605', '688')):
            symbol = f'sh{code}'
        else:
            symbol = f'sz{code}'

        end_date = (datetime.now() + timedelta(days=1)).strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=40)).strftime('%Y%m%d')

        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(
            ak.stock_zh_a_daily,
            symbol=symbol, start_date=start_date, end_date=end_date
        )
        try:
            df = future.result(timeout=10)
        except (FutureTimeout, Exception):
            return None
        finally:
            # 关键：不能用 `with` 写法。with 退出时会 shutdown(wait=True)，
            # 阻塞等待卡死的线程，导致超时失效。这里 wait=False 直接放弃等待。
            executor.shutdown(wait=False)

        if df is None or len(df) < 20:
            return None

        return df.tail(25)
    except (FutureTimeout, Exception):
        return None

def analyze_stock(code, info):
    """分析单只股票"""
    name = info['name']
    
    # 剔除ST
    if 'ST' in str(name) or '*ST' in str(name) or '退' in str(name):
        return None
    
    # 板块过滤
    if not (code.startswith(('600', '601', '603', '605', '000', '001', '300', '688'))):
        return None
    
    # 市值过滤
    market_cap = info.get('market_cap', 0)
    if market_cap == 0 or market_cap < MARKET_CAP_MIN or market_cap > MARKET_CAP_MAX:
        return None
    
    # 获取历史数据
    df_hist = get_stock_hist_data(code)
    if df_hist is None:
        return None
    
    latest = df_hist.iloc[-1]
    close = latest['close']
    
    # 计算均线
    ma5 = df_hist['close'].rolling(5).mean().iloc[-1]
    ma10 = df_hist['close'].rolling(10).mean().iloc[-1]
    ma20 = df_hist['close'].rolling(20).mean().iloc[-1]
    
    # 均线分级评分（问题11修复：替代刚性淘汰，保留破位淘汰）
    if close >= ma5 and close >= ma10 and close >= ma20 and ma5 > ma10 > ma20:
        ma_score = 30  # 完美多头
    elif close >= ma10 and ma10 > ma20:
        ma_score = 20  # 接近多头，回调买点
    elif close >= ma20:
        ma_score = 10  # 弱势站稳
    else:
        return None  # 跌破20日线，趋势破坏直接淘汰
    
    # 成交量分析
    vol_last5 = df_hist.tail(5)['volume'].mean()
    vol_prev5 = df_hist.tail(10)['volume'].iloc[:-5].mean()
    vol_ratio = vol_last5 / vol_prev5 if vol_prev5 > 0 else 1
    
    # 换手率
    turnover_rate = df_hist.tail(3)['turnover'].mean() * 100
    if turnover_rate > 10 or turnover_rate < 5:
        return None
    
    # 当前涨跌幅
    prev_close = df_hist.iloc[-2]['close']
    change_pct = (close - prev_close) / prev_close * 100 if prev_close > 0 else 0

    # 3日涨跌幅
    recent3 = df_hist.tail(3)
    change_3d = (recent3.iloc[-1]['close'] - recent3.iloc[0]['close']) / recent3.iloc[0]['close'] * 100

    # 20日涨跌幅（过热检测）
    if len(df_hist) >= 20:
        change_20d = (df_hist.iloc[-1]['close'] - df_hist.iloc[0]['close']) / df_hist.iloc[0]['close'] * 100
    else:
        change_20d = change_3d
    # 20日涨幅 > 35% 追高风险，直接排除
    if change_20d > 35:
        return None

    # ---- 评分计算 ----
    limit_up_count = info['count']
    first_days_ago = info.get('first_days_ago', 10)
    consecutive = info.get('consecutive', 0)
    limit_up_decay_score = info.get('limit_up_decay_score', limit_up_count * 10)  # 问题8：时间衰减得分

    # 技术评分（问题1修复：去掉量比分档，量比仅在综合分 vol_ratio*10 计一次，避免双重计算）
    tech_score = ma_score  # 均线分级基础分（问题11）
    if change_3d > 0 and vol_ratio >= 1.2:
        tech_score += 10  # 量价齐升

    # 换手率加分（问题2修复：与过滤区间5-10对齐，高位换手惩罚）
    if 5 <= turnover_rate <= 8:
        tech_score += 5
    elif 8 < turnover_rate <= 10:
        tech_score -= 5  # 高位换手，出货嫌疑

    # 首板新鲜度加分（问题9修复：今日首板0天降权，1-3天回调买点最佳）
    if first_days_ago == 0:
        recency_bonus = 5   # 今日涨停，次日追高风险
    elif first_days_ago <= 3:
        recency_bonus = 15  # 1-3天，回调买点最佳
    elif first_days_ago <= 7:
        recency_bonus = 8
    else:
        recency_bonus = 0

    # 连板加分（问题3修复：分段计分，≥4连板转惩罚，规避高位接盘）
    if consecutive <= 1:
        consecutive_bonus = 0
    elif consecutive == 2:
        consecutive_bonus = 10
    elif consecutive == 3:
        consecutive_bonus = 15
    else:
        consecutive_bonus = -15  # ≥4连板，高位风险

    # 过热惩罚（20日涨幅 25%-35% 之间）
    overheat_penalty = -10 if change_20d > 25 else 0

    # 综合评分（问题8修复：涨停次数改用时间衰减得分，避免远期涨停等权）
    total_score = (limit_up_decay_score
                   + tech_score
                   + vol_ratio * 10
                   + recency_bonus
                   + consecutive_bonus
                   + overheat_penalty)

    board = '科创板' if code.startswith('688') else ('创业板' if code.startswith('300') else ('深交所' if code.startswith(('000', '001')) else '上交所'))

    return {
        '代码': code,
        '名称': name,
        '综合评分': round(total_score, 1),
        '涨停次数(近20日)': limit_up_count,
        '涨停衰减得分': limit_up_decay_score,
        '连板天数': consecutive,
        '首次涨停距今(天)': first_days_ago,
        '流通市值(亿)': round(market_cap / 100000000, 2),
        '最新价': round(close, 2),
        'MA5': round(ma5, 2),
        'MA10': round(ma10, 2),
        'MA20': round(ma20, 2),
        '换手率': round(turnover_rate, 2),
        '量比(近5日)': round(vol_ratio, 2),
        '当前涨跌幅': f'{change_pct:+.2f}%',
        '3日涨跌幅': f'{change_3d:+.2f}%',
        '20日涨跌幅': f'{change_20d:+.2f}%',
        '技术评分': tech_score,
        '板块': board,
        '所属行业': info.get('industry', '')
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', choices=['original', '3d'], default='original',
                        help='scoring model: original (default) or 3d (3-dimension)')
    args = parser.parse_args()
    use_3d = args.model == '3d'

    print("=" * 70)
    print("📈 短线强势股筛选 (技术面+资金面综合)")
    print("=" * 70)
    print("筛选条件：")
    print("  1. A股/深证/创业板/科创板")
    print("  2. 剔除ST及退市类")
    print("  3. 市值 50亿-200亿")
    print("  4. 近20交易日有涨停")
    print("  5. 均线分级评分(完美多头30/接近多头20/弱势10/破ma20淘汰)")
    print("  6. 换手率合理区间 (5%-10%)")
    print("  7. 成交量放量")
    print("  8. 20日涨幅 ≤ 35%（防追高）")
    print("")
    if use_3d:
        print("评分权重：")
        print("  涨停衰减得分(0.9^天数×10) + 量比×10 + 技术评分 + 首板新鲜度 + 连板分段 + 板块热度(0-30) - 过热惩罚")
        print("连板分段: 2板+10/3板+15/≥4板-15 | 首板: 今日+5/1-3天+15/4-7天+8 | 换手: 5-8%+5/8-10%-5")
        print("板块热度 = 涨停集中度(0-15) + 龙头高度(0-10) + 趋势加速度(0-5)")
    else:
        print("评分权重：")
        print("  涨停衰减得分(0.9^天数×10) + 量比×10 + 技术评分 + 首板新鲜度 + 连板分段 + 板块共振 - 过热惩罚")
        print("连板分段: 2板+10/3板+15/≥4板-15 | 首板: 今日+5/1-3天+15/4-7天+8 | 换手: 5-8%+5/8-10%-5")
    print("=" * 70)
    
    trade_dates = get_trade_dates(25)
    all_stocks = get_all_limit_up_stocks(trade_dates)
    
    if not all_stocks:
        return
    
    results = []
    analyzed = 0
    
    print(f"\n🔍 开始技术面分析...")
    
    for code, info in all_stocks.items():
        analyzed += 1
        result = analyze_stock(code, info)
        if result:
            results.append(result)
            print(f"  ✅ {code} {info['name']} - 评分: {result['综合评分']}")
        
        if analyzed % 20 == 0:
            print(f"  已分析 {analyzed}/{len(all_stocks)} 只... 符合条件: {len(results)}")
        
        time.sleep(0.25)  # 避免请求过快
    
    if not results:
        print("\n⚠️ 未找到符合条件的股票")
        return

    if use_3d:
        # ---- 板块热度评价（三维度：涨停集中度 + 龙头高度 + 趋势加速度）----
        # 行业活跃股数 = 近20日出现过涨停的股票数，作为行业规模的代理指标
        industry_universe = Counter()
        for code, info in all_stocks.items():
            ind = info.get('industry', '')
            if ind:
                industry_universe[ind] += 1

        recent3 = trade_dates[:3]
        day_lu = {d: Counter() for d in recent3}
        leader_board = {}

        for code, info in all_stocks.items():
            ind = info.get('industry', '')
            if not ind:
                continue
            for d in recent3:
                if d in info['dates']:
                    day_lu[d][ind] += 1
            if info['consecutive'] > leader_board.get(ind, 0):
                leader_board[ind] = info['consecutive']

        d0, d1, d2 = recent3[0], recent3[1], recent3[2]

        for r in results:
            ind = r.get('所属行业', '')
            bonus = 0
            r['板块涨停比'] = '--'
            r['板块趋势'] = '--'

            if ind:
                lu_today = day_lu[d0].get(ind, 0)
                total_active = industry_universe.get(ind, 1)
                if lu_today > 0:
                    concentration = lu_today / max(total_active, 1)
                    ratio_score = round(min(15, concentration * 30))
                    r['板块涨停比'] = f'{lu_today}/{total_active}'
                else:
                    ratio_score = 0

                leader = leader_board.get(ind, 1)
                leader_score = min(10, max(0, leader - 1) * 3)

                c0 = day_lu[d0].get(ind, 0)
                c1 = day_lu[d1].get(ind, 0)
                c2 = day_lu[d2].get(ind, 0)
                if c0 >= c1 >= c2 and c0 > 0:
                    trend_score = min(5, (c0 - c2) * 2)
                    r['板块趋势'] = '↑加速'
                elif c0 > 0 and c0 >= c1:
                    trend_score = 2
                    r['板块趋势'] = '→平稳'
                elif c0 > 0:
                    trend_score = 0
                    r['板块趋势'] = '↓减速'
                else:
                    trend_score = 0

                bonus = ratio_score + leader_score + trend_score

            r['板块热度加分'] = bonus
            r['综合评分'] = round(r['综合评分'] + bonus, 1)
    else:
        # 原始板块热度：同行业 >= 3 只入选 +10，>= 2 只 +5
        industry_counter = {}
        for r in results:
            ind = r.get('所属行业', '')
            if ind:
                industry_counter[ind] = industry_counter.get(ind, 0) + 1
        for r in results:
            ind = r.get('所属行业', '')
            n = industry_counter.get(ind, 0)
            bonus = 10 if n >= 3 else (5 if n >= 2 else 0)
            r['板块热度加分'] = bonus
            r['综合评分'] = round(r['综合评分'] + bonus, 1)

    df_results = pd.DataFrame(results)
    df_results = df_results.sort_values('综合评分', ascending=False)

    print(f"\n✅ 筛选完成！找到 {len(df_results)} 只短线强势股")
    print("=" * 140)

    if use_3d:
        display_cols = ['代码', '名称', '涨停次数(近20日)', '涨停衰减得分', '连板天数', '首次涨停距今(天)',
                        '流通市值(亿)', '最新价', '当前涨跌幅', '量比(近5日)',
                        '3日涨跌幅', '20日涨跌幅', '板块涨停比', '板块趋势', '板块热度加分', '综合评分', '所属行业']
    else:
        display_cols = ['代码', '名称', '涨停次数(近20日)', '涨停衰减得分', '连板天数', '首次涨停距今(天)',
                        '流通市值(亿)', '最新价', '当前涨跌幅', '量比(近5日)',
                        '3日涨跌幅', '20日涨跌幅', '板块热度加分', '综合评分', '所属行业']
    print(df_results[display_cols].head(50).to_string(index=False))
    
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M')
    suffix = '_3Model' if use_3d else ''
    output_path = f'{timestamp}-result{suffix}.csv'
    df_results.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"\n📁 结果已保存到: {output_path}")

if __name__ == "__main__":
    main()