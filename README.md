# Short-Term Stock Picker (短线强势股筛选工具)

[![GitHub stars](https://img.shields.io/github/stars/online0001/skills?style=social)](https://github.com/online0001/skills)
[![Python](https://img.shields.io/badge/Python-3.7+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

[English](#english) | [中文](#中文)

---

## English

### Overview

`short-term-stock-picker` is a quantitative screening tool for A-share market, also known as: **短线选股器**, **强势股筛选工具**, **涨停板选股**, **量化选股**, **技术面选股**.

It identifies stocks with high short-term momentum by combining:
- **Limit-up history** - Stocks with recent limit-up in past 20 trading days
- **Technical analysis** - MA5/MA10/20 alignment, golden cross patterns
- **Volume analysis** - Momentum indicators, volume surge detection
- **Capital flow** - Fund flow estimation

### Features

- **Multi-Factor Screening**: Combines limit-up history, technical indicators, and capital flow
- **Technical Analysis**: MA alignment, golden cross, volume analysis
- **No API Token Required**: Uses AKShare open data source
- **Comprehensive Scoring**: Multi-dimensional scoring system for ranking
- **Cross-Board Support**: Shanghai, Shenzhen, GEM (创业板), STAR (科创板)

### Screening Criteria

| Criterion | Description |
|-----------|-------------|
| Market Cap | Circulating market cap ≤ 150 billion CNY |
| Limit-Up | At least 1 limit-up in past 20 trading days |
| MA Alignment | Price above MA5, MA10, MA20 simultaneously |
| MA Pattern | MA5 > MA10 > MA20 (bullish alignment) |
| Turnover Rate | 0.5% - 10% |
| Volume | Recent 5-day volume > previous 5-day volume |

### Scoring System

```
Total Score = Limit-Up Count × 20 + Technical Score + Volume Ratio × 5
```

### Installation

```bash
git clone https://github.com/online0001/skills.git
cd skills/short-term-stock-picker
pip install akshare pandas
python3 scripts/pick_stocks.py
```

### Output

Results saved to `result.csv`:
- Stock code, name
- Limit-up count (20 days)
- Market cap, price, MA5/10/20
- Turnover rate, volume ratio
- Total score

### Requirements

- Python 3.7+
- akshare, pandas

---

## 中文

### 简介

`short-term-stock-picker`（短线强势股筛选工具）是一款面向A股市场的量化选股工具，支持：**短线选股**、**强势股筛选**、**涨停板选股**、**技术面选股**、**量化交易策略**。

通过综合分析涨停历史、均线系统、成交量变化等多维度指标，筛选出具有短期强势特征的股票。

### 功能特点

- **多因子筛选**：综合涨停基因、技术形态、资金流向
- **技术分析**：均线多头排列、量价配合、趋势健康
- **无需Token**：基于AKShare开源数据源，免费使用
- **综合评分**：多维度打分体系，科学排序
- **全市场覆盖**：主板（沪/深）、创业板、科创板

### 筛选条件

| 条件 | 说明 |
|------|------|
| 市值 | 流通市值 ≤ 150亿 |
| 涨停基因 | 近20个交易日有涨停 |
| 均线站稳 | 股价站稳5/10/20日均线 |
| 均线多头 | MA5 > MA10 > MA20 |
| 换手率 | 0.5% - 10% 合理区间 |
| 成交量 | 近5日均量 > 前5日均量 |

### 评分体系

```
综合评分 = 涨停次数×20 + 技术评分 + 量比×5
```

- **技术评分** = 均线多头(20分) + 成交量放量(5-15分) + 量价配合(10分) + 换手稳定(5分)
- **量比** = 近5日均量 / 前5日均量（>1.5为明显放量）

### 安装使用

```bash
# 克隆仓库
git clone https://github.com/online0001/skills.git
cd skills/short-term-stock-picker

# 安装依赖
pip install akshare pandas

# 运行选股
python3 scripts/pick_stocks.py
```

### 数据来源

| 数据类型 | 来源 |
|----------|------|
| 涨停股池 | 东方财富 |
| 历史行情 | 新浪财经 |
| 市值数据 | 东方财富 |

### 输出结果

结果保存至 `result.csv`，包含：
- 代码、名称、涨停次数
- 流通市值、最新价、均线
- 换手率、量比、综合评分

### 项目结构

```
short-term-stock-picker/
├── SKILL.md          # OpenClaw Skill 元数据
├── scripts/
│   └── pick_stocks.py  # 选股脚本
├── references/        # 参考资料
└── README.md         # 项目说明文档
```

### 免责声明

本工具仅供教育学习和研究参考使用。股票投资存在较大风险，请理性投资，盈亏自负。

---

**GitHub**: https://github.com/online0001/skills

*Made with ❤️ for A-share investors*