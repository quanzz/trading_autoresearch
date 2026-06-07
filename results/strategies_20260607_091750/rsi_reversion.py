"""
RSI Mean Reversion Strategy.

RSI 均值回归策略。
"""

from typing import List

from backtest.account import Bar, Order, Direction, OrderType, Account
from backtest.strategy_base import Strategy, rsi


class RsiReversionStrategy(Strategy):
    """
    RSI-based mean reversion with asymmetric risk/reward.
    - BUY when RSI < oversold threshold (panic selling)
    - SELL when RSI > overbought threshold (greedy buying)
    - Exit at RSI midpoint, or via hard stop/take-profit
    - Large number of small trades with positive expectancy

    基于 RSI 的均值回归策略，具有非对称风险/收益比。
    - RSI < 超卖阈值时做多（恐慌抛售）
    - RSI > 超买阈值时做空（贪婪买入）
    - 在 RSI 中位线平仓，或通过硬止损/止盈平仓
    - 大量小额交易，具有正期望值
    """

    def __init__(self, config: dict):
        super().__init__(config)
        self.name = "RSI Reversion"
        self.rsi_period = 7
        self.oversold = 25
        self.overbought = 75
        self.position_size = 1
        self.stop_loss_pct = 0.01       # 1% stop — cut losses fast / 1% 止损 — 快速止损
        self.take_profit_pct = 0.025    # 2.5% target — asymmetric R:R / 2.5% 目标 — 非对称风险收益比
        self.max_hold_bars = 480        # Max 8 hours hold time / 最长持仓 8 小时

    def init(self, lookback):
        self._entry_bar = -9999
        self._entry_price = 0.0

    def on_bar(self, i: int, bar: Bar, account: Account,
               lookback: List[Bar]) -> List[Order]:
        if i < self.rsi_period + 2:
            return []

        closes = [b.close for b in lookback]
        curr_rsi = rsi(closes, self.rsi_period)

        sym = self.symbol
        pos = self.get_position(account)
        bars_held = i - self._entry_bar if pos is not None else 0

        # === EXITS ===
        # === 平仓条件 ===
        if pos is not None:
            entry_px = self._entry_price

            # 1. Stop loss / Take profit
            # 1. 止损 / 止盈
            if pos.direction == Direction.LONG:
                pnl_pct = (bar.close - entry_px) / entry_px
                if pnl_pct <= -self.stop_loss_pct:
                    return [Order(sym, Direction.SHORT, pos.quantity)]
                if pnl_pct >= self.take_profit_pct:
                    return [Order(sym, Direction.SHORT, pos.quantity)]
                # Exit at RSI midpoint recovery
                # RSI 回到中位线时平仓
                if bars_held > 10 and curr_rsi >= 50:
                    return [Order(sym, Direction.SHORT, pos.quantity)]
            else:  # SHORT / 空头
                pnl_pct = (entry_px - bar.close) / entry_px
                if pnl_pct <= -self.stop_loss_pct:
                    return [Order(sym, Direction.LONG, pos.quantity)]
                if pnl_pct >= self.take_profit_pct:
                    return [Order(sym, Direction.LONG, pos.quantity)]
                if bars_held > 10 and curr_rsi <= 50:
                    return [Order(sym, Direction.LONG, pos.quantity)]

            # 2. Time stop
            # 2. 时间止损
            if bars_held >= self.max_hold_bars:
                if pos.direction == Direction.LONG:
                    return [Order(sym, Direction.SHORT, pos.quantity)]
                else:
                    return [Order(sym, Direction.LONG, pos.quantity)]

        # === ENTRIES (only when flat) ===
        # === 开仓条件（仅空仓时） ===
        if pos is None:
            # Oversold — buy the panic
            # 超卖 — 买入恐慌
            if curr_rsi < self.oversold:
                self._entry_bar = i
                self._entry_price = bar.close
                return [Order(sym, Direction.LONG, self.position_size)]

            # Overbought — sell the euphoria
            # 超买 — 卖出狂热
            elif curr_rsi > self.overbought:
                self._entry_bar = i
                self._entry_price = bar.close
                return [Order(sym, Direction.SHORT, self.position_size)]

        return []
