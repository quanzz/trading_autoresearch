"""
Bar-by-bar backtest engine.
FIXED — do not modify. The agent edits strategy.py instead.
"""

import time
from typing import Dict, List, Optional

from .account import Account, Bar, Order, Direction, OrderType
from .metrics import compute_all_metrics


def run_backtest(
    strategy,
    data: Dict[str, List[Bar]],
    account: Account,
    warmup_bars: int = 50,
    time_budget_seconds: float = 300.0,
) -> dict:
    """
    Run a bar-by-bar backtest.

    Args:
        strategy: Strategy instance with on_bar(i, bar, account, lookback) method.
        data: Dict mapping symbol → list of Bar objects.
        account: Account instance with initial capital and fee settings.
        warmup_bars: Number of initial bars to skip (for indicator warmup).
        time_budget_seconds: Maximum wall-clock time. Exits early if exceeded.

    Returns:
        Dict with metrics, account summary, and timing info.
    """
    symbols = list(data.keys())
    if not symbols:
        return {"error": "No data provided"}

    primary_symbol = symbols[0]
    bars = data[primary_symbol]
    n_bars = len(bars)

    if n_bars <= warmup_bars:
        return {"error": f"Not enough bars ({n_bars}) for warmup ({warmup_bars})"}

    t_start = time.time()
    strategy.symbols = symbols  # Expose symbols to strategy
    strategy.init(bars[:warmup_bars])

    pending_orders: List[Order] = []
    bar_idx = 0
    last_progress = -1

    for i in range(warmup_bars, n_bars - 1):
        bar_idx = i
        current_bar = bars[i]
        next_bar = bars[i + 1]  # for next-bar-open execution
        lookback = bars[:i + 1]

        # Execute pending orders from previous bar at this bar's open
        for order in pending_orders:
            fill_price = current_bar.open
            account.execute_order(order, fill_price, current_bar.date)

        # Get current prices for mark-to-market
        prices = {symbol: current_bar.close for symbol in symbols}
        account.mark_to_market(current_bar.date, prices)

        # Get new orders from strategy
        new_orders = strategy.on_bar(i, current_bar, account, lookback)
        pending_orders = []
        if new_orders:
            for order in new_orders:
                if isinstance(order, Order):
                    pending_orders.append(order)

        # Progress indicator (every 10%)
        pct = (i - warmup_bars) * 100 // (n_bars - warmup_bars - 1)
        if pct % 10 == 0 and pct != last_progress:
            last_progress = pct
            elapsed = time.time() - t_start
            print(f"\r  Backtesting... {pct}% ({i}/{n_bars} bars, "
                  f"{elapsed:.1f}s elapsed)", end="", flush=True)

        # Check time budget
        if time.time() - t_start > time_budget_seconds:
            print(f"\n  Time budget reached after {i} bars")
            break

    # Execute any remaining pending orders at last bar's close
    if pending_orders and bar_idx < n_bars - 1:
        last_bar = bars[-1]
        for order in pending_orders:
            account.execute_order(order, last_bar.close, last_bar.date)

    # Final mark-to-market
    if bar_idx > 0:
        final_bar = bars[min(bar_idx, n_bars - 1)]
        prices = {symbol: final_bar.close for symbol in symbols}
        account.mark_to_market(final_bar.date, prices)

    t_end = time.time()

    # Close any remaining positions at final price to compute realized P&L
    _close_all_positions(account, bars[min(bar_idx, n_bars - 1)])

    print()  # newline after progress

    # Compute results
    acct_summary = account.summary()
    metrics = compute_all_metrics(account.equity_curve)

    return {
        **metrics,
        **acct_summary,
        "bars_processed": bar_idx - warmup_bars + 1,
        "total_bars": n_bars,
        "elapsed_seconds": t_end - t_start,
        "equity_curve": account.equity_curve,
        "equity_timestamps": account._equity_timestamps,
    }


def _close_all_positions(account: Account, final_bar: Bar):
    """Close all open positions at the final bar's close price."""
    for symbol, pos in list(account.positions.items()):
        if pos.direction == Direction.LONG:
            close_order = Order(
                symbol=symbol,
                direction=Direction.SHORT,
                quantity=pos.quantity,
                order_type=OrderType.MARKET,
            )
        else:
            close_order = Order(
                symbol=symbol,
                direction=Direction.LONG,
                quantity=pos.quantity,
                order_type=OrderType.MARKET,
            )
        account.execute_order(close_order, final_bar.close, final_bar.date)
