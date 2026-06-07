"""
Pure Momentum Strategy — minimal, clean trend following.

纯动量策略 — 极简趋势跟踪。
Entry on momentum signal, exit on stop/target/timeout only.
No momentum exit, no volume filter, no trend filter.
"""

from typing import List

from backtest.account import Bar, Order, Direction, OrderType, Account
from backtest.strategy_base import Strategy


class PureMomentumStrategy(Strategy):
    """
    Bare-bones momentum trend following.
    LONG on positive momentum, SHORT on negative momentum.
    Exits: stop-loss, take-profit, or max hold timeout only.
    No intermediate exits — let winners run.

    极简动量趋势跟踪。
    动量向上做多，动量向下做空。
    仅止损/止盈/超时出场，无中间出场——让利润奔跑。
    """

    def __init__(self, config: dict):
        super().__init__(config)
        self.name = "Pure Momentum"
        self.momentum_period = 12
        self.position_size = 1
        self.stop_loss_pct = 0.02
        self.take_profit_pct = 0.04
        self.max_hold_bars = 360

    def init(self, lookback):
        self._entry_bar = -9999
        self._entry_price = 0.0

    def on_bar(self, i: int, bar: Bar, account: Account,
               lookback: List[Bar]) -> List[Order]:
        if i < self.momentum_period + 2:
            return []

        closes = [b.close for b in lookback]
        sym = self.symbol
        pos = self.get_position(account)
        bars_held = i - self._entry_bar if pos is not None else 0

        # === EXITS: stop-loss, take-profit, timeout ONLY ===
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

        # === ENTRIES: pure momentum signal ===
        if pos is None:
            momentum = (closes[-1] - closes[-self.momentum_period - 1]) / closes[-self.momentum_period - 1]

            if momentum > 0.003:
                self._entry_bar = i
                self._entry_price = bar.close
                return [Order(sym, Direction.LONG, self.position_size)]
            elif momentum < -0.003:
                self._entry_bar = i
                self._entry_price = bar.close
                return [Order(sym, Direction.SHORT, self.position_size)]

        return []
