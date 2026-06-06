"""
Trading strategy definitions for Trading Autoresearch.
THIS IS THE FILE THE AGENT MODIFIES — it is the only place where
strategy logic should be added, removed, or changed.

The agent can:
- Modify parameters of existing strategies
- Write entirely new strategy classes
- Combine strategies with filters or signals

The active strategy is selected by create_strategy() at the bottom of this file.

Strategy Interface:
    class Strategy:
        def init(self, lookback: List[Bar]):
            '''Called once before backtest starts. Use for indicator setup.'''

        def on_bar(self, i, bar, account, lookback) -> List[Order]:
            '''Called on each bar. Return a list of Order objects.'''

Note: self.symbols is set by the engine before init() is called.
Use self.symbols[0] to get the primary trading symbol.
"""

from typing import List

from backtest.account import Bar, Order, Direction, OrderType, Account


# ===========================================================================
# Strategy base class
# ===========================================================================

class Strategy:
    """Base strategy class. All strategies inherit from this."""

    def __init__(self, config: dict):
        self.config = config
        self.name = "BaseStrategy"
        self.symbols = []  # Set by engine before init()

    @property
    def symbol(self) -> str:
        """Primary trading symbol (first in data config)."""
        return self.symbols[0] if self.symbols else ""

    def init(self, lookback: List[Bar]):
        """Called once before the backtest loop begins."""
        pass

    def on_bar(self, i: int, bar: Bar, account: Account,
               lookback: List[Bar]) -> List[Order]:
        """
        Called on each bar after warmup.

        Args:
            i: Current bar index (0-based).
            bar: Current bar data (OHLCV).
            account: Account state (cash, positions, equity curve).
            lookback: All bars from index 0 to i (inclusive).

        Returns:
            List of Order objects to execute. Return empty list for no action.
        """
        return []

    def has_position(self, account: Account) -> bool:
        """Check if we currently hold a position in the primary symbol."""
        return self.symbol in account.positions

    def get_position(self, account: Account):
        """Get current position in the primary symbol, or None."""
        return account.positions.get(self.symbol)


# ===========================================================================
# Technical indicator helpers
# ===========================================================================

def sma(values: List[float], period: int) -> float:
    """Simple Moving Average of the last `period` values. Returns single value."""
    if len(values) < period:
        return values[-1] if values else 0.0
    return sum(values[-period:]) / period


def ema(values: List[float], period: int) -> float:
    """Exponential Moving Average. Returns the latest EMA value."""
    if len(values) < 2:
        return values[-1] if values else 0.0
    multiplier = 2.0 / (period + 1)
    result = values[0]
    for v in values[1:]:
        result = (v - result) * multiplier + result
    return result


def stddev(values: List[float], period: int) -> float:
    """Sample standard deviation of the last `period` values."""
    if len(values) < period:
        return 0.0
    window = values[-period:]
    mean = sum(window) / period
    variance = sum((x - mean) ** 2 for x in window) / (period - 1)
    return variance ** 0.5


def rsi(closes: List[float], period: int = 14) -> float:
    """Relative Strength Index (0-100)."""
    if len(closes) < period + 1:
        return 50.0
    gains = 0.0
    losses = 0.0
    for i in range(-period, 0):
        delta = closes[i] - closes[i - 1]
        if delta > 0:
            gains += delta
        else:
            losses -= delta
    avg_gain = gains / period
    avg_loss = losses / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


# ===========================================================================
# Strategy 1: SMA Crossover
# ===========================================================================

class SmaCrossStrategy(Strategy):
    """
    Simple Moving Average crossover strategy.
    BUY when fast MA crosses above slow MA.
    SELL when fast MA crosses below slow MA.
    Always in the market — flips between long and short.
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
        prev_closes = closes[:-1]
        prev_fast = sma(prev_closes, self.fast_period)
        prev_slow = sma(prev_closes, self.slow_period)

        sym = self.symbol
        pos = self.get_position(account)

        # Bullish crossover: fast crosses above slow
        if prev_fast <= prev_slow and fast_ma > slow_ma:
            if pos is not None and pos.direction == Direction.SHORT:
                # Flip: close short, open long
                return [
                    Order(sym, Direction.LONG, pos.quantity),
                    Order(sym, Direction.LONG, self.position_size),
                ]
            elif pos is None:
                return [Order(sym, Direction.LONG, self.position_size)]

        # Bearish crossover: fast crosses below slow
        elif prev_fast >= prev_slow and fast_ma < slow_ma:
            if pos is not None and pos.direction == Direction.LONG:
                # Flip: close long, open short
                return [
                    Order(sym, Direction.SHORT, pos.quantity),
                    Order(sym, Direction.SHORT, self.position_size),
                ]
            elif pos is None:
                return [Order(sym, Direction.SHORT, self.position_size)]

        return []


# ===========================================================================
# Strategy 2: Bollinger Bands Mean Reversion
# ===========================================================================

class BollingerBreakoutStrategy(Strategy):
    """
    Bollinger Bands mean reversion strategy.
    BUY when price closes below lower band (oversold).
    SELL when price closes above upper band (overbought).
    Exit when price crosses back through the middle band.
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
        if bar.close <= lower:
            # Price at lower band — go long
            if pos is not None and pos.direction == Direction.SHORT:
                return [
                    Order(sym, Direction.LONG, pos.quantity),
                    Order(sym, Direction.LONG, self.position_size),
                ]
            elif pos is None:
                return [Order(sym, Direction.LONG, self.position_size)]

        elif bar.close >= upper:
            # Price at upper band — go short
            if pos is not None and pos.direction == Direction.LONG:
                return [
                    Order(sym, Direction.SHORT, pos.quantity),
                    Order(sym, Direction.SHORT, self.position_size),
                ]
            elif pos is None:
                return [Order(sym, Direction.SHORT, self.position_size)]

        # Exit when price crosses middle band
        prev_close = closes[-2] if len(closes) >= 2 else bar.close
        if pos is not None:
            if pos.direction == Direction.LONG and prev_close < ma <= bar.close:
                return [Order(sym, Direction.SHORT, pos.quantity)]
            elif pos.direction == Direction.SHORT and prev_close > ma >= bar.close:
                return [Order(sym, Direction.LONG, pos.quantity)]

        return []


# ===========================================================================
# Strategy 3: Momentum with Volume Filter
# ===========================================================================

class MomentumStrategy(Strategy):
    """
    Price momentum strategy with volume confirmation.
    BUY when recent returns are positive AND volume is above average.
    SELL when recent returns are negative AND volume is above average.
    Includes a simple stop-loss: exit if position moves against us by > 2%.
    """

    def __init__(self, config: dict):
        super().__init__(config)
        self.name = "Momentum + Volume"
        self.momentum_period = 10
        self.volume_period = 20
        self.volume_threshold = 1.2  # volume must be > 1.2x average
        self.position_size = 1
        self.stop_loss_pct = 0.02    # 2% stop loss

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
        if pos is not None:
            entry_price = pos.avg_price
            if pos.direction == Direction.LONG:
                loss_pct = (entry_price - bar.close) / entry_price
                if loss_pct >= self.stop_loss_pct:
                    return [Order(sym, Direction.SHORT, pos.quantity)]
            else:  # SHORT
                loss_pct = (bar.close - entry_price) / entry_price
                if loss_pct >= self.stop_loss_pct:
                    return [Order(sym, Direction.LONG, pos.quantity)]

        # Momentum signal
        momentum = (closes[-1] - closes[-self.momentum_period - 1]) / closes[-self.momentum_period - 1]

        # Volume filter
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


# ===========================================================================
# Strategy 4: RSI Mean Reversion with Tight Risk Control
# ===========================================================================

class RsiReversionStrategy(Strategy):
    """
    RSI-based mean reversion with asymmetric risk/reward.
    - BUY when RSI < oversold threshold (panic selling)
    - SELL when RSI > overbought threshold (greedy buying)
    - Exit at RSI midpoint, or via hard stop/take-profit
    - Large number of small trades with positive expectancy
    """

    def __init__(self, config: dict):
        super().__init__(config)
        self.name = "RSI Reversion"
        self.rsi_period = 7
        self.oversold = 25
        self.overbought = 75
        self.position_size = 1
        self.stop_loss_pct = 0.01       # 1% stop — cut losses fast
        self.take_profit_pct = 0.025    # 2.5% target — asymmetric R:R
        self.max_hold_bars = 480        # Max 8 hours hold time

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
        if pos is not None:
            entry_px = self._entry_price

            # 1. Stop loss / Take profit
            if pos.direction == Direction.LONG:
                pnl_pct = (bar.close - entry_px) / entry_px
                if pnl_pct <= -self.stop_loss_pct:
                    return [Order(sym, Direction.SHORT, pos.quantity)]
                if pnl_pct >= self.take_profit_pct:
                    return [Order(sym, Direction.SHORT, pos.quantity)]
                # Exit at RSI midpoint recovery
                if bars_held > 10 and curr_rsi >= 50:
                    return [Order(sym, Direction.SHORT, pos.quantity)]
            else:  # SHORT
                pnl_pct = (entry_px - bar.close) / entry_px
                if pnl_pct <= -self.stop_loss_pct:
                    return [Order(sym, Direction.LONG, pos.quantity)]
                if pnl_pct >= self.take_profit_pct:
                    return [Order(sym, Direction.LONG, pos.quantity)]
                if bars_held > 10 and curr_rsi <= 50:
                    return [Order(sym, Direction.LONG, pos.quantity)]

            # 2. Time stop
            if bars_held >= self.max_hold_bars:
                if pos.direction == Direction.LONG:
                    return [Order(sym, Direction.SHORT, pos.quantity)]
                else:
                    return [Order(sym, Direction.LONG, pos.quantity)]

        # === ENTRIES (only when flat) ===
        if pos is None:
            # Oversold — buy the panic
            if curr_rsi < self.oversold:
                self._entry_bar = i
                self._entry_price = bar.close
                return [Order(sym, Direction.LONG, self.position_size)]

            # Overbought — sell the euphoria
            elif curr_rsi > self.overbought:
                self._entry_bar = i
                self._entry_price = bar.close
                return [Order(sym, Direction.SHORT, self.position_size)]

        return []


# ===========================================================================
# Active Strategy Selection
# ===========================================================================
# The agent modifies create_strategy() to switch strategies or change params.

def create_strategy(config: dict) -> Strategy:
    """
    Factory function that creates the active strategy.
    The agent modifies this to switch strategies or pass custom parameters.
    """
    strategy = RsiReversionStrategy(config)
    strategy.rsi_period = 7
    strategy.oversold = 25
    strategy.overbought = 75
    strategy.position_size = 1
    strategy.stop_loss_pct = 0.01
    strategy.take_profit_pct = 0.025
    strategy.max_hold_bars = 480
    return strategy
