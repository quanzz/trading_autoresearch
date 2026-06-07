"""
Enhanced Momentum Strategy with Risk Management.

增强动量策略（含风险管理）。
"""

from typing import List

from backtest.account import Bar, Order, Direction, OrderType, Account
from backtest.strategy_base import Strategy, sma


class EnhancedMomentumStrategy(Strategy):
    """
    Momentum strategy with stop-loss, take-profit, and volume filter.
    Uses shorter lookback for faster signal response.

    动量策略 + 止损止盈 + 成交量过滤。
    使用更短回顾期以获得更快的信号响应。
    """

    def __init__(self, config: dict):
        super().__init__(config)
        self.name = "Enhanced Momentum"
        self.momentum_period = 8
        self.volume_period = 15
        self.volume_threshold = 1.1
        self.position_size = 1
        self.stop_loss_pct = 0.015
        self.take_profit_pct = 0.03
        self.max_hold_bars = 240

    def init(self, lookback):
        self._entry_bar = -9999
        self._entry_price = 0.0

    def on_bar(self, i: int, bar: Bar, account: Account,
               lookback: List[Bar]) -> List[Order]:
        min_bars = max(self.momentum_period, self.volume_period) + 2
        if i < min_bars:
            return []

        closes = [b.close for b in lookback]
        volumes = [b.volume for b in lookback]

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
                # Momentum exit: close if momentum reverses
                momentum = (closes[-1] - closes[-self.momentum_period - 1]) / closes[-self.momentum_period - 1]
                if bars_held > 10 and momentum < -0.003:
                    return [Order(sym, Direction.SHORT, pos.quantity)]
            else:
                pnl_pct = (entry_px - bar.close) / entry_px
                if pnl_pct <= -self.stop_loss_pct:
                    return [Order(sym, Direction.LONG, pos.quantity)]
                if pnl_pct >= self.take_profit_pct:
                    return [Order(sym, Direction.LONG, pos.quantity)]
                momentum = (closes[-1] - closes[-self.momentum_period - 1]) / closes[-self.momentum_period - 1]
                if bars_held > 10 and momentum > 0.003:
                    return [Order(sym, Direction.LONG, pos.quantity)]

            if bars_held >= self.max_hold_bars:
                if pos.direction == Direction.LONG:
                    return [Order(sym, Direction.SHORT, pos.quantity)]
                else:
                    return [Order(sym, Direction.LONG, pos.quantity)]

        # === ENTRIES ===
        if pos is None:
            momentum = (closes[-1] - closes[-self.momentum_period - 1]) / closes[-self.momentum_period - 1]
            avg_volume = sma(volumes, self.volume_period)
            high_volume = volumes[-1] > avg_volume * self.volume_threshold

            if momentum > 0.003 and high_volume:
                self._entry_bar = i
                self._entry_price = bar.close
                return [Order(sym, Direction.LONG, self.position_size)]
            elif momentum < -0.003 and high_volume:
                self._entry_bar = i
                self._entry_price = bar.close
                return [Order(sym, Direction.SHORT, self.position_size)]

        return []
