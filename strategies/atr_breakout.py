"""
ATR-Adaptive Channel Breakout.

ATR自适应通道突破。
Uses ATR-based stops instead of fixed percentage.
"""

from typing import List

from backtest.account import Bar, Order, Direction, OrderType, Account
from backtest.strategy_base import Strategy


class ATRBreakoutStrategy(Strategy):
    """Channel breakout with ATR-based dynamic stops."""

    def __init__(self, config: dict):
        super().__init__(config)
        self.name = "ATR Breakout"
        self.long_channel = 18
        self.short_channel = 23
        self.atr_period = 14
        self.atr_stop_mult = 2.0
        self.atr_target_mult = 5.0
        self.position_size = 1
        self.max_hold_bars = 360

    def init(self, lookback):
        self._entry_bar = -9999
        self._entry_price = 0.0

    def _atr(self, lookback: List[Bar]) -> float:
        """Simple ATR calculation."""
        period = self.atr_period
        if len(lookback) < period + 1:
            return 0.01
        trs = []
        for i in range(-period, 0):
            b = lookback[i]
            prev = lookback[i - 1]
            tr = max(b.high - b.low, abs(b.high - prev.close), abs(b.low - prev.close))
            trs.append(tr)
        return sum(trs) / len(trs)

    def on_bar(self, i: int, bar: Bar, account: Account,
               lookback: List[Bar]) -> List[Order]:
        min_bars = max(self.long_channel, self.short_channel, self.atr_period) + 2
        if i < min_bars:
            return []

        sym = self.symbol
        pos = self.get_position(account)
        bars_held = i - self._entry_bar if pos is not None else 0

        atr_val = self._atr(lookback)
        atr_pct = atr_val / bar.close  # ATR as percentage of price

        # === EXITS ===
        if pos is not None:
            entry_px = self._entry_price

            if pos.direction == Direction.LONG:
                pnl_pct = (bar.close - entry_px) / entry_px
                stop_dist = self.atr_stop_mult * atr_pct
                target_dist = self.atr_target_mult * atr_pct
                if pnl_pct <= -stop_dist:
                    return [Order(sym, Direction.SHORT, pos.quantity)]
                if pnl_pct >= target_dist:
                    return [Order(sym, Direction.SHORT, pos.quantity)]
            else:
                pnl_pct = (entry_px - bar.close) / entry_px
                stop_dist = self.atr_stop_mult * atr_pct
                target_dist = self.atr_target_mult * atr_pct
                if pnl_pct <= -stop_dist:
                    return [Order(sym, Direction.LONG, pos.quantity)]
                if pnl_pct >= target_dist:
                    return [Order(sym, Direction.LONG, pos.quantity)]

            if bars_held >= self.max_hold_bars:
                if pos.direction == Direction.LONG:
                    return [Order(sym, Direction.SHORT, pos.quantity)]
                else:
                    return [Order(sym, Direction.LONG, pos.quantity)]

        # === ENTRY ===
        if pos is None:
            long_highs = [b.high for b in lookback[-self.long_channel:-1]]
            short_lows = [b.low for b in lookback[-self.short_channel:-1]]

            if bar.close > max(long_highs):
                self._entry_bar = i
                self._entry_price = bar.close
                return [Order(sym, Direction.LONG, self.position_size)]
            elif bar.close < min(short_lows):
                self._entry_bar = i
                self._entry_price = bar.close
                return [Order(sym, Direction.SHORT, self.position_size)]

        return []
