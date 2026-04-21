# Short-Term Stock Picker (短线强势股筛选工具)

[![GitHub stars](https://img.shields.io/github/stars/online0001/skills?style=social)](https://github.com/online0001/skills)
[![Python](https://img.shields.io/badge/Python-3.7+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

[English](#english) | [中文](#中文)

---

## English

### Overview

`short-term-stock-picker` is a **professional quantitative stock screening tool** designed for **A-share market** (Chinese stock market / 沪深股市 / A股).

Also known as: **短线选股器**, **强势股筛选工具**, **量化选股**, **涨停板选股**, **技术面选股**, **短线交易策略**, **A股打板工具**.

### What It Does

This tool identifies **short-term strong stocks (短线强势股)** with high momentum by combining:
- **Limit-up history analysis (涨停基因分析)** - Stocks with recent limit-up days in past 20 trading sessions
- **Technical analysis (技术面分析)** - MA5/10/20 alignment, golden cross patterns, volume analysis
- **Capital flow estimation (资金流向估算)** - Fund flow estimation based on volume and price action
- **Trend health assessment (趋势健康度)** - Multi-dimensional scoring system

### Supported Features

| Feature | Description |
|---------|-------------|
| **Limit-Up Screening** | Filter stocks with limit-up history in past 20 trading days |
| **Technical Analysis** | MA5/MA10/MA20 alignment detection, bullish pattern recognition |
| **Volume Analysis** | Volume surge detection, momentum indicators |
| **Market Cap Filter** | Circulating market cap ≤ 150 billion CNY |
| **Board Coverage** | Shanghai Main Board, Shenzhen, GEM (创业板), STAR (科创板) |
| **ST Exclusion** | Automatic removal of ST and delisting candidates |
| **Comprehensive Scoring** | Multi-factor scoring for stock ranking |

### Supported Data Sources

| Data Type | Source | API |
|-----------|--------|-----|
| Limit-up Pool | East Money | `stock_zt_pool_em()` |
| Historical Quotes | Sina Finance | `stock_zh_a_daily()` |
| Market Cap | East Money | Limit-up pool data |
| Real-time Quotes | East Money | `stock_zt_pool_em()` |

### Screening Criteria

| Criterion | Threshold | Description |
|-----------|-----------|-------------|
| Market Cap | ≤ 150亿 | Circulating market cap limit |
| Limit-Up | ≥ 1次 | At least 1 limit-up in 20 days |
| MA Alignment | 100% | Price above MA5, MA10, MA20 |
| MA Pattern | 多头 | MA5 > MA10 > MA20 |
| Turnover Rate | 0.5-10% | Reasonable range |
| Volume Ratio | > 1.0 | Recent 5-day vs previous 5-day |

### Scoring System

```
Total Score = Limit-Up Count × 20 + Technical Score + Volume Ratio × 5
```

**Technical Score Components:**
- MA Bullish Alignment: 20 points
- Volume Surge (>1.5x): 15 points
- Volume Surge (>1.2x): 10 points
- Price-Volume Combo: 10 points
- Turnover Stability: 5 points

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

### Output Fields

| Field | Description |
|-------|-------------|
| 代码 | Stock code |
| 名称 | Stock name |
| 涨停次数(近20日) | Limit-up count in past 20 days |
| 流通市值(亿) | Circulating market cap (100M CNY) |
| 最新价 | Latest price |
| MA5/MA10/MA20 | 5/10/20-day moving averages |
| 换手率 | Turnover rate (%) |
| 量比(近5日) | Volume ratio (5-day) |
| 3日涨跌 | 3-day price change direction |
| 均线多头 | MA bullish status |
| 综合评分 | Total score |

### Requirements

- Python 3.7+
- akshare >= 1.18
- pandas

### Use Cases

- **短线交易** - Short-term trading signals
- **涨停板策略** - Limit-up trading strategies
- **强势股操作** - Strong stocks identification
- **技术分析选股** - Technical analysis stock screening
- **量化投资** - Quantitative investment research
- **A股打板** - A-share limit-up trading
- **股票池筛选** - Stock pool filtering
- **热点板块追踪** - Hot sector tracking
- **资金流向分析** - Capital flow analysis

### Disclaimer

This tool is for **educational and research purposes only**. Stock trading involves substantial risk. Past performance does not guarantee future results. Please make investment decisions responsibly.

---

## 中文

### 简介

`short-term-stock-picker`（短线强势股筛选工具）是一款面向 **A股市场** 的 **专业量化选股工具**，支持：

- **短线选股**、**强势股筛选**、**涨停板选股**、**技术面选股**
- **量化交易策略**、**A股打板分析**、**资金流向研究**
- **均线系统分析**、**量价配合分析**、**趋势健康度评估**

本工具基于 **AKShare** 开源金融数据接口，**无需API Token**，一键运行即可筛选出具备短线强势特征的股票。

### 功能特点

- **接口完整**：基于AKShare 98+数据接口构建
- **市场全面**：支持主板（沪/深）、创业板（300）、科创板（688）
- **功能丰富**：包含涨停基因分析、技术面筛选、资金估算、综合评分
- **调用简便**：一行命令即可运行，无需复杂配置
- **参数灵活**：可调整市值、换手率、均线参数
- **错误处理**：内置异常处理机制，确保程序稳定运行
- **数据格式**：输出CSV格式，便于Excel/WPS分析
- **文档详细**：SKILL.md + README双文档说明

### 筛选条件

| 条件 | 阈值 | 说明 |
|------|------|------|
| 市值 | ≤ 150亿 | 流通市值过滤 |
| 涨停基因 | ≥ 1次 | 近20个交易日有涨停 |
| 均线站稳 | 100% | 股价站稳MA5/MA10/MA20 |
| 均线多头 | 多头 | MA5 > MA10 > MA20 |
| 换手率 | 0.5-10% | 合理区间 |
| 成交量 | > 1.0倍 | 近5日均量 > 前5日均量 |

### 数据来源

| 数据类型 | 来源 | 说明 |
|----------|------|------|
| 涨停股池 | 东方财富 | `stock_zt_pool_em()` |
| 历史行情 | 新浪财经 | `stock_zh_a_daily()` |
| 市值数据 | 东方财富 | 涨停池内嵌数据 |
| 实时行情 | 东方财富 | 涨停池实时数据 |

### 评分体系

```
综合评分 = 涨停次数×20 + 技术评分 + 量比×5
```

**技术评分组成：**
- 均线多头排列：20分
- 成交量明显放量(>1.5倍)：15分
- 成交量温和放量(>1.2倍)：10分
- 量价配合：10分
- 换手率稳定：5分

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

### 输出字段

| 字段 | 说明 |
|------|------|
| 代码 | 6位股票代码 |
| 名称 | 股票名称 |
| 涨停次数(近20日) | 近20个交易日涨停次数 |
| 流通市值(亿) | 流通市值（亿元） |
| 最新价 | 最新成交价 |
| MA5/MA10/MA20 | 5/10/20日均线价格 |
| 换手率 | 日均换手率(%) |
| 量比(近5日) | 成交量放大比例 |
| 3日涨跌 | 近3日涨跌方向 |
| 均线多头 | 是否均线多头排列 |
| 技术评分 | 技术面得分 |
| 综合评分 | 综合实力得分 |
| 板块 | 上交所/深交所/创业板/科创板 |
| 所属行业 | 申万行业分类 |

### 适用场景

- **短线选股** - 筛选短期强势股
- **强势股筛选** - 识别市场领先者
- **涨停板策略** - 追涨停板分析
- **技术面选股** - MA金叉、均线多头
- **量化投资研究** - 量化策略回测
- **A股打板** - 涨停板打板策略
- **股票池管理** - 构建自选股池
- **热点板块追踪** - 热门题材分析
- **资金流向研究** - 主力资金动向

### 项目结构

```
short-term-stock-picker/
├── SKILL.md              # OpenClaw Skill 元数据
├── README.md             # 项目说明文档
├── LICENSE               # MIT开源协议
├── scripts/
│   └── pick_stocks.py   # 选股脚本（核心）
├── references/           # 参考资料目录
└── result.csv           # 筛选结果（运行后生成）
```

### 技术栈

- **Python 3.7+** - 编程语言
- **AKShare** - 金融数据接口
- **Pandas** - 数据处理分析

### 依赖环境

```txt
akshare >= 1.18
pandas
python >= 3.7
```

### 免责声明

本工具仅供**教育学习和研究参考**使用。股票投资存在较大风险，过往业绩不代表未来表现。量化筛选结果仅供参考，不构成投资建议。**请理性投资，盈亏自负。**

---

## 支持的AKShare接口

### 涨停板行情接口

| 接口 | 说明 |
|------|------|
| `stock_zt_pool_em()` | 涨停股池 |
| `stock_zt_pool_previous_em()` | 昨日涨停股池 |
| `stock_dt_pool_em()` | 跌停股池 |

### 历史行情接口

| 接口 | 说明 |
|------|------|
| `stock_zh_a_daily()` | 新浪财经历史行情 |
| `stock_zh_a_hist()` | 东方财富历史行情 |
| `stock_zh_a_hist_tx()` | 腾讯历史行情 |

---

*Made with ❤️ for A-share investors | 专为A股投资者打造*

**GitHub**: https://github.com/online0001/skills