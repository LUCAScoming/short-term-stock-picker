#!/usr/bin/env python3
"""
热门放量板块筛选脚本
找到最近5个交易日中成交量明显放大且持续走强的热门板块（行业板块+概念板块）
"""

import sys
import io

# Windows 终端 UTF-8 支持
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import pandas as pd
from datetime import datetime, timedelta
import time
import json
import urllib.request

VOLUME_RATIO_MIN = 1.2      # 最低量比阈值
CHANGE_5D_MIN = 0           # 最低5日涨幅
TOP_N = 40                  # 输出前N个板块
SLEEP_S = 0.15              # API调用间隔

EASTMONEY_LIST_URL = "https://push2.eastmoney.com/api/qt/clist/get"
EASTMONEY_KLINE_URL = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


def _em_fetch(url, params, timeout=15):
    """用 urllib 请求东方财富 API，返回解析后的 JSON data"""
    qs = "&".join(f"{k}={v}" for k, v in params.items())
    full_url = f"{url}?{qs}"
    req = urllib.request.Request(full_url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return body.get("data")
    except Exception:
        return None


def get_all_boards():
    """获取所有行业板块和概念板块列表"""
    boards = []

    # 行业板块 (m:90+t:2)
    data = _em_fetch(EASTMONEY_LIST_URL, {
        "pn": "1", "pz": "500", "po": "1", "np": "1",
        "ut": "bd1d9ddb04089700cf9c27f6f7426281",
        "fltt": "2", "invt": "2", "fid": "f3",
        "fs": "m:90+t:2+f:!50",
        "fields": "f2,f12,f14",
    })
    if data and data.get("diff"):
        for item in data["diff"]:
            boards.append({
                "code": str(item.get("f12", "")),
                "name": str(item.get("f14", "")),
                "type": "行业",
            })
        print(f"  行业板块: {len(boards)} 个")
    else:
        print(f"  ⚠️ 行业板块获取失败")

    # 概念板块 (m:90+t:3)
    data = _em_fetch(EASTMONEY_LIST_URL, {
        "pn": "1", "pz": "1000", "po": "1", "np": "1",
        "ut": "bd1d9ddb04089700cf9c27f6f7426281",
        "fltt": "2", "invt": "2", "fid": "f12",
        "fs": "m:90+t:3+f:!50",
        "fields": "f2,f12,f14",
    })
    concept_start = len(boards)
    if data and data.get("diff"):
        for item in data["diff"]:
            boards.append({
                "code": str(item.get("f12", "")),
                "name": str(item.get("f14", "")),
                "type": "概念",
            })
        print(f"  概念板块: {len(boards) - concept_start} 个")
    else:
        print(f"  ⚠️ 概念板块获取失败")

    time.sleep(0.3)
    return boards


def get_board_hist(board_code, board_type):
    """获取板块历史日线数据，返回 DataFrame"""
    secid = f"90.{board_code}"
    data = _em_fetch(EASTMONEY_KLINE_URL, {
        "secid": secid,
        "klt": "101",            # 日K
        "fqt": "1",              # 前复权
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
        "lmt": "60",
        "ut": "bd1d9ddb04089700cf9c27f6f7426281",
    })
    if not data or not data.get("klines"):
        return None

    rows = []
    for line in data["klines"]:
        parts = line.split(",")
        if len(parts) >= 7:
            rows.append({
                "日期": parts[0],
                "开盘": float(parts[1]),
                "收盘": float(parts[2]),
                "最高": float(parts[3]),
                "最低": float(parts[4]),
                "成交量": float(parts[5]),
                "成交额": float(parts[6]),
            })

    if len(rows) < 11:
        return None

    return pd.DataFrame(rows).tail(30)


def analyze_board_volume(df):
    """分析板块量价，返回: 量比, 5日涨幅, 今日涨幅, 20日涨幅, 连续放量天数"""
    if df is None or len(df) < 11:
        return None

    close_col = "收盘"
    volume_col = "成交量"

    # 量比：近5日均量 / 前5日均量
    tail5_vol = df.tail(5)[volume_col].astype(float).mean()
    prev5_vol = df.tail(10).iloc[:-5][volume_col].astype(float).mean()
    vol_ratio = tail5_vol / prev5_vol if prev5_vol > 0 else 1.0

    # 价格涨跌幅
    closes = df[close_col].astype(float)
    latest = closes.iloc[-1]
    prev = closes.iloc[-2]
    change_today = (latest - prev) / prev * 100

    # 5日涨幅
    base_5d = closes.iloc[-6]
    change_5d = (latest - base_5d) / base_5d * 100

    # 20日涨幅
    if len(closes) >= 21:
        base_20d = closes.iloc[-21]
        change_20d = (latest - base_20d) / base_20d * 100
    else:
        change_20d = change_5d

    # 连续放量天数
    volumes = df[volume_col].astype(float).values
    consecutive = 0
    for i in range(len(volumes) - 1, 0, -1):
        if volumes[i] > volumes[i - 1]:
            consecutive += 1
        else:
            break

    return vol_ratio, change_5d, change_today, change_20d, consecutive


def main():
    print("=" * 70)
    print("🔥 热门放量板块筛选")
    print("=" * 70)
    print(f"筛选条件：")
    print(f"  1. 近5日量比 >= {VOLUME_RATIO_MIN}（放量）")
    print(f"  2. 5日涨幅 > {CHANGE_5D_MIN}%（上涨趋势）")
    print(f"  3. 行业板块 + 概念板块全覆盖")
    print("=" * 70)

    # 1. 获取板块列表
    print("\n📊 获取板块列表...")
    all_boards = get_all_boards()
    if not all_boards:
        print("❌ 未获取到任何板块数据")
        return

    n_industry = len([b for b in all_boards if b['type'] == '行业'])
    n_concept = len([b for b in all_boards if b['type'] == '概念'])
    print(f"📈 共 {len(all_boards)} 个板块（{n_industry} 行业 + {n_concept} 概念）")

    # 2. 逐个分析板块
    print(f"\n🔍 开始分析板块量价数据...")
    results = []

    for i, board in enumerate(all_boards):
        try:
            df = get_board_hist(board['code'], board['type'])
            if df is None:
                continue

            out = analyze_board_volume(df)
            if out is None:
                continue

            vol_ratio, change_5d, change_today, change_20d, consecutive = out

            # 过滤
            if vol_ratio < VOLUME_RATIO_MIN:
                continue
            if change_5d <= CHANGE_5D_MIN:
                continue

            # 综合评分: 量比(核心) + 涨幅 + 连放天数 + 中期趋势
            score = vol_ratio * 40 + change_5d * 2 + consecutive * 3 + change_20d * 0.5

            results.append({
                '板块代码': board['code'],
                '板块名称': board['name'],
                '类型': board['type'],
                '量比(近5日)': round(vol_ratio, 2),
                '5日涨跌幅(%)': round(change_5d, 2),
                '今日涨跌幅(%)': round(change_today, 2),
                '20日涨跌幅(%)': round(change_20d, 2),
                '连续放量天数': consecutive,
                '综合评分': round(score, 1),
            })

            if (i + 1) % 150 == 0:
                print(f"  已分析 {i+1}/{len(all_boards)} 个... 符合条件: {len(results)}")

            time.sleep(SLEEP_S)
        except Exception:
            continue

    # 3. 排序输出
    if not results:
        print("\n⚠️ 未找到符合条件的放量板块")
        return

    df_results = pd.DataFrame(results)
    df_results = df_results.sort_values('综合评分', ascending=False).reset_index(drop=True)

    print(f"\n✅ 筛选完成！共 {len(df_results)} 个放量热门板块\n")

    display_cols = ['板块名称', '板块代码', '类型', '量比(近5日)', '5日涨跌幅(%)',
                    '今日涨跌幅(%)', '20日涨跌幅(%)', '连续放量天数', '综合评分']

    # 综合 Top N
    print(f"{'='*110}")
    print(f"🏆 综合 TOP {min(TOP_N, len(df_results))} 放量热门板块")
    print(f"{'='*110}")
    print(df_results[display_cols].head(TOP_N).to_string(index=False))

    # 行业板块 Top 15
    df_industry = df_results[df_results['类型'] == '行业'].head(15)
    if len(df_industry) > 0:
        print(f"\n{'='*110}")
        print(f"🏭 行业板块 TOP 15")
        print(f"{'='*110}")
        print(df_industry[display_cols].to_string(index=False))

    # 概念板块 Top 15
    df_concept = df_results[df_results['类型'] == '概念'].head(15)
    if len(df_concept) > 0:
        print(f"\n{'='*110}")
        print(f"💡 概念板块 TOP 15")
        print(f"{'='*110}")
        print(df_concept[display_cols].to_string(index=False))

    # 类型统计
    print(f"\n{'='*110}")
    print("📊 板块类型分布统计")
    print(f"{'='*110}")
    type_stats = df_results.groupby('类型').agg(
        数量=('板块名称', 'count'),
        平均量比=('量比(近5日)', 'mean'),
        平均5日涨幅=('5日涨跌幅(%)', 'mean'),
        最高评分=('综合评分', 'max'),
    ).round(2)
    print(type_stats.to_string())

    # 4. 保存
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M')
    output_path = f'{timestamp}-hot-sectors.csv'
    df_results.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"\n📁 完整结果已保存到: {output_path}")


if __name__ == "__main__":
    main()
