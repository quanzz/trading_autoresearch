"""
Asymmetric Channel Breakout — different stops for long vs short.

非对称通道突破 — 多空使用不同止损止盈。
Market has bullish bias — try tighter stop for shorts.
"""

from typing import List

from backtest.account import Bar, Order, Direction, OrderType, Account
from backtest.strategy_base import Strategy


class AsymmetricBreakoutStrategy(Strategy):
    """Channel breakout with separate long/short risk parameters."""

    def __init__(self, config: dict):
        super().__init__(config)
        self.name = "Asymmetric Breakout"
        self.long_channel = 19
        self.short_channel = 25
        self.position_size = 1
        self.long_stop_pct = 0.02
        self.long_target_pct = 0.05
        self.short_stop_pct = 0.02
        self.short_target_pct = 0.05
        self.max_hold_bars = 360

    def init(self, lookback):
        self._entry_bar = -9999
        self._entry_price = 0.0
        self._entry_dir = None

    def on_bar(self, i: int, bar: Bar, account: Account,
               lookback: List[Bar]) -> List[Order]:
        if i < max(self.long_channel, self.short_channel) + 2:
            return []

        sym = self.symbol
        pos = self.get_position(account)
        bars_held = i - self._entry_bar if pos is not None else 0

        # === EXITS ===
        if pos is not None:
            entry_px = pos.avg_price  # Use actual fill price from account

            if pos.direction == Direction.LONG:
                pnl_pct = (bar.close - entry_px) / entry_px
                if pnl_pct <= -self.long_stop_pct:
                    return [Order(sym, Direction.SHORT, pos.quantity)]
                if pnl_pct >= self.long_target_pct:
                    return [Order(sym, Direction.SHORT, pos.quantity)]
            else:
                pnl_pct = (entry_px - bar.close) / entry_px
                if pnl_pct <= -self.short_stop_pct:
                    return [Order(sym, Direction.LONG, pos.quantity)]
                if pnl_pct >= self.short_target_pct:
                    return [Order(sym, Direction.LONG, pos.quantity)]

            if bars_held >= self.max_hold_bars:
                if pos.direction == Direction.LONG:
                    return [Order(sym, Direction.SHORT, pos.quantity)]
                else:
                    return [Order(sym, Direction.LONG, pos.quantity)]

        # === ENTRY: Different channels for long and short ===
        if pos is None:
            long_highs = [b.high for b in lookback[-self.long_channel:-1]]
            long_ch_high = max(long_highs)
            short_lows = [b.low for b in lookback[-self.short_channel:-1]]
            short_ch_low = min(short_lows)

            if bar.close > long_ch_high:
                self._entry_bar = i
                self._entry_price = bar.close
                return [Order(sym, Direction.LONG, self.position_size)]
            elif bar.close < short_ch_low:
                self._entry_bar = i
                self._entry_price = bar.close
                return [Order(sym, Direction.SHORT, self.position_size)]

        return []
