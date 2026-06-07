#!/usr/bin/env python
"""
Trading Autoresearch — Single Run Entry Point.

Loads config, data, strategy; runs backtest; prints parseable metrics summary.
After each backtest, automatically generates:
  1. A copy of the strategies directory → results/strategies_<timestamp>/
  2. An equity curve chart             → results/equity_<timestamp>_<name>.png
  3. A summary report                  → results/report_<timestamp>_<name>.md


Trading Autoresearch — 单次运行入口。

加载配置、数据、策略；运行回测；输出可解析的指标摘要。
每次回测后自动生成：
  1. 策略目录副本  → results/strategies_<timestamp>/
  2. 权益曲线图    → results/equity_<timestamp>_<name>.png
  3. 摘要报告      → results/report_<timestamp>_<name>.md

Usage / 用法：
    python run.py
    python run.py --config config.yaml
"""

import argparse
import os
import shutil
import sys
import time
from datetime import datetime
from typing import List

import yaml

from prepare import load_all_data
from strategies import create_strategy
from backtest import Account, run_backtest


# ===========================================================================
# Configuration
# 配置
# ===========================================================================

def load_config(config_path: str) -> dict:
    """Load YAML configuration file.

    加载 YAML 配置文件。"""
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ===========================================================================
# Post-backtest: copy strategy script
# 回测后处理：复制策略脚本
# ===========================================================================

def save_strategy_copy(script_dir: str, results_dir: str, timestamp: str):
    """Copy the strategies/ directory to results/ with a date-stamped name.

    将 strategies/ 目录复制到 results/ 目录，文件名带时间戳。"""
    src = os.path.join(script_dir, "strategies")
    dst = os.path.join(results_dir, f"strategies_{timestamp}")
    if os.path.isdir(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    # Also copy strategy.py wrapper for reference
    # 同时复制 strategy.py 封装文件以供参考
    wrapper_src = os.path.join(script_dir, "strategy.py")
    wrapper_dst = os.path.join(results_dir, f"strategy_{timestamp}.py")
    shutil.copy2(wrapper_src, wrapper_dst)
    print(f"Strategy copy saved: {dst}")


# ===========================================================================
# Post-backtest: equity curve chart
# 回测后处理：权益曲线图
# ===========================================================================

def save_equity_chart(
    results_dir: str,
    timestamp: str,
    strategy_name: str,
    equity_curve: List[float],
    equity_timestamps: List[str],
    initial_capital: float,
    result: dict,
):
    """Generate and save an equity curve chart as a PNG image.

    生成权益曲线图并保存为 PNG 图片。"""
    import matplotlib
    matplotlib.use("Agg")  # non-interactive backend / 非交互式后端
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib.ticker import FuncFormatter

    # Sanitize strategy name for filename
    # 清理策略名称用于文件名
    safe_name = strategy_name.replace(" ", "_").replace("/", "_").replace("\\", "_")
    filename = f"equity_{timestamp}_{safe_name}.png"
    filepath = os.path.join(results_dir, filename)

    # Prepare data
    # 准备数据
    n = len(equity_curve)
    if n < 2:
        print(f"  Skipping chart: insufficient data points ({n})")
        return

    # Parse timestamps for x-axis
    # 解析时间戳用于 x 轴
    try:
        dates = [datetime.strptime(ts, "%Y-%m-%d %H:%M:%S") for ts in equity_timestamps]
    except (ValueError, TypeError):
        # Fall back to bar index if timestamps can't be parsed
        # 如果时间戳无法解析，退而使用 K 线索引
        dates = list(range(n))

    # Compute drawdown for shading
    # 计算回撤用于阴影区域
    peak = initial_capital
    drawdowns = []
    for v in equity_curve:
        if v > peak:
            peak = v
        dd = (peak - v) / peak * 100 if peak > 0 else 0
        drawdowns.append(dd)

    # Create figure with two subplots: equity + drawdown
    # 创建包含两个子图的图表：权益 + 回撤
    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(14, 8),
        gridspec_kw={"height_ratios": [3, 1]},
        sharex=True,
    )

    # --- Top panel: equity curve ---
    # --- 上图：权益曲线 ---
    ax1.plot(dates, equity_curve, color="#2e86de", linewidth=1.2, label="Equity")
    ax1.axhline(y=initial_capital, color="#888888", linewidth=0.8,
                linestyle="--", alpha=0.7, label=f"Initial ({initial_capital:,.0f})")
    ax1.fill_between(dates, initial_capital, equity_curve,
                     where=[v >= initial_capital for v in equity_curve],
                     color="#2ecc71", alpha=0.08)
    ax1.fill_between(dates, initial_capital, equity_curve,
                     where=[v < initial_capital for v in equity_curve],
                     color="#e74c3c", alpha=0.08)

    # Metrics annotation
    # 指标注释
    score = result.get("score", 0)
    mdd = result.get("max_drawdown", 0)
    sharpe = result.get("sharpe_ratio", 0)
    total_ret = result.get("total_return", 0)
    trades = result.get("total_trades", 0)
    win_rate = result.get("win_rate", 0)

    textstr = (
        f"Score: {score:.4f}\n"
        f"MDD: {mdd:.2%}\n"
        f"Sharpe: {sharpe:.2f}\n"
        f"Return: {total_ret:.2%}\n"
        f"Trades: {trades}\n"
        f"Win Rate: {win_rate:.2%}"
    )
    props = dict(boxstyle="round,pad=0.4", facecolor="white", alpha=0.85, edgecolor="#cccccc")
    ax1.text(0.02, 0.97, textstr, transform=ax1.transAxes, fontsize=9,
             verticalalignment="top", fontfamily="monospace", bbox=props)

    ax1.set_ylabel("Portfolio Equity")
    ax1.set_title(f"Equity Curve — {strategy_name}", fontsize=13, fontweight="bold")
    ax1.legend(loc="upper right", fontsize=8)
    ax1.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax1.grid(True, alpha=0.2)

    # --- Bottom panel: drawdown ---
    # --- 下图：回撤 ---
    ax2.fill_between(dates, 0, drawdowns, color="#e74c3c", alpha=0.35)
    ax2.plot(dates, drawdowns, color="#c0392b", linewidth=0.8)
    ax2.set_ylabel("Drawdown (%)")
    ax2.set_xlabel("Date")
    ax2.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:.1f}%"))
    ax2.grid(True, alpha=0.2)
    ax2.invert_yaxis()

    # Format x-axis dates
    # 格式化 x 轴日期
    if isinstance(dates[0], datetime):
        ax2.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
        ax2.xaxis.set_major_locator(mdates.AutoDateLocator())
        fig.autofmt_xdate()

    plt.tight_layout()
    plt.savefig(filepath, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Equity chart saved: {filepath}")


# ===========================================================================
# Post-backtest: summary report
# 回测后处理：摘要报告
# ===========================================================================

def save_summary_report(
    results_dir: str,
    timestamp: str,
    strategy_name: str,
    strategy,
    config: dict,
    result: dict,
):
    """Generate a markdown summary report for the current backtest.

    为当前回测生成 Markdown 摘要报告。"""
    safe_name = strategy_name.replace(" ", "_").replace("/", "_").replace("\\", "_")
    filename = f"report_{timestamp}_{safe_name}.md"
    filepath = os.path.join(results_dir, filename)

    # Extract strategy parameters (public attributes)
    # 提取策略参数（公开属性）
    params = {}
    for attr in dir(strategy):
        if attr.startswith("_"):
            continue
        if attr in ("config", "name", "symbols"):
            continue
        val = getattr(strategy, attr, None)
        if callable(val):
            continue
        if isinstance(val, (int, float, str, bool)):
            params[attr] = val

    params_str = "\n".join(f"| `{k}` | `{v}` |" for k, v in params.items())
    if not params_str:
        params_str = "| (none) | |"

    acct_cfg = config.get("account", {})
    metrics_cfg = config.get("metrics", {})

    report = f"""# Strategy Backtest Report

**Generated**: {timestamp}
**Strategy**: {strategy_name}

---

## Configuration

| Parameter | Value |
|-----------|-------|
| Initial Capital | {acct_cfg.get("initial_capital", "N/A"):,.2f} |
| Commission Rate | {acct_cfg.get("commission_rate", 0):.4%} |
| Slippage Rate | {acct_cfg.get("slippage_rate", 0):.4%} |
| Contract Multiplier | {acct_cfg.get("multiplier", 1)} |
| Margin Rate | {acct_cfg.get("margin_rate", 0.10):.1%} |
| Allow Short | {acct_cfg.get("allow_short", True)} |
| MDD Weight | {metrics_cfg.get("mdd_weight", 0.6)} |
| Sharpe Weight | {metrics_cfg.get("sharpe_weight", 0.4)} |
| Risk-Free Rate | {metrics_cfg.get("risk_free_rate", 0.02)} |

## Strategy Parameters

| Parameter | Value |
|-----------|-------|
{params_str}

## Performance Metrics

| Metric | Value |
|--------|-------|
| **Score** | **{result.get("score", 0):.4f}** |
| Max Drawdown | {result.get("max_drawdown", 0):.4f} ({result.get("max_drawdown", 0):.2%}) |
| Sharpe Ratio | {result.get("sharpe_ratio", 0):.2f} |
| Total Return | {result.get("total_return", 0):.4f} ({result.get("total_return", 0):.2%}) |
| Total Trades | {result.get("total_trades", 0)} |
| Round Trips | {result.get("round_trips", 0)} |
| Win Rate | {result.get("win_rate", 0):.4f} ({result.get("win_rate", 0):.2%}) |
| Gross P&L | {result.get("gross_pnl", 0):,.2f} |
| Final Equity | {result.get("final_equity", 0):,.2f} |
| Bars Processed | {result.get("bars_processed", 0):,} / {result.get("total_bars", 0):,} |
| Elapsed Time | {result.get("elapsed_seconds", 0):.1f}s |

## Equity Curve Data

See `equity_{timestamp}_{safe_name}.png` for the equity curve chart.

The equity curve is also available programmatically via the backtest result dict.

---

*Report auto-generated by Trading Autoresearch at {timestamp}*
"""

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"Summary report saved: {filepath}")


# ===========================================================================
# Main
# 主函数
# ===========================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Trading Autoresearch — Single Backtest Run")
    parser.add_argument("--config", default="config.yaml",
                        help="Path to configuration YAML file")
    parser.add_argument("--no-artifacts", action="store_true",
                        help="Skip generating artifacts (strategy copy, chart, report)")
    args = parser.parse_args()

    # Resolve paths relative to this script's directory
    # 相对于脚本目录解析路径
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Generate timestamp for this run
    # 生成本次运行的时间戳
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Ensure results directory exists
    # 确保 results 目录存在
    results_dir = os.path.join(script_dir, "results")
    os.makedirs(results_dir, exist_ok=True)

    # Load config
    # 加载配置
    config_path = os.path.join(script_dir, args.config)
    if not os.path.exists(config_path):
        print(f"ERROR: Config file not found: {config_path}")
        sys.exit(1)

    config = load_config(config_path)
    data_cfg = config.get("data", {})
    acct_cfg = config.get("account", {})
    bt_cfg = config.get("backtest", {})

    # Load data
    # 加载数据
    data_dir = os.path.join(script_dir, data_cfg.get("directory", "./data"))
    symbols = data_cfg.get("symbols", [])
    if not symbols:
        print("ERROR: No symbols configured in config.yaml")
        sys.exit(1)

    print(f"Loading data for symbols: {symbols}")
    print(f"Data directory: {data_dir}")
    data = load_all_data(data_dir, symbols)

    total_bars = sum(len(bars) for bars in data.values())
    if total_bars == 0:
        print("ERROR: No data loaded")
        sys.exit(1)

    # Create account
    # 创建账户
    account = Account(
        initial_capital=acct_cfg.get("initial_capital", 100000.0),
        commission_rate=acct_cfg.get("commission_rate", 0.0003),
        slippage_rate=acct_cfg.get("slippage_rate", 0.0001),
        multiplier=acct_cfg.get("multiplier", 1.0),
        margin_rate=acct_cfg.get("margin_rate", 0.10),
        allow_short=acct_cfg.get("allow_short", True),
    )

    # Create strategy
    # 创建策略
    strategy = create_strategy(config)

    print(f"\nStrategy: {strategy.name}")
    print(f"Initial capital: {account.initial_capital:,.2f}")
    print(f"Commission rate: {account.commission_rate:.4%}")
    print(f"Slippage rate: {account.slippage_rate:.4%}")
    print(f"Multiplier: {account.multiplier}")
    print(f"Margin rate: {account.margin_rate:.1%}")
    print(f"Allow short: {account.allow_short}")
    print(f"Total bars: {total_bars:,}")
    print()

    # Run backtest
    # 运行回测
    warmup = bt_cfg.get("warmup_bars", 50)
    time_budget = bt_cfg.get("time_budget_seconds", 300)

    t0 = time.time()
    result = run_backtest(
        strategy=strategy,
        data=data,
        account=account,
        warmup_bars=warmup,
        time_budget_seconds=time_budget,
    )
    t1 = time.time()

    # Check for errors
    # 检查错误
    if "error" in result:
        print(f"ERROR: {result['error']}")
        sys.exit(1)

    # Print parseable summary (matching karpathy's format)
    # 打印可解析的摘要
    print("---")
    print(f"score:            {result['score']:.4f}")
    print(f"max_drawdown:     {result['max_drawdown']:.4f}")
    print(f"sharpe_ratio:     {result['sharpe_ratio']:.2f}")
    print(f"total_return:     {result['total_return']:.4f}")
    print(f"total_trades:     {result['total_trades']}")
    print(f"win_rate:         {result['win_rate']:.4f}")
    print(f"bars_processed:   {result['bars_processed']}")
    print(f"elapsed_seconds:  {t1 - t0:.1f}")
    print(f"round_trips:      {result.get('round_trips', 0)}")
    print()

    # ------------------------------------------------------------------
    # Post-backtest artifact generation
    # 回测后产出物生成
    # ------------------------------------------------------------------
    if not args.no_artifacts:
        print("Generating post-backtest artifacts...")

        # 1. Save a copy of the strategy script
        # 1. 保存策略脚本副本
        save_strategy_copy(script_dir, results_dir, timestamp)

        # 2. Generate equity curve chart
        # 2. 生成权益曲线图
        equity_curve = result.get("equity_curve", [])
        equity_timestamps = result.get("equity_timestamps", [])
        if equity_curve:
            save_equity_chart(
                results_dir=results_dir,
                timestamp=timestamp,
                strategy_name=strategy.name,
                equity_curve=equity_curve,
                equity_timestamps=equity_timestamps,
                initial_capital=account.initial_capital,
                result=result,
            )

        # 3. Generate summary report
        # 3. 生成摘要报告
        save_summary_report(
            results_dir=results_dir,
            timestamp=timestamp,
            strategy_name=strategy.name,
            strategy=strategy,
            config=config,
            result=result,
        )

        print("Artifacts saved to:", results_dir)
    else:
        print("Artifact generation skipped (--no-artifacts)")


if __name__ == "__main__":
    main()
