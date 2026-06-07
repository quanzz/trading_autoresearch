"""
Pullback Strategy — Buy oversold dips in uptrend.

回调买入策略 — 在上升趋势中买入超卖回调。
Long when RSI oversold AND price above SMA (uptrend confirmed).
"""

from typing import List

from backtest.account import Bar, Order, Direction, OrderType, Account
from backtest.strategy_base import Strategy, sma, rsi


class PullbackStrategy(Strategy):
    """
    Buy pullbacks in an uptrend.
    LONG when RSI < oversold AND close > SMA(trend) — dip in uptrend.
    SHORT when RSI > overbought AND close < SMA(trend) — rally in downtrend.

    上升趋势中买入回调。下跌趋势中卖出反弹。
    """

    def __init__(self, config: dict):
        super().__init__(config)
        self.name = "Pullback"
        self.rsi_period = 14
        self.rsi_oversold = 35
        self.rsi_overbought = 65
        self.rsi_exit_long = 55
        self.rsi_exit_short = 45
        self.trend_period = 50
        self.position_size = 1
        self.stop_loss_pct = 0.02
        self.take_profit_pct = 0.05
        self.max_hold_bars = 360

    def init(self, lookback):
        self._entry_bar = -9999
        self._entry_price = 0.0

    def on_bar(self, i: int, bar: Bar, account: Account,
               lookback: List[Bar]) -> List[Order]:
        min_bars = max(self.rsi_period, self.trend_period) + 2
        if i < min_bars:
            return []

        closes = [b.close for b in lookback]
        sym = self.symbol
        pos = self.get_position(account)
        bars_held = i - self._entry_bar if pos is not None else 0

        rsi_val = rsi(closes, self.rsi_period)
        trend_sma = sma(closes, self.trend_period)

        # === EXITS ===
        if pos is not None:
            entry_px = self._entry_price

            if pos.direction == Direction.LONG:
                pnl_pct = (bar.close - entry_px) / entry_px
                if pnl_pct <= -self.stop_loss_pct:
                    return [Order(sym, Direction.SHORT, pos.quantity)]
                if pnl_pct >= self.take_profit_pct:
                    return [Order(sym, Direction.SHORT, pos.quantity)]
                # Exit when RSI recovers
                if bars_held > 5 and rsi_val > self.rsi_exit_long:
                    return [Order(sym, Direction.SHORT, pos.quantity)]
            else:
                pnl_pct = (entry_px - bar.close) / entry_px
                if pnl_pct <= -self.stop_loss_pct:
                    return [Order(sym, Direction.LONG, pos.quantity)]
                if pnl_pct >= self.take_profit_pct:
                    return [Order(sym, Direction.LONG, pos.quantity)]
                if bars_held > 5 and rsi_val < self.rsi_exit_short:
                    return [Order(sym, Direction.LONG, pos.quantity)]

            if bars_held >= self.max_hold_bars:
                if pos.direction == Direction.LONG:
                    return [Order(sym, Direction.SHORT, pos.quantity)]
                else:
                    return [Order(sym, Direction.LONG, pos.quantity)]

        # === ENTRIES: Pullback in trend direction ===
        if pos is None:
            uptrend = closes[-1] > trend_sma
            downtrend = closes[-1] < trend_sma

            # Long: RSI oversold in uptrend
            if rsi_val < self.rsi_oversold and uptrend:
                self._entry_bar = i
                self._entry_price = bar.close
                return [Order(sym, Direction.LONG, self.position_size)]
            # Short: RSI overbought in downtrend
            elif rsi_val > self.rsi_overbought and downtrend:
                self._entry_bar = i
                self._entry_price = bar.close
                return [Order(sym, Direction.SHORT, self.position_size)]

        return []
