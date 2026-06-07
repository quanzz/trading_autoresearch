"""
Momentum + Volume Filter Strategy.

动量 + 成交量过滤策略。
"""

from typing import List

from backtest.account import Bar, Order, Direction, OrderType, Account
from backtest.strategy_base import Strategy, sma


class MomentumStrategy(Strategy):
    """
    Price momentum strategy with volume confirmation.
    BUY when recent returns are positive AND volume is above average.
    SELL when recent returns are negative AND volume is above average.
    Includes a simple stop-loss: exit if position moves against us by > 2%.

    带成交量确认的价格动量策略。
    近期收益率为正且成交量高于均线时做多。
    近期收益率为负且成交量高于均线时做空。
    包含简单止损：如果仓位逆向波动超过 2% 则平仓。
    """

    def __init__(self, config: dict):
        super().__init__(config)
        self.name = "Momentum + Volume"
        self.momentum_period = 10
        self.volume_period = 20
        self.volume_threshold = 1.2  # volume must be > 1.2x average / 成交量须 > 均值的 1.2 倍
        self.position_size = 1
        self.stop_loss_pct = 0.02    # 2% stop loss / 2% 止损

    def on_bar(self, i: int, bar: Bar, account: Account,
               lookback: List[Bar]) -> List[Order]:
        min_bars = max(self.momentum_period, self.volume_period) + 2
        if i < min_bars:
            return []

        closes = [b.close for b in lookback]
        volumes = [b.volume for b in lookback]

        sym = self.symbol
        pos = self.get_position(account)

        # Stop-loss check
        # 止损检查
        if pos is not None:
            entry_price = pos.avg_price
            if pos.direction == Direction.LONG:
                loss_pct = (entry_price - bar.close) / entry_price
                if loss_pct >= self.stop_loss_pct:
                    return [Order(sym, Direction.SHORT, pos.quantity)]
            else:  # SHORT / 空头
                loss_pct = (bar.close - entry_price) / entry_price
                if loss_pct >= self.stop_loss_pct:
                    return [Order(sym, Direction.LONG, pos.quantity)]

        # Momentum signal
        # 动量信号
        momentum = (closes[-1] - closes[-self.momentum_period - 1]) / closes[-self.momentum_period - 1]

        # Volume filter
        # 成交量过滤
        avg_volume = sma(volumes, self.volume_period) if len(volumes) >= self.volume_period else volumes[-1]
        current_volume = volumes[-1]
        high_volume = current_volume > avg_volume * self.volume_threshold

        if momentum > 0.002 and high_volume:
            if pos is not None and pos.direction == Direction.SHORT:
                return [
                    Order(sym, Direction.LONG, pos.quantity),
                    Order(sym, Direction.LONG, self.position_size),
                ]
            elif pos is None:
                return [Order(sym, Direction.LONG, self.position_size)]

        elif momentum < -0.002 and high_volume:
            if pos is not None and pos.direction == Direction.LONG:
                return [
                    Order(sym, Direction.SHORT, pos.quantity),
                    Order(sym, Direction.SHORT, self.position_size),
                ]
            elif pos is None:
                return [Order(sym, Direction.SHORT, self.position_size)]

        return []
