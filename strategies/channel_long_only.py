"""
Channel Breakout — Long Only variant.
通道突破 — 仅做多。
"""

from typing import List
from backtest.account import Bar, Order, Direction, OrderType, Account
from backtest.strategy_base import Strategy


class ChannelLongOnlyStrategy(Strategy):
    def __init__(self, config: dict):
        super().__init__(config)
        self.name = "Channel Long Only"
        self.channel_period = 18
        self.position_size = 1
        self.stop_loss_pct = 0.02
        self.take_profit_pct = 0.05
        self.max_hold_bars = 360

    def init(self, lookback):
        self._entry_bar = -9999

    def on_bar(self, i: int, bar: Bar, account: Account,
               lookback: List[Bar]) -> List[Order]:
        if i < self.channel_period + 2:
            return []
        sym = self.symbol
        pos = self.get_position(account)
        bars_held = i - self._entry_bar if pos is not None else 0

        if pos is not None:
            entry_px = pos.avg_price
            if pos.direction == Direction.LONG:
                pnl_pct = (bar.close - entry_px) / entry_px
                if pnl_pct <= -self.stop_loss_pct:
                    return [Order(sym, Direction.SHORT, pos.quantity)]
                if pnl_pct >= self.take_profit_pct:
                    return [Order(sym, Direction.SHORT, pos.quantity)]
            if bars_held >= self.max_hold_bars:
                return [Order(sym, Direction.SHORT, pos.quantity)]

        if pos is None:
            highs = [b.high for b in lookback[-self.channel_period:-1]]
            if bar.close > max(highs):
                self._entry_bar = i
                return [Order(sym, Direction.LONG, self.position_size)]
        return []
