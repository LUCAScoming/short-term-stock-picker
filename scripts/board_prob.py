#!/usr/bin/env python3
"""
二进三涨停概率预估 - Logistic 回归模型
读取 pick_stocks.py 输出的 CSV，对当天涨停的票追加"二进三概率"列
非涨停票显示 "--"

用法: python scripts/board_prob.py <input.csv> [--retrain]
"""

import sys
import os
import pickle
import warnings
from datetime import datetime, timedelta
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

import pandas as pd
import numpy as np
import akshare as ak
import time
import random as _random
import json as _json
import urllib.request as _urllib_req
import urllib.parse as _urllib_parse

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


import akshare.utils.func
akshare.utils.func.request_with_retry = _patched_request_with_retry
akshare.utils.request.request_with_retry = _patched_request_with_retry
# ---- end monkey-patch ----

from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

warnings.filterwarnings('ignore')

CACHE_DIR = Path(__file__).parent.parent / '.cache'
CACHE_DIR.mkdir(exist_ok=True)
MODEL_PATH = CACHE_DIR / 'board_prob_model.pkl'
TRAIN_DATA_PATH = CACHE_DIR / 'board_prob_train.csv'


def get_trade_dates(n):
    """近 N 个交易日"""
    dates = []
    d = datetime.now()
    while len(dates) < n:
        if d.weekday() < 5:
            dates.append(d.strftime('%Y%m%d'))
        d -= timedelta(days=1)
    return dates


def _parse_seal_time(val):
    """封板时间 -> 距 9:30 的分钟数，越早越强"""
    if val is None or pd.isna(val) or str(val).strip() in ('', 'nan'):
        return 240
    try:
        parts = str(val).strip().split(':')
        h, m = int(parts[0]), int(parts[1])
        return max(0, min((h - 9) * 60 + (m - 30), 240))
    except Exception:
        return 240


def _parse_board_stat(val):
    """涨停统计列: '2/3' -> board_count=2。返回连板估算值，无法解析返回 1"""
    if val is None or pd.isna(val) or str(val).strip() in ('', 'nan'):
        return 1
    try:
        s = str(val).strip()
        if '/' in s:
            return int(s.split('/')[0])
        return int(s)
    except Exception:
        return 1


def fetch_pools(dates, desc="limit-up data"):
    """批量拉取每日涨停池，返回 {date: DataFrame}"""
    pools = {}
    for i, date in enumerate(dates):
        try:
            df = ak.stock_zt_pool_em(date=date)
            if df is not None and len(df) > 0:
                pools[date] = df
            time.sleep(0.15)
        except Exception:
            continue
        if (i + 1) % 10 == 0 or i == 0:
            pct = int((i + 1) / len(dates) * 100)
            print(f"[PROGRESS] collect:{pct}:{i+1}/{len(dates)}")
    return pools


def collect_training_data(n_days=120):
    """收集历史二板样本：某天涨停 + 前一天也涨停 = 二板候选，标注次日是否三板"""
    trade_dates = get_trade_dates(n_days + 2)
    print(f"Collecting historical limit-up data (~{n_days} days)...")
    pools = fetch_pools(trade_dates, desc="historical pools")
    sorted_dates = sorted(pools.keys())  # 从早到晚

    if len(sorted_dates) < 3:
        print("Insufficient historical data")
        return None

    samples = []
    # 遍历 T 日，判断 T 日涨停的票是否属于"二板及以上"
    for idx in range(1, len(sorted_dates)):
        t_date = sorted_dates[idx]
        y_date = sorted_dates[idx - 1]   # T-1 (昨天)
        n_date = sorted_dates[idx + 1] if idx + 1 < len(sorted_dates) else None  # T+1 (明天)

        t_pool = pools[t_date]
        y_codes = set(pools[y_date]['代码'].astype(str).str.zfill(6))
        n_codes = set(pools[n_date]['代码'].astype(str).str.zfill(6)) if n_date else set()

        # 当日板块热度
        sector_counts = t_pool['所属行业'].value_counts().to_dict() if '所属行业' in t_pool.columns else {}

        for _, row in t_pool.iterrows():
            code = str(row['代码']).zfill(6)

            # 只收 T-1 也涨停的（即连板 ≥ 2），避免一板样本稀释
            if code not in y_codes:
                continue

            market_cap = row.get('流通市值', 0) or 0
            turnover = row.get('换手率', 0) or 0
            seal_min = _parse_seal_time(row.get('首次封板时间', None))
            zhaban = row.get('炸板次数', 0) or 0
            industry = row.get('所属行业', '')
            board_stat = _parse_board_stat(row.get('涨停统计', None))

            samples.append({
                'code': code,
                'date': t_date,
                'market_cap': float(market_cap),
                'turnover': float(turnover),
                'seal_minutes': seal_min,
                'zhaban': int(zhaban),
                'sector_count': sector_counts.get(industry, 1),
                'board_stat': board_stat,
                'label': 1 if code in n_codes else 0,
            })

    if not samples:
        print("[PROGRESS] collect:100:No 2-board samples found")
        return None

    df = pd.DataFrame(samples)
    print(f"[PROGRESS] collect:100:Samples={len(df)} success_rate={df['label'].mean():.1%}")
    return df


def train_model(df):
    """训练 Logistic 回归"""
    feature_cols = ['market_cap', 'turnover', 'seal_minutes', 'zhaban', 'sector_count', 'board_stat']

    X = df[feature_cols].copy()
    y = df['label'].values

    # market_cap 取 log，避免长尾
    X['market_cap'] = np.log1p(X['market_cap'].clip(lower=1))

    X = X.fillna(0).replace([np.inf, -np.inf], 0)

    pipeline = Pipeline([
        ('scaler', StandardScaler()),
        ('clf', LogisticRegression(C=1.0, class_weight='balanced',
                                   max_iter=2000, random_state=42))
    ])
    pipeline.fit(X, y)

    # 打印特征重要性
    coef = pipeline.named_steps['clf'].coef_[0]
    print("Feature weights (log-odds):")
    for name, w in zip(feature_cols, coef):
        direction = "stronger" if w > 0 else "weaker"
        print(f"  {name:>16s}: {w:+.4f}  ({direction})")

    return pipeline, feature_cols


def predict_prob(model, feature_cols, pool_row, sector_count=1):
    """对单只涨停票预测三板概率"""
    row_data = {
        'market_cap': np.log1p(max(float(pool_row.get('流通市值', 0) or 0), 1)),
        'turnover': float(pool_row.get('换手率', 0) or 0),
        'seal_minutes': _parse_seal_time(pool_row.get('首次封板时间', None)),
        'zhaban': int(pool_row.get('炸板次数', 0) or 0),
        'sector_count': sector_count,
        'board_stat': _parse_board_stat(pool_row.get('涨停统计', None)),
    }
    X = pd.DataFrame([row_data])[feature_cols]
    proba = model.predict_proba(X)[0]
    return proba[1]


def load_or_train(retrain=False, train_days=120):
    """加载缓存模型，或重新训练"""
    if not retrain and MODEL_PATH.exists():
        age_hours = (time.time() - MODEL_PATH.stat().st_mtime) / 3600
        if age_hours < 24:
            print(f"Loading cached model ({age_hours:.0f}h old)...")
            with open(MODEL_PATH, 'rb') as f:
                return pickle.load(f)

    print("Training new model...")
    df = collect_training_data(n_days=train_days)
    if df is None:
        print("Falling back to heuristic model")
        return None, None

    df.to_csv(TRAIN_DATA_PATH, index=False, encoding='utf-8-sig')
    model, features = train_model(df)
    with open(MODEL_PATH, 'wb') as f:
        pickle.dump((model, features), f)
    print(f"Model saved to {MODEL_PATH}")
    return model, features


def main():
    import argparse
    parser = argparse.ArgumentParser(description='涨停二进三概率预估')
    parser.add_argument('csv', help='Input CSV from pick_stocks.py')
    parser.add_argument('--retrain', action='store_true', help='Force retrain model')
    parser.add_argument('--train-days', type=int, default=120, help='Historical days for training')
    args = parser.parse_args()

    # 1. 读取 CSV
    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(f"File not found: {args.csv}")
        sys.exit(1)

    df_input = pd.read_csv(csv_path, dtype={'代码': str})
    df_input['代码'] = df_input['代码'].str.zfill(6)
    print(f"Loaded {len(df_input)} stocks from {csv_path.name}")

    # 2. 加载/训练模型
    print("=" * 60)
    print("[PROGRESS] train:0:Loading or training model...")
    model, feature_cols = load_or_train(retrain=args.retrain, train_days=args.train_days)
    print("[PROGRESS] train:100:Model ready")

    # 3. 获取今日涨停池
    today_str = datetime.now().strftime('%Y%m%d')
    print(f"\nFetching today's ({today_str}) limit-up pool...")
    print("[PROGRESS] predict:10:Fetching today limit-up pool...")
    try:
        today_pool = ak.stock_zt_pool_em(date=today_str)
    except Exception:
        # 如果今天还没收盘，尝试上一个交易日
        trade_dates = get_trade_dates(3)
        today_str = trade_dates[0]
        print(f"  Retry with latest trading day: {today_str}")
        today_pool = ak.stock_zt_pool_em(date=today_str)

    if today_pool is None or len(today_pool) == 0:
        print("Warning: no limit-up data for today, all probs will be '--'")
        today_pool = pd.DataFrame()

    today_codes = set(today_pool['代码'].astype(str).str.zfill(6)) if len(today_pool) > 0 else set()

    # 当日板块热度
    if len(today_pool) > 0 and '所属行业' in today_pool.columns:
        today_sector_counts = today_pool['所属行业'].value_counts().to_dict()
    else:
        today_sector_counts = {}

    # 构建今日涨停池索引 (code -> row)
    today_pool_index = {}
    if len(today_pool) > 0:
        for _, row in today_pool.iterrows():
            code = str(row['代码']).zfill(6)
            today_pool_index[code] = row

    # 4. 计算概率
    def calc_prob(code):
        if code not in today_codes:
            return '--'
        if model is None:
            row = today_pool_index.get(code)
            if row is None:
                return '--'
            board = _parse_board_stat(row.get('涨停统计', None))
            mc = float(row.get('流通市值', 0) or 0)
            base = 0.35
            if board >= 3:
                base -= 0.05 * (board - 2)
            if 0 < mc < 5e9:
                base += 0.05
            return f'{max(0.08, min(base, 0.55)):.0%}'

        pool_row = today_pool_index.get(code)
        if pool_row is None:
            return '--'

        # 填入 sector_count
        industry = pool_row.get('所属行业', '')
        sector_ct = today_sector_counts.get(industry, 1)

        prob = predict_prob(model, feature_cols, pool_row, sector_count=sector_ct)
        prob = max(0.02, min(prob, 0.85))
        return f'{prob:.0%}'

    df_input['二进三概率'] = df_input['代码'].apply(calc_prob)

    # 5. 输出
    limit_up_count = sum(1 for v in df_input['二进三概率'] if v != '--')
    print(f"\n[PROGRESS] predict:100:Stocks at limit-up today: {limit_up_count}/{len(df_input)}")

    out_path = csv_path.parent / f'{csv_path.stem}_prob.csv'
    df_input.to_csv(out_path, index=False, encoding='utf-8-sig')
    print(f"Output: {out_path}")

    # 预览
    print("\n" + "=" * 80)
    print("Preview (涨停票 + 概率):")
    preview = df_input[df_input['二进三概率'] != '--'][['代码', '名称', '连板天数', '流通市值(亿)', '二进三概率', '所属行业']]
    if len(preview) > 0:
        print(preview.to_string(index=False))
    else:
        print("  (none of the CSV stocks are at limit-up today)")
    print("=" * 80)


if __name__ == '__main__':
    main()
