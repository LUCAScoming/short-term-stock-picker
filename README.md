# Short-Term Stock Picker (短线强势股筛选工具)

[![GitHub stars](https://img.shields.io/github/stars/online0001/skills?style=social)](https://github.com/online0001/skills)
[![Python](https://img.shields.io/badge/Python-3.7+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

[English](#english) | [中文](#中文)

---

## English

### Overview

`short-term-stock-picker` is a **quantitative stock screening tool** designed for **A-share market** (Chinese stock market). Also known as: **短线选股器**, **强势股筛选工具**, **量化选股**, **涨停板选股**, **技术面选股**.

This tool identifies **short-term strong stocks (短线强势股)** with high momentum by combining:
- **Technical analysis** - MA5/10/20 alignment, golden cross patterns
- **Limit-up history** - Stocks with recent limit-up days
- **Volume analysis** - Momentum indicators
- **Capital flow** - Fund flow estimation

Perfect for: **短线交易**, **涨停板策略**, **强势股操作**, **技术分析选股**, **量化投资**, **A股打板**, **股票筛选**, **沪深股市分析**.

### Features

- **Multi-Factor Screening**: Combines limit-up history, technical indicators, and capital flow
- **Technical Analysis**: MA5/10/20 alignment, golden cross patterns, volume analysis
- **No API Token Required**: Uses AKShare open data source
- **Comprehensive Scoring**: Multi-dimensional scoring system for ranking
- **Cross-Board Support**: Covers Shanghai, Shenzhen, GEM (创业板), and STAR (科创板)

### Screening Criteria

| Criterion | Description |
|-----------|-------------|
| Market Cap | Circulating market cap ≤ 150 billion CNY |
| Limit-Up History | At least 1 limit-up in past 20 trading days |
| Stock Type | Exclude ST and delisting candidates |
| Boards | Shanghai Main Board, Shenzhen, GEM, STAR |
| MA Alignment | Price above MA5, MA10, MA20 simultaneously |
| MA Pattern | MA5 > MA10 > MA20 (bullish alignment) |
| Turnover Rate | 0.5% - 10% (reasonable range) |
| Volume | Recent 5-day volume > previous 5-day volume |

### Scoring System

```
Total Score = Limit-Up Count × 20 + Technical Score + Volume Ratio × 5
```

- Technical Score = MA bullish (20) + Volume surge (5-15) + Price-volume combo (10) + Turnover stability (5)
- Volume Ratio = Avg volume (last 5 days) / Avg volume (previous 5 days)

### Installation

```bash
# Clone the repository
git clone https://github.com/online0001/skills.git
cd skills/short-term-stock-picker

# Install dependencies
pip install akshare pandas

# Run the screener
python3 scripts/pick_stocks.py
```

### Data Source

- **AKShare** - Open-source financial data library
- **East Money (东方财富)** - Primary data provider for:
  - Limit-up pool data
  - Market cap information
  - Real-time quotes

### Output

Results are saved to `result.csv` with the following fields:

| Field | Description |
|-------|-------------|
| 代码 | Stock code |
| 名称 | Stock name |
| 涨停次数(近20日) | Limit-up count in past 20 days |
| 流通市值(亿) | Circulating market cap (100M CNY) |
| 最新价 | Latest price |
| MA5/MA10/MA20 | Moving averages |
| 换手率 | Turnover rate (%) |
| 量比(近5日) | Volume ratio (5-day) |
| 综合评分 | Total score |

### Requirements

- Python 3.7+
- akshare
- pandas

### Disclaimer

This tool is for educational and research purposes only. Stock trading involves substantial risk. Past performance does not guarantee future results. Please make investment decisions responsibly.

---

## 中文

### 简介

`short-term-stock-picker`（短线强势股筛选工具）是一款面向 **A股市场** 的 **量化选股工具**，支持：
- **短线选股**、**强势股筛选**、**涨停板选股**
- **技术面分析**、**量化交易策略**、**A股打板分析**
- **均线系统**、**量价配合分析**、**资金流向研究**

通过综合分析 **涨停历史**、**均线多头排列**、**成交量放量**、**换手率** 等多维度指标，筛选出具有 **短期强势特征** 的股票。

**适用场景**：短线交易、追涨停板、强势股操作、技术分析、量化选股、股票池筛选、热点板块追踪、资金流向分析、东方财富数据研究。

### 核心特性

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
| ST过滤 | 排除ST、*ST、退市风险股 |
| 板块 | 主板、创业板、科创板 |
| 均线站稳 | 股价站稳5/10/20日均线 |
| 均线多头 | MA5 > MA10 > MA20 |
| 换手率 | 0.5% - 10% 合理区间 |
| 成交量 | 近5日均量 > 前5日均量（放量） |

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
| 市值数据 | 东方财富 |
| 行情数据 | 新浪财经 |
| 历史K线 | 新浪财经 |

### 输出结果

结果保存至 `result.csv`，包含以下字段：

| 字段 | 说明 |
|------|------|
| 代码 | 股票代码 |
| 名称 | 股票名称 |
| 涨停次数(近20日) | 近20日涨停次数 |
| 流通市值(亿) | 流通市值（亿元） |
| 最新价 | 最新成交价 |
| MA5/MA10/MA20 | 5/10/20日均线 |
| 换手率 | 日均换手率(%) |
| 量比(近5日) | 成交量放大比例 |
| 综合评分 | 综合实力得分 |

### 依赖环境

- Python 3.7+
- akshare >= 1.18
- pandas

### 免责声明

本工具仅供教育学习和研究参考使用。股票投资存在较大风险，过往业绩不代表未来表现。请理性投资，盈亏自负。

---

## 项目结构

```
short-term-stock-picker/
├── SKILL.md          # OpenClaw Skill 元数据
├── scripts/
│   └── pick_stocks.py  # 选股脚本
├── references/        # 参考资料
├── result.csv        # 筛选结果（运行后生成）
└── README.md         # 项目说明文档
```

## License

MIT License

---

*Made with ❤️ for A-share investors*
