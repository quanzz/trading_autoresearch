"""
Bollinger Band Breakout Strategy — Long Only.

布林带突破策略 — 仅做多。
Enter LONG when close breaks above the upper Bollinger Band.
Uses standard deviation for adaptive channel width.
"""

from typing import List

from backtest.account import Bar, Order, Direction, OrderType, Account
from backtest.strategy_base import Strategy, sma, stddev


class BBBreakoutStrategy(Strategy):
    """
    Bollinger Band breakout — LONG only.
    Buy when close > upper band (sma + k * stddev).
    Adaptive channel width based on volatility.

    布林带突破 — 仅做多。
    收盘价突破上轨时做多。通道宽度随波动率自适应。
    """

    def __init__(self, config: dict):
        super().__init__(config)
        self.name = "BB Breakout"
        self.bb_period = 20
        self.bb_std = 2.0
        self.position_size = 1
        self.stop_loss_pct = 0.02
        self.take_profit_pct = 0.05
        self.max_hold_bars = 360

    def init(self, lookback):
        self._entry_bar = -9999
        self._entry_price = 0.0

    def on_bar(self, i: int, bar: Bar, account: Account,
               lookback: List[Bar]) -> List[Order]:
        if i < self.bb_period + 2:
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

        # === ENTRY: Long on BB upper band breakout ===
        if pos is None:
            mid = sma(closes[:-1], self.bb_period)  # exclude current bar
            std = stddev(closes[:-1], self.bb_period)
            upper = mid + self.bb_std * std

            if bar.close > upper:
                self._entry_bar = i
                self._entry_price = bar.close
                return [Order(sym, Direction.LONG, self.position_size)]

        return []
