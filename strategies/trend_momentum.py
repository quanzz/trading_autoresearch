"""
Trend-Filtered Momentum Strategy.

趋势过滤动量策略：仅顺势交易。
Uses EMA trend filter to avoid counter-trend entries,
which should reduce false signals and improve Sharpe.
"""

from typing import List

from backtest.account import Bar, Order, Direction, OrderType, Account
from backtest.strategy_base import Strategy, ema


class TrendMomentumStrategy(Strategy):
    """
    Momentum strategy with EMA trend direction filter.
    LONG only when price > EMA(trend) — uptrend confirmed.
    SHORT only when price < EMA(trend) — downtrend confirmed.

    动量策略 + EMA 趋势方向过滤。
    仅在 EMA(趋势) 方向一致时入场。
    """

    def __init__(self, config: dict):
        super().__init__(config)
        self.name = "Trend Momentum"
        self.momentum_period = 12
        self.trend_ema_period = 50
        self.position_size = 1
        self.stop_loss_pct = 0.02
        self.take_profit_pct = 0.04
        self.max_hold_bars = 360

    def init(self, lookback):
        self._entry_bar = -9999
        self._entry_price = 0.0

    def on_bar(self, i: int, bar: Bar, account: Account,
               lookback: List[Bar]) -> List[Order]:
        min_bars = max(self.momentum_period, self.trend_ema_period) + 2
        if i < min_bars:
            return []

        closes = [b.close for b in lookback]
        sym = self.symbol
        pos = self.get_position(account)
        bars_held = i - self._entry_bar if pos is not None else 0

        # Trend filter: only trade in trend direction
        trend_ema_val = ema(closes, self.trend_ema_period)
        uptrend = closes[-1] > trend_ema_val
        downtrend = closes[-1] < trend_ema_val

        # === EXITS ===
        if pos is not None:
            entry_px = self._entry_price

            if pos.direction == Direction.LONG:
                pnl_pct = (bar.close - entry_px) / entry_px
                if pnl_pct <= -self.stop_loss_pct:
                    return [Order(sym, Direction.SHORT, pos.quantity)]
                if pnl_pct >= self.take_profit_pct:
                    return [Order(sym, Direction.SHORT, pos.quantity)]
                # Trend exit: exit if trend reverses
                if bars_held > 10 and downtrend:
                    return [Order(sym, Direction.SHORT, pos.quantity)]
            else:
                pnl_pct = (entry_px - bar.close) / entry_px
                if pnl_pct <= -self.stop_loss_pct:
                    return [Order(sym, Direction.LONG, pos.quantity)]
                if pnl_pct >= self.take_profit_pct:
                    return [Order(sym, Direction.LONG, pos.quantity)]
                if bars_held > 10 and uptrend:
                    return [Order(sym, Direction.LONG, pos.quantity)]

            if bars_held >= self.max_hold_bars:
                if pos.direction == Direction.LONG:
                    return [Order(sym, Direction.SHORT, pos.quantity)]
                else:
                    return [Order(sym, Direction.LONG, pos.quantity)]

        # === ENTRIES ===
        if pos is None:
            momentum = (closes[-1] - closes[-self.momentum_period - 1]) / closes[-self.momentum_period - 1]

            # Only enter in trend direction
            if momentum > 0.003 and uptrend:
                self._entry_bar = i
                self._entry_price = bar.close
                return [Order(sym, Direction.LONG, self.position_size)]
            elif momentum < -0.003 and downtrend:
                self._entry_bar = i
                self._entry_price = bar.close
                return [Order(sym, Direction.SHORT, self.position_size)]

        return []
