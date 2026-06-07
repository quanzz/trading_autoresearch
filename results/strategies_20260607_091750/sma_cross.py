"""
SMA Crossover Strategy.

SMA 交叉策略。
"""

from typing import List

from backtest.account import Bar, Order, Direction, OrderType, Account
from backtest.strategy_base import Strategy, sma


class SmaCrossStrategy(Strategy):
    """
    Simple Moving Average crossover strategy.
    BUY when fast MA crosses above slow MA.
    SELL when fast MA crosses below slow MA.
    Always in the market — flips between long and short.

    简单移动平均交叉策略。
    快线上穿慢线时做多。
    快线下穿慢线时做空。
    始终在市场 — 在多空之间切换。
    """

    def __init__(self, config: dict):
        super().__init__(config)
        self.name = "SMA Crossover"
        self.fast_period = 20
        self.slow_period = 60
        self.position_size = 1

    def on_bar(self, i: int, bar: Bar, account: Account,
               lookback: List[Bar]) -> List[Order]:
        min_bars = self.slow_period + 2
        if i < min_bars:
            return []

        closes = [b.close for b in lookback]
        fast_ma = sma(closes, self.fast_period)
        slow_ma = sma(closes, self.slow_period)

        # Previous bar's MAs for crossover detection
        # 上一根 K 线的 MA 用于检测交叉
        prev_closes = closes[:-1]
        prev_fast = sma(prev_closes, self.fast_period)
        prev_slow = sma(prev_closes, self.slow_period)

        sym = self.symbol
        pos = self.get_position(account)

        # Bullish crossover: fast crosses above slow
        # 看涨交叉：快线上穿慢线
        if prev_fast <= prev_slow and fast_ma > slow_ma:
            if pos is not None and pos.direction == Direction.SHORT:
                # Flip: close short, open long
                # 翻转：平空仓，开多仓
                return [
                    Order(sym, Direction.LONG, pos.quantity),
                    Order(sym, Direction.LONG, self.position_size),
                ]
            elif pos is None:
                return [Order(sym, Direction.LONG, self.position_size)]

        # Bearish crossover: fast crosses below slow
        # 看跌交叉：快线下穿慢线
        elif prev_fast >= prev_slow and fast_ma < slow_ma:
            if pos is not None and pos.direction == Direction.LONG:
                # Flip: close long, open short
                # 翻转：平多仓，开空仓
                return [
                    Order(sym, Direction.SHORT, pos.quantity),
                    Order(sym, Direction.SHORT, self.position_size),
                ]
            elif pos is None:
                return [Order(sym, Direction.SHORT, self.position_size)]

        return []
