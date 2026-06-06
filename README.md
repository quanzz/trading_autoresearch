# Trading Autoresearch

基于 karpathy/autoresearch 的思路，将自主 AI 研究范式应用于量化交易策略优化。

## 项目结构

```
trading_autoresearch/
├── backtest/
│   ├── __init__.py      # 回测框架导出
│   ├── account.py        # 账户、持仓、订单、交易 (不可修改)
│   ├── engine.py         # 逐Bar回测循环 (不可修改)
│   └── metrics.py        # 最大回撤、夏普比率、综合得分 (不可修改)
├── config.yaml           # 用户配置：手续费、滑点、乘数等
├── prepare.py            # CSV数据加载 (不可修改)
├── strategy.py           # 交易策略 — AI Agent 修改此文件
├── run.py                # 单次回测入口
├── program.md            # AI Agent 指令
├── results.tsv           # 实验结果记录 (tab分隔)
└── research_log.md       # 研究发现日志 (Markdown)
```

## 快速开始

### 1. 安装依赖

```bash
pip install numpy pandas pyyaml
```

### 2. 准备数据

将分钟级 CSV 数据放入 `data/` 目录，文件命名如 `au2607.csv`。

CSV 格式（逗号分隔）：
```
date,open,high,low,close,volume,amt,oi
2026-06-06 09:31:28,450.50,450.80,450.20,450.60,1234,556000,50000
```

### 3. 修改配置

编辑 `config.yaml` 设置手续费、滑点、乘数等参数。

### 4. 运行回测

```bash
python run.py
```

### 5. 启动自主研究

将 `program.md` 作为 AI Agent 的指令，让它自主迭代优化策略：

```
请阅读 program.md，开始 Trading Autoresearch 实验。
```

## 设计说明

- **只需修改一个文件**: Agent 只修改 `strategy.py`，保持变更可审查
- **固定评估指标**: `backtest/` 中的回测引擎和指标计算不可修改
- **综合评分**: 加权结合最大回撤 (优先级最高) 和夏普比率
- **无人值守**: 一次启动后完全自主运行
- **结果追踪**: `results.tsv` 记录每次实验，`research_log.md` 记录发现

## 优化指标

- **最大回撤 (Max Drawdown, MDD)**: 优先级最高
- **夏普比率 (Sharpe Ratio)**: 优先级其次
- **综合得分**: `score = -0.6 × MDD + 0.4 × min(Sharpe, 3) / 3`
