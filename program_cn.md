# Trading Autoresearch

一个量化交易策略优化实验：AI Agent 自主迭代交易策略、回测评估，并优化风险调整后收益。

## 项目结构

```
trading_autoresearch/
├── backtest/                    # 回测框架（只读，不可修改）
│   ├── __init__.py              # 包导出
│   ├── account.py               # 账户、持仓、订单、交易数据模型
│   ├── engine.py                # 逐 Bar 回测引擎
│   ├── metrics.py               # 最大回撤、夏普比率、综合得分计算
│   └── strategy_base.py         # 策略基类 + 技术指标辅助函数
├── strategies/                  # 策略实现目录 —— Agent 在此创建/编辑策略
│   ├── __init__.py              # 策略注册 + create_strategy() 工厂
│   ├── sma_cross.py             # SMA 交叉策略
│   ├── bollinger_breakout.py    # 布林带均值回归策略
│   ├── momentum_volume.py       # 动量 + 成交量策略
│   └── rsi_reversion.py         # RSI 均值回归策略
├── data/                        # 数据目录（存放 CSV 行情文件）
│   └── au2607.csv               # 示例：单个品种的分钟级 OHLCV 数据
├── results/                     # 回测产物目录（每次运行自动生成）
│   ├── strategies_<时间戳>/     # 策略目录的副本
│   ├── equity_<时间戳>_<名>.png # 净值曲线图（含回撤面板）
│   └── report_<时间戳>_<名>.md  # 回测总结报告（Markdown）
├── config.yaml                  # 用户配置：手续费/滑点/乘数/保证金率（只读）
├── prepare.py                   # CSV 数据加载（只读）
├── strategy.py                  # 薄封装 — 重新导出 strategies/（不可修改）
├── run.py                       # 单次回测入口，运行后输出指标并生成产物
├── results.tsv                  # 实验结果记录（Tab 分隔，untracked）
├── research_log.md              # 研究发现日志（人类可读）
├── program.md / program_cn.md   # AI Agent 指令（本文件）
├── pyproject.toml               # 项目依赖
└── README.md                    # 项目说明
```

### 文件角色说明

| 文件/目录 | 角色 | 是否可修改 |
|-----------|------|-----------|
| `backtest/` | 回测框架（引擎、账户、指标、策略基类） | ❌ 只读 |
| `config.yaml` | 交易参数配置 | ❌ 只读（用户编辑） |
| `prepare.py` | 数据加载与预处理 | ❌ 只读 |
| `strategy.py` | 薄封装重新导出 | ❌ 只读 |
| `run.py` | 回测入口与产物生成 | ❌ 只读 |
| `strategies/` | 策略实现目录 | ✅ **Agent 修改** |
| `results.tsv` | 实验结果记录 | ✏️ Agent 追加（untracked） |
| `research_log.md` | 研究发现日志 | ✏️ Agent 追加 |
| `results/` | 回测产物输出 | 🤖 自动生成 |

## 初始化设置

开始新实验前，请按以下步骤操作：

1. **约定运行标签**：基于当前日期提议一个标签（例如 `jun6`）。分支 `autoresearch/<tag>` 必须尚不存在——这代表一次全新的运行。
2. **创建分支**：从当前 master 执行 `git checkout -b autoresearch/<tag>`。
3. **阅读相关文件**：阅读上述项目结构中列出的文件，理解各自职责。
4. **验证数据存在**：检查 `data/` 目录下是否包含所配置品种的 CSV 文件。如果数据文件不存在，告知用户提供数据。
5. **初始化 results.tsv**：创建仅包含表头行的 `results.tsv`：

```
commit	score	mdd	sharpe	total_return	trades	status	description
```

6. **确认并开始**：确认一切就绪后，启动实验循环。

获得用户确认后，立即开始实验循环。

## 实验

每次实验在 CPU 上运行单次回测。回测逐 Bar 遍历分钟级 OHLCV 数据，执行策略产生的交易信号。

**你可以做的事：**
- 在 `strategies/` 目录下创建和编辑策略文件 — 这是你唯一可以修改的地方。一切皆可调整：策略类型、参数、指标周期、仓位大小、入场/出场逻辑、过滤器、止损/止盈规则。你可以编写全新的策略类作为独立的 `.py` 文件，文件名体现策略特点。
- 修改 `strategies/__init__.py` 来切换活跃策略或调整参数。
- 使用 `backtest.strategy_base` 中的指标辅助函数（`sma`、`ema`、`stddev`、`rsi`）。

**你不可以做的事：**
- 修改 `backtest/`、`prepare.py`、`config.yaml`、`strategy.py` 或 `run.py`。它们都是只读的。
- 安装新的包或添加依赖。你只能使用 `pyproject.toml` 中已有的库（numpy、pandas、pyyaml 以及 Python 标准库）。
- 修改评估框架。`backtest/metrics.py` 中的 `compute_all_metrics` 函数是唯一的评判标准。

**目标很简单：获得最高的 `score`（综合得分）。** 得分是以下两项的加权组合：
- `score = -MDD权重 × MDD + 夏普权重 × min(Sharpe, 3) / 3`
- 默认权重：MDD = 0.6，夏普 = 0.4
- 得分越高越好。MDD 贡献为负值（回撤越低，得分越高）。

**策略设计核心原则：**
- **无未来函数**：策略在 Bar `i` 只能看到 `lookback[:i+1]`。订单在**下一根** Bar 的开盘价执行。
- **风险管理**：保护本金（低 MDD）是最高优先级。一个收益 50% 但回撤 40% 的策略，得分会低于收益 20% 但回撤仅 5% 的策略。
- **鲁棒性**：能在不同市场环境（趋势、震荡、高波动）下稳定表现的策略得分更高。
- **简洁性原则**：其他条件相同时，越简单越好。增加 50 行复杂逻辑换来微小的得分提升是不值得的。删除代码并获得相同或更好的结果，则是极好的成果。

**首次运行**：你的第一次运行应始终用于建立基线。使用默认策略直接运行。

## 输出格式

回测结束后会打印摘要：

```
---
score:            0.4521
max_drawdown:     0.1234
sharpe_ratio:     1.89
total_return:     0.2345
total_trades:     156
win_rate:         0.5200
bars_processed:   10000
elapsed_seconds:  2.3
round_trips:      45
```

从日志中提取关键指标：

```
grep "^score:" run.log
```

## 记录结果

每次实验结束后，将结果记录到 `results.tsv`（Tab 分隔，**不是**逗号分隔）。

TSV 文件包含表头行和 8 列：

```
commit	score	mdd	sharpe	total_return	trades	status	description
```

1. git commit 哈希（短格式，7 个字符）
2. 达到的 score（例如 0.4521）——崩溃时填 0.0
3. 最大回撤 max_drawdown（例如 0.1234）——崩溃时填 0.0
4. 夏普比率 sharpe_ratio（例如 1.89）——崩溃时填 0.0
5. 总收益 total_return（例如 0.2345）——崩溃时填 0.0
6. 总交易次数 total_trades——崩溃时填 0
7. 状态 status：`keep`（保留）、`discard`（丢弃）或 `crash`（崩溃）
8. 本实验尝试内容的简短描述

示例：

```
commit	score	mdd	sharpe	total_return	trades	status	description
a1b2c3d	0.4521	0.1234	1.89	0.2345	156	keep	基线 SMA交叉策略 (20, 60)
b2c3d4e	0.4612	0.1102	1.92	0.2511	142	keep	快线上调至30，慢线上调至90
c3d4e5f	0.3910	0.1801	1.55	0.1500	200	discard	添加RSI过滤器 - 太多虚假信号
d4e5f6g	0.0000	0.0000	0.00	0.0000	0	crash	参数名拼写错误
```

## 研究日志

同时维护 `research_log.md`，以人类可读的格式记录。每条记录应包含：

```markdown
## YYYY-MM-DD HH:MM | 实验 #N

**策略**: <策略名称及关键参数>
**得分**: X.XXXX | **MDD**: X.XX% | **夏普**: X.XX | **收益**: X.XX%
**假设**: <你认为什么改进会有效>
**发现**: <实际发生了什么，以及你认为为什么会发生>
**决定**: KEEP / DISCARD / CRASH — <简要原因>
```

研究日志是用户了解你思考过程的窗口。要有洞察力。记录模式、市场行为、边界情况和可推广的经验教训。

## 实验循环

实验在专用分支上运行（例如 `autoresearch/jun6`）。

无限循环，永不停歇：

1. 查看 git 状态：当前所在的分支/commit
2. 阅读 `strategies/`、`results.tsv` 和 `research_log.md`，理解当前状态和过往实验
3. 基于过往结果，提出一个改进假设
4. 用你的实验想法修改 `strategies/` 下的策略文件
5. 使用描述性信息执行 `git commit`
6. 运行实验：`python run.py > run.log 2>&1`
7. 读取结果：`grep "^score:\|^max_drawdown:\|^sharpe_ratio:\|^total_return:\|^total_trades:\|^win_rate:" run.log`
8. 如果 grep 输出为空，说明运行崩溃。执行 `tail -n 50 run.log` 读取 Python 堆栈跟踪并尝试修复。如果多次尝试都无法解决，放弃。
9. 将结果记录到 `results.tsv`（注意：**不要**提交 `results.tsv`，让它保持 untracked 状态）
10. 如果 score 提高了（更高），则"推进"分支，保留该 commit。在 `research_log.md` 中撰写详细记录。
11. 如果 score 持平或更差，`git reset` 回到实验前的状态
12. 在 `research_log.md` 中撰写简短的丢弃记录。

注意：每次运行会自动在 `results/` 目录生成三个产物：
- `results/strategies_<时间戳>/` — 策略目录的完整副本
- `results/equity_<时间戳>_<策略名>.png` — 含回撤面板的净值曲线图
- `results/report_<时间戳>_<策略名>.md` — 完整的 Markdown 总结报告

核心理念是：你是一个完全自主的量化研究员，不断尝试新想法。有效的就保留，无效的就丢弃。你不断推进分支以便迭代。如果感觉陷入瓶颈，更深入地思考——重新阅读策略代码寻找新角度，组合之前差点成功的实验元素，尝试更激进的策略变更。

**超时处理**：每次回测应该很快完成（几秒到几分钟）。如果单次运行超过 10 分钟，终止它并视为崩溃。

**崩溃处理**：如果运行崩溃（bug、数据问题等），自行判断：如果是简单的修复（拼写错误、缺少导入），修复后重新运行。如果想法本身就有根本性问题，跳过它，记录 "crash"，继续下一个实验。

**永不停止**：一旦实验循环开始，**不要**暂停询问用户是否继续。**不要**问"我应该继续吗？"或"这是个好的暂停点吗？"。用户可能在睡觉或离开了电脑。你是自主的。如果你思路枯竭，更努力地思考——尝试不同的策略类型（趋势跟踪、均值回归、突破、动量、形态识别），更激进地调整参数，添加风险管理模块，组合多个信号，尝试不同的仓位管理方法。循环持续运行，直到用户手动中断。

用户可能会在睡觉时让你持续运行。如果每次实验耗时约 1-2 分钟，你每小时可以运行 30-60 次实验，一晚上可以完成数百次。

## 策略设计空间

以下是你可探索的维度：

- **趋势跟踪**：均线交叉、MACD、ADX、通道突破
- **均值回归**：布林带、RSI 极值、统计套利
- **动量**：价格变化率、相对强弱、量价分析
- **突破**：支撑/阻力位、波动率突破、开盘区间
- **形态识别**：K线形态、价格行为模式
- **过滤器**：成交量确认、波动率状态、日内时段
- **风险管理**：止损、止盈、移动止损、最大持仓数
- **仓位管理**：固定仓位、波动率调整、凯利公式
- **出场规则**：时间出场、信号出场、移动出场、利润目标
- **多时间框架**：使用多个回顾周期确认信号
