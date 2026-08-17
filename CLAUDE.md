# Short-Term Stock Picker

短线强选工具，基于 AKShare 开放数据，筛选 A 股短线强势标的。

## 项目结构

```
scripts/pick_stocks.py   # 核心选股脚本（涨停+技术面+资金面）
scripts/board_prob.py    # 二进三涨停概率预估（Logistic 回归）
scripts/hot_sectors.py   # 热门放量板块筛选
server.py                # Web 管理界面（http://localhost:8080）
```

## 常用命令

```bash
python scripts/pick_stocks.py   # 命令行运行选股
python scripts/hot_sectors.py   # 命令行运行板块筛选
python server.py                # 启动 Web UI
```

## 评分体系（v3.0 修改记录，分支 feature/pointChange3.0）

基于 original 评分修复 6 处问题（commit `9760e81`）：

| # | 问题 | 修改前 | 修改后 |
|---|------|--------|--------|
| 1 | 量比双重计算 | tech_score 内按 vol_ratio 加 15/10/5，综合分又 vol_ratio×10 | 去掉 tech_score 量比分档，综合分仅 vol_ratio×10 计一次 |
| 2 | 换手率过滤/加分区间矛盾 | 过滤留 5-10，加分 2-8（错位） | 加分 5-8% +5，8-10% -5（高位换手惩罚） |
| 3 | 连板加分无上限 | (consecutive-1)×10 无封顶 | 2板+10 / 3板+15 / ≥4板-15（高位接盘惩罚） |
| 8 | 涨停次数无时间衰减 | limit_up_count×10 等权 | limit_up_decay_score = Σ 0.9^days_ago×10，近期权重高 |
| 9 | 今日首板陷阱 | first_days_ago≤3 一律 15 分 | 今日(0天)→5 分，1-3 天→15 分，4-7 天→8 分 |
| 11 | 均线刚性淘汰 | 不满足完美多头直接 return None | 分级：完美多头 30 / 接近多头 20 / 弱势 10 / 破 ma20 才淘汰 |

**附带改动**：
- 结果输出新增 `涨停衰减得分` 列，original 与 3d 两套 `display_cols` 同步加入
- 启动打印的筛选条件第 5 条、评分权重说明文案已更新

**可调参数**：
- 衰减系数 `0.9`（`get_all_limit_up_stocks` 内）：越小则远期涨停掉权越快
- 连板转惩罚阈值 `≥4`（`analyze_stock` 内）：可改为 `≥3` 更激进

**未修问题（后续可做）**：资金面缺失 #4、多周期过热 #10、大盘环境过滤 #7、市值/除权数据修正 #12/#13、板块热度各自短板。

## 注意事项

- 所有问题用中文回答
- commit message 使用中文
- 选股结果的 CSV 文件（`*-result*.csv`）需要一并提交到仓库
- Windows 终端编码问题：用 `sys.stdout.reconfigure(encoding='utf-8')`，不要用 `io.TextIOWrapper` 包裹（会造成双重缓冲）
- 本机 requests 库无法直连东方财富 push 服务器，需要 monkey-patch 替换为 urllib.request（见 `pick_stocks.py` 头部）
- 所有 `print` 用英文/数字，避免 emoji 在 subprocess 中 GBK 报错；如果要用 emoji，确保已 reconfigure stdout
