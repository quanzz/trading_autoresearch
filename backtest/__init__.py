"""
Backtest framework for Trading Autoresearch.
Provides bar-by-bar simulation with account, metrics, and strategy tools.

Trading Autoresearch 回测框架。
提供逐 K 线模拟，包含账户、指标和策略工具。
"""

from .account import Account, Bar, Order, Trade, Position, Direction, OrderType
from .engine import run_backtest
from .metrics import max_drawdown, sharpe_ratio, combined_score, compute_all_metrics
from .strategy_base import Strategy, sma, ema, stddev, rsi

__all__ = [
    "Account",
    "Bar",
    "Order",
    "Trade",
    "Position",
    "Direction",
    "OrderType",
    "run_backtest",
    "max_drawdown",
    "sharpe_ratio",
    "combined_score",
    "compute_all_metrics",
    "Strategy",
    "sma",
    "ema",
    "stddev",
    "rsi",
]
