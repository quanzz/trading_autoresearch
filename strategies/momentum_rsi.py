"""
Momentum + RSI Filter Strategy — Long Only.

动量 + RSI 过滤策略 — 仅做多。
Only enters LONG when momentum is positive AND RSI confirms
the market isn't overbought, improving entry timing.
"""

from typing import List

from backtest.account import Bar, Order, Direction, OrderType, Account
from backtest.strategy_base import Strategy, rsi


class MomentumRsiStrategy(Strategy):
    """
    Momentum with RSI entry filter for better timing.
    LONG only when: momentum > threshold AND RSI < rsi_max (not overbought).
    This avoids buying after the move has already exhausted.

    动量 + RSI 入场过滤提升择时。
    仅当动量向上且 RSI 未超买时做多，避免追高。
    """

    def __init__(self, config: dict):
        super().__init__(config)
        self.name = "Momentum + RSI"
        self.momentum_period = 16
        self.rsi_period = 14
        self.rsi_max = 60          # Only enter when RSI < 60 (not overbought)
        self.position_size = 1
        self.stop_loss_pct = 0.02
        self.take_profit_pct = 0.05
        self.max_hold_bars = 360
        self.entry_threshold = 0.0025
        self.exit_threshold = 0.003

    def init(self, lookback):
        self._entry_bar = -9999
        self._entry_price = 0.0

    def on_bar(self, i: int, bar: Bar, account: Account,
               lookback: List[Bar]) -> List[Order]:
        min_bars = max(self.momentum_period, self.rsi_period) + 2
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
                momentum = (closes[-1] - closes[-self.momentum_period - 1]) / closes[-self.momentum_period - 1]
                if bars_held > 10 and momentum < -self.exit_threshold:
                    return [Order(sym, Direction.SHORT, pos.quantity)]
            else:
                pnl_pct = (entry_px - bar.close) / entry_px
                if pnl_pct <= -self.stop_loss_pct:
                    return [Order(sym, Direction.LONG, pos.quantity)]
                if pnl_pct >= self.take_profit_pct:
                    return [Order(sym, Direction.LONG, pos.quantity)]
                momentum = (closes[-1] - closes[-self.momentum_period - 1]) / closes[-self.momentum_period - 1]
                if bars_held > 10 and momentum > self.exit_threshold:
                    return [Order(sym, Direction.LONG, pos.quantity)]

            if bars_held >= self.max_hold_bars:
                if pos.direction == Direction.LONG:
                    return [Order(sym, Direction.SHORT, pos.quantity)]
                else:
                    return [Order(sym, Direction.LONG, pos.quantity)]

        # === ENTRIES: Momentum + RSI filter, LONG ONLY ===
        if pos is None:
            momentum = (closes[-1] - closes[-self.momentum_period - 1]) / closes[-self.momentum_period - 1]
            rsi_val = rsi(closes, self.rsi_period)

            if momentum > self.entry_threshold and rsi_val < self.rsi_max:
                self._entry_bar = i
                self._entry_price = bar.close
                return [Order(sym, Direction.LONG, self.position_size)]

        return []
