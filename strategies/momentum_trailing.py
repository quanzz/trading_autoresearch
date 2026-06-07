"""
Momentum Strategy with Trailing Stop.

动量策略 + 移动止损。
Once in profit, activates a trailing stop to protect gains
and capture more of the big moves.
"""

from typing import List

from backtest.account import Bar, Order, Direction, OrderType, Account
from backtest.strategy_base import Strategy


class MomentumTrailingStrategy(Strategy):
    """
    Momentum entry with trailing stop exit management.
    Trailing stop activates after trailing_activate_pct profit,
    then trails at trailing_distance_pct behind the best price.

    动量入场 + 移动止损出场管理。
    盈利达到激活阈值后启动移动止损，追踪最佳价格。
    """

    def __init__(self, config: dict):
        super().__init__(config)
        self.name = "Momentum Trailing"
        self.momentum_period = 18
        self.position_size = 1
        self.stop_loss_pct = 0.02
        self.take_profit_pct = 0.05
        self.max_hold_bars = 360
        self.entry_threshold = 0.003
        self.exit_threshold = 0.003
        # Trailing stop params
        self.trailing_activate_pct = 0.02   # Activate trailing after 2% profit
        self.trailing_distance_pct = 0.015  # Trail 1.5% behind best price

    def init(self, lookback):
        self._entry_bar = -9999
        self._entry_price = 0.0
        self._best_price = 0.0
        self._trailing_active = False

    def on_bar(self, i: int, bar: Bar, account: Account,
               lookback: List[Bar]) -> List[Order]:
        if i < self.momentum_period + 2:
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

                # Update best price and trailing stop
                if bar.close > self._best_price:
                    self._best_price = bar.close
                if pnl_pct >= self.trailing_activate_pct:
                    self._trailing_active = True

                # Trailing stop exit
                if self._trailing_active:
                    trail_stop = self._best_price * (1.0 - self.trailing_distance_pct)
                    if bar.close <= trail_stop:
                        return [Order(sym, Direction.SHORT, pos.quantity)]

                # Hard stop
                if pnl_pct <= -self.stop_loss_pct:
                    return [Order(sym, Direction.SHORT, pos.quantity)]
                # Take profit
                if pnl_pct >= self.take_profit_pct:
                    return [Order(sym, Direction.SHORT, pos.quantity)]
                # Momentum exit (secondary)
                momentum = (closes[-1] - closes[-self.momentum_period - 1]) / closes[-self.momentum_period - 1]
                if bars_held > 10 and momentum < -self.exit_threshold:
                    return [Order(sym, Direction.SHORT, pos.quantity)]
            else:
                pnl_pct = (entry_px - bar.close) / entry_px

                if bar.close < self._best_price or self._best_price == 0:
                    self._best_price = bar.close
                if pnl_pct >= self.trailing_activate_pct:
                    self._trailing_active = True

                if self._trailing_active:
                    trail_stop = self._best_price * (1.0 + self.trailing_distance_pct)
                    if bar.close >= trail_stop:
                        return [Order(sym, Direction.LONG, pos.quantity)]

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

        # === ENTRIES ===
        if pos is None:
            momentum = (closes[-1] - closes[-self.momentum_period - 1]) / closes[-self.momentum_period - 1]

            if momentum > self.entry_threshold:
                self._entry_bar = i
                self._entry_price = bar.close
                self._best_price = bar.close
                self._trailing_active = False
                return [Order(sym, Direction.LONG, self.position_size)]
            elif momentum < -self.entry_threshold:
                self._entry_bar = i
                self._entry_price = bar.close
                self._best_price = bar.close
                self._trailing_active = False
                return [Order(sym, Direction.SHORT, self.position_size)]

        return []
