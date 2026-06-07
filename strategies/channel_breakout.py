"""
Channel Breakout Strategy — Long Only with Risk Management.

通道突破策略 — 仅做多，含风险管理。
Enter LONG when price breaks above the highest high of the last N bars.
Classic trend-following approach adapted for minute data.
"""

from typing import List

from backtest.account import Bar, Order, Direction, OrderType, Account
from backtest.strategy_base import Strategy, sma


class ChannelBreakoutStrategy(Strategy):
    """
    Donchian channel breakout — LONG only.
    Buy when close > highest high of last `channel_period` bars.
    Exit on stop-loss, take-profit, or timeout.

    Donchian 通道突破 — 仅做多。
    收盘价突破 N 日最高价时做多。
    """

    def __init__(self, config: dict):
        super().__init__(config)
        self.name = "Channel Breakout"
        self.channel_period = 20
        self.position_size = 1
        self.stop_loss_pct = 0.02
        self.take_profit_pct = 0.05
        self.max_hold_bars = 480
        self.use_channel_stop = False  # Use channel low as trailing stop
        self.volume_confirm = False    # Require above-average volume on breakout
        self.atr_filter = False        # Only trade when ATR is normal
        self.atr_period = 14
        self.atr_max_mult = 2.0        # Max ATR multiple of its average

    def init(self, lookback):
        self._entry_bar = -9999
        self._entry_price = 0.0

    def on_bar(self, i: int, bar: Bar, account: Account,
               lookback: List[Bar]) -> List[Order]:
        if i < self.channel_period + 2:
            return []

        sym = self.symbol
        pos = self.get_position(account)
        bars_held = i - self._entry_bar if pos is not None else 0

        # === EXITS ===
        if pos is not None:
            entry_px = self._entry_price

            if pos.direction == Direction.LONG:
                pnl_pct = (bar.close - entry_px) / entry_px
                # Channel trailing stop: exit if close drops below channel low
                if self.use_channel_stop and bars_held > 5:
                    lows = [b.low for b in lookback[-self.channel_period:-1]]
                    channel_low = min(lows)
                    if bar.close < channel_low:
                        return [Order(sym, Direction.SHORT, pos.quantity)]
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

        # === ENTRY: Channel breakout (long above high, short below low) ===
        if pos is None:
            highs = [b.high for b in lookback[-self.channel_period:-1]]
            lows = [b.low for b in lookback[-self.channel_period:-1]]
            channel_high = max(highs)
            channel_low = min(lows)

            long_breakout = bar.close > channel_high
            short_breakout = bar.close < channel_low

            if self.volume_confirm:
                volumes = [b.volume for b in lookback]
                avg_vol = sma(volumes, self.channel_period)
                long_breakout = long_breakout and volumes[-1] > avg_vol
                short_breakout = short_breakout and volumes[-1] > avg_vol

            if long_breakout:
                self._entry_bar = i
                self._entry_price = bar.close
                return [Order(sym, Direction.LONG, self.position_size)]
            elif short_breakout:
                self._entry_bar = i
                self._entry_price = bar.close
                return [Order(sym, Direction.SHORT, self.position_size)]

        return []
