"""
Dual Momentum Strategy — fast + slow momentum confirmation.

双动量策略 — 快慢动量双重确认。
Only enters when both fast and slow momentum agree on direction,
filtering out short-term noise and improving signal quality.
"""

from typing import List

from backtest.account import Bar, Order, Direction, OrderType, Account
from backtest.strategy_base import Strategy


class DualMomentumStrategy(Strategy):
    """
    Dual timeframe momentum confirmation.
    Both fast and slow momentum must agree for entry.
    This filters out false signals from short-term noise.

    双时间框架动量确认。
    快慢动量方向一致时才入场，过滤短期噪音。
    """

    def __init__(self, config: dict):
        super().__init__(config)
        self.name = "Dual Momentum"
        self.fast_period = 6
        self.slow_period = 18
        self.position_size = 1
        self.stop_loss_pct = 0.02
        self.take_profit_pct = 0.05
        self.max_hold_bars = 360
        self.entry_threshold = 0.003
        self.exit_threshold = 0.003

    def init(self, lookback):
        self._entry_bar = -9999
        self._entry_price = 0.0

    def on_bar(self, i: int, bar: Bar, account: Account,
               lookback: List[Bar]) -> List[Order]:
        min_bars = max(self.fast_period, self.slow_period) + 2
        if i < min_bars:
            return []

        closes = [b.close for b in lookback]
        sym = self.symbol
        pos = self.get_position(account)
        bars_held = i - self._entry_bar if pos is not None else 0

        # === EXITS ===
        if pos is not None:
            entry_px = self._entry_price

            if pos.direction == Direction.LONG:
                pnl_pct = (bar.close - entry_px) / entry_px
                if pnl_pct <= -self.stop_loss_pct:
                    return [Order(sym, Direction.SHORT, pos.quantity)]
                if pnl_pct >= self.take_profit_pct:
                    return [Order(sym, Direction.SHORT, pos.quantity)]
                # Momentum exit: exit when slow momentum reverses
                slow_mom = (closes[-1] - closes[-self.slow_period - 1]) / closes[-self.slow_period - 1]
                if bars_held > 10 and slow_mom < -self.exit_threshold:
                    return [Order(sym, Direction.SHORT, pos.quantity)]
            else:
                pnl_pct = (entry_px - bar.close) / entry_px
                if pnl_pct <= -self.stop_loss_pct:
                    return [Order(sym, Direction.LONG, pos.quantity)]
                if pnl_pct >= self.take_profit_pct:
                    return [Order(sym, Direction.LONG, pos.quantity)]
                slow_mom = (closes[-1] - closes[-self.slow_period - 1]) / closes[-self.slow_period - 1]
                if bars_held > 10 and slow_mom > self.exit_threshold:
                    return [Order(sym, Direction.LONG, pos.quantity)]

            if bars_held >= self.max_hold_bars:
                if pos.direction == Direction.LONG:
                    return [Order(sym, Direction.SHORT, pos.quantity)]
                else:
                    return [Order(sym, Direction.LONG, pos.quantity)]

        # === ENTRIES: dual momentum confirmation ===
        if pos is None:
            fast_mom = (closes[-1] - closes[-self.fast_period - 1]) / closes[-self.fast_period - 1]
            slow_mom = (closes[-1] - closes[-self.slow_period - 1]) / closes[-self.slow_period - 1]

            # Both fast and slow momentum must agree and exceed threshold
            if fast_mom > self.entry_threshold and slow_mom > self.entry_threshold:
                self._entry_bar = i
                self._entry_price = bar.close
                return [Order(sym, Direction.LONG, self.position_size)]
            elif fast_mom < -self.entry_threshold and slow_mom < -self.entry_threshold:
                self._entry_bar = i
                self._entry_price = bar.close
                return [Order(sym, Direction.SHORT, self.position_size)]

        return []
