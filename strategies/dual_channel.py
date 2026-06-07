"""
Dual Channel Breakout Strategy.

双通道突破策略。
Use long channel for trend direction, short channel for entry timing.
"""

from typing import List

from backtest.account import Bar, Order, Direction, OrderType, Account
from backtest.strategy_base import Strategy


class DualChannelStrategy(Strategy):
    """
    Dual Donchian channel breakout.
    Long channel (50) determines trend, short channel (20) times entries.
    Only trade in the direction of the longer trend.

    双通道突破：长通道定趋势，短通道定入场时机。顺势交易。
    """

    def __init__(self, config: dict):
        super().__init__(config)
        self.name = "Dual Channel"
        self.short_period = 20
        self.long_period = 50
        self.position_size = 1
        self.stop_loss_pct = 0.02
        self.take_profit_pct = 0.05
        self.max_hold_bars = 360

    def init(self, lookback):
        self._entry_bar = -9999
        self._entry_price = 0.0

    def on_bar(self, i: int, bar: Bar, account: Account,
               lookback: List[Bar]) -> List[Order]:
        min_bars = self.long_period + 2
        if i < min_bars:
            return []

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
            else:
                pnl_pct = (entry_px - bar.close) / entry_px
                if pnl_pct <= -self.stop_loss_pct:
                    return [Order(sym, Direction.LONG, pos.quantity)]
                if pnl_pct >= self.take_profit_pct:
                    return [Order(sym, Direction.LONG, pos.quantity)]

            if bars_held >= self.max_hold_bars:
                if pos.direction == Direction.LONG:
                    return [Order(sym, Direction.SHORT, pos.quantity)]
                else:
                    return [Order(sym, Direction.LONG, pos.quantity)]

        # === ENTRY: Trend-aligned channel breakout ===
        if pos is None:
            # Long channel for trend direction
            long_highs = [b.high for b in lookback[-self.long_period:-1]]
            long_lows = [b.low for b in lookback[-self.long_period:-1]]
            long_mid = (max(long_highs) + min(long_lows)) / 2.0

            # Short channel for entry
            short_highs = [b.high for b in lookback[-self.short_period:-1]]
            short_lows = [b.low for b in lookback[-self.short_period:-1]]
            short_high = max(short_highs)
            short_low = min(short_lows)

            uptrend = bar.close > long_mid
            downtrend = bar.close < long_mid

            # Long breakout in uptrend
            if bar.close > short_high and uptrend:
                self._entry_bar = i
                self._entry_price = bar.close
                return [Order(sym, Direction.LONG, self.position_size)]
            # Short breakout in downtrend
            elif bar.close < short_low and downtrend:
                self._entry_bar = i
                self._entry_price = bar.close
                return [Order(sym, Direction.SHORT, self.position_size)]

        return []
