"""
Backtest framework for Trading Autoresearch.
Provides bar-by-bar simulation with account, metrics, and strategy tools.
"""

from .account import Account, Bar, Order, Trade, Position, Direction, OrderType
from .engine import run_backtest
from .metrics import max_drawdown, sharpe_ratio, combined_score, compute_all_metrics

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
]
