"""
Strategy base class and technical indicator helpers for Trading Autoresearch.

策略基类和技术指标辅助函数。

FIXED — do not modify. The agent creates/edits strategy files under strategies/.
固定模块 — 请勿修改。agent 在 strategies/ 目录下创建/编辑策略文件。
"""

from typing import List

from .account import Bar, Order, Direction, OrderType, Account


class Strategy:
    """Base strategy class. All strategies inherit from this.

    策略基类。所有策略都继承此类。"""

    def __init__(self, config: dict):
        self.config = config
        self.name = "BaseStrategy"
        self.symbols = []  # Set by engine before init() / 由引擎在 init() 前设置

    @property
    def symbol(self) -> str:
        """Primary trading symbol (first in data config).

        主交易品种（数据配置中的第一个）。"""
        return self.symbols[0] if self.symbols else ""

    def init(self, lookback: List[Bar]):
        """Called once before the backtest loop begins.

        在回测循环开始前调用一次。"""
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

        预热后每根 K 线调用一次。

        Args:
            i: 当前 K 线索引（从 0 开始）。
            bar: 当前 K 线数据（OHLCV）。
            account: 账户状态（现金、持仓、权益曲线）。
            lookback: 从索引 0 到 i（含）的所有 K 线。

        Returns:
            待执行的 Order 对象列表。无操作返回空列表。
        """
        return []

    def has_position(self, account: Account) -> bool:
        """Check if we currently hold a position in the primary symbol.

        检查当前是否持有主品种的仓位。"""
        return self.symbol in account.positions

    def get_position(self, account: Account):
        """Get current position in the primary symbol, or None.

        获取当前主品种的仓位，无持仓返回 None。"""
        return account.positions.get(self.symbol)


# ===========================================================================
# Technical indicator helpers
# 技术指标辅助函数
# ===========================================================================

def sma(values: List[float], period: int) -> float:
    """Simple Moving Average of the last `period` values. Returns single value.

    最近 `period` 个值的简单移动平均。返回单个值。"""
    if len(values) < period:
        return values[-1] if values else 0.0
    return sum(values[-period:]) / period


def ema(values: List[float], period: int) -> float:
    """Exponential Moving Average. Returns the latest EMA value.

    指数移动平均。返回最新的 EMA 值。"""
    if len(values) < 2:
        return values[-1] if values else 0.0
    multiplier = 2.0 / (period + 1)
    result = values[0]
    for v in values[1:]:
        result = (v - result) * multiplier + result
    return result


def stddev(values: List[float], period: int) -> float:
    """Sample standard deviation of the last `period` values.

    最近 `period` 个值的样本标准差。"""
    if len(values) < period:
        return 0.0
    window = values[-period:]
    mean = sum(window) / period
    variance = sum((x - mean) ** 2 for x in window) / (period - 1)
    return variance ** 0.5


def rsi(closes: List[float], period: int = 14) -> float:
    """Relative Strength Index (0-100).

    相对强弱指数（0-100）。"""
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
