"""
Performance metrics: Max Drawdown, Sharpe Ratio, and combined score.
FIXED — do not modify. The agent edits strategy.py instead.
"""

import math
from typing import List

import numpy as np


def max_drawdown(equity_curve: List[float]) -> float:
    """
    Compute Maximum Drawdown from an equity curve.
    MDD = max((peak - trough) / peak) over the period.
    Returns a value in [0, 1]. 0 = no drawdown, 1 = total loss.
    """
    if len(equity_curve) < 2:
        return 0.0

    peak = equity_curve[0]
    mdd = 0.0

    for value in equity_curve:
        if value > peak:
            peak = value
        if peak > 0:
            dd = (peak - value) / peak
            if dd > mdd:
                mdd = dd

    return mdd


def sharpe_ratio(equity_curve: List[float], risk_free_rate: float = 0.02,
                 periods_per_year: int = 252) -> float:
    """
    Compute annualized Sharpe Ratio from an equity curve.
    Uses daily returns aggregated from the equity curve.

    Args:
        equity_curve: List of equity values (minute-level).
        risk_free_rate: Annual risk-free rate (default 2%).
        periods_per_year: Trading days per year (default 252).

    Returns:
        Annualized Sharpe ratio, or 0.0 if insufficient data.
    """
    if len(equity_curve) < 2:
        return 0.0

    equity = np.array(equity_curve)

    # Aggregate to daily returns
    # We don't know exact day boundaries, so we resample by taking
    # every Nth point where N approximates daily bars.
    # A typical trading day has ~240 minutes (4 hours).
    minute_bars_per_day = 240

    daily_equity = equity[::minute_bars_per_day]
    if len(daily_equity) < 2:
        # Not enough data for daily — use all points but scale annualization
        daily_equity = equity
        periods_per_year = 252 * minute_bars_per_day

    daily_returns = np.diff(daily_equity) / daily_equity[:-1]

    if len(daily_returns) < 2:
        return 0.0

    mean_return = np.mean(daily_returns)
    std_return = np.std(daily_returns, ddof=1)

    if std_return == 0:
        return 0.0

    # Annualize
    annualized_return = mean_return * periods_per_year
    annualized_std = std_return * math.sqrt(periods_per_year)

    excess_return = annualized_return - risk_free_rate
    return excess_return / annualized_std


def combined_score(mdd: float, sharpe: float, mdd_weight: float = 0.6,
                   sharpe_weight: float = 0.4) -> float:
    """
    Compute weighted combined score.
    Higher is better.

    MDD contributes negatively (lower MDD → higher score):
      mdd_term = -mdd_weight * mdd

    Sharpe contributes positively (higher Sharpe → higher score),
    capped at 3.0 to prevent outlier domination:
      sharpe_term = sharpe_weight * min(sharpe, 3.0) / 3.0

    Score range: [-mdd_weight, sharpe_weight] approximately.
    """
    mdd_term = -mdd_weight * mdd
    sharpe_term = sharpe_weight * min(max(sharpe, -3.0), 3.0) / 3.0
    return mdd_term + sharpe_term


def compute_all_metrics(equity_curve: List[float], risk_free_rate: float = 0.02,
                        mdd_weight: float = 0.6,
                        sharpe_weight: float = 0.4) -> dict:
    """
    Compute all backtest metrics from an equity curve.
    Returns a dict with all metrics.
    """
    mdd = max_drawdown(equity_curve)
    sharpe = sharpe_ratio(equity_curve, risk_free_rate)
    score = combined_score(mdd, sharpe, mdd_weight, sharpe_weight)

    return {
        "score": score,
        "max_drawdown": mdd,
        "sharpe_ratio": sharpe,
    }
