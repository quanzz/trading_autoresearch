"""
Bollinger Bands Mean Reversion Strategy.

布林带均值回归策略。
"""

from typing import List

from backtest.account import Bar, Order, Direction, OrderType, Account
from backtest.strategy_base import Strategy, sma, stddev


class BollingerBreakoutStrategy(Strategy):
    """
    Bollinger Bands mean reversion strategy.
    BUY when price closes below lower band (oversold).
    SELL when price closes above upper band (overbought).
    Exit when price crosses back through the middle band.

    布林带均值回归策略。
    价格收盘低于下轨时做多（超卖）。
    价格收盘高于上轨时做空（超买）。
    价格穿越中轨时平仓。
    """

    def __init__(self, config: dict):
        super().__init__(config)
        self.name = "Bollinger Bands"
        self.period = 20
        self.std_multiplier = 2.0
        self.position_size = 1

    def on_bar(self, i: int, bar: Bar, account: Account,
               lookback: List[Bar]) -> List[Order]:
        if i < self.period:
            return []

        closes = [b.close for b in lookback]
        ma = sma(closes, self.period)
        std = stddev(closes, self.period)
        upper = ma + self.std_multiplier * std
        lower = ma - self.std_multiplier * std

        sym = self.symbol
        pos = self.get_position(account)

        # Mean reversion logic
        # 均值回归逻辑
        if bar.close <= lower:
            # Price at lower band — go long
            # 价格触及下轨 — 做多
            if pos is not None and pos.direction == Direction.SHORT:
                return [
                    Order(sym, Direction.LONG, pos.quantity),
                    Order(sym, Direction.LONG, self.position_size),
                ]
            elif pos is None:
                return [Order(sym, Direction.LONG, self.position_size)]

        elif bar.close >= upper:
            # Price at upper band — go short
            # 价格触及上轨 — 做空
            if pos is not None and pos.direction == Direction.LONG:
                return [
                    Order(sym, Direction.SHORT, pos.quantity),
                    Order(sym, Direction.SHORT, self.position_size),
                ]
            elif pos is None:
                return [Order(sym, Direction.SHORT, self.position_size)]

        # Exit when price crosses middle band
        # 价格穿越中轨时平仓
        prev_close = closes[-2] if len(closes) >= 2 else bar.close
        if pos is not None:
            if pos.direction == Direction.LONG and prev_close < ma <= bar.close:
                return [Order(sym, Direction.SHORT, pos.quantity)]
            elif pos.direction == Direction.SHORT and prev_close > ma >= bar.close:
                return [Order(sym, Direction.LONG, pos.quantity)]

        return []
