"""
Strategy registry for Trading Autoresearch.
Imports all available strategies and provides the factory function.

Trading Autoresearch 策略注册中心。
导入所有可用策略并提供工厂函数。

THE AGENT CAN:
- Modify create_strategy() to switch strategies or tune parameters.
- Create new strategy files in this directory.
- Import new strategies and add them to the registry.

AGENT 可以：
- 修改 create_strategy() 来切换策略或调整参数。
- 在此目录下创建新的策略文件。
- 导入新策略并添加到注册中心。
"""

from strategies.sma_cross import SmaCrossStrategy
from strategies.bollinger_breakout import BollingerBreakoutStrategy
from strategies.momentum_volume import MomentumStrategy
from strategies.rsi_reversion import RsiReversionStrategy
from strategies.enhanced_momentum import EnhancedMomentumStrategy

# Re-export indicator helpers for convenience
# 重新导出指标辅助函数以便使用
from backtest.strategy_base import Strategy, sma, ema, stddev, rsi

__all__ = [
    "SmaCrossStrategy",
    "BollingerBreakoutStrategy",
    "MomentumStrategy",
    "RsiReversionStrategy",
    "Strategy",
    "sma",
    "ema",
    "stddev",
    "rsi",
    "create_strategy",
]


def create_strategy(config: dict) -> Strategy:
    """
    Factory function that creates the active strategy.
    The agent modifies this to switch strategies or pass custom parameters.

    Available strategies:
        SmaCrossStrategy       — SMA crossover, always in market
        BollingerBreakoutStrategy — Bollinger Bands mean reversion
        MomentumStrategy       — Momentum + volume filter
        RsiReversionStrategy   — RSI mean reversion with tight risk control

    创建活跃策略的工厂函数。
    Agent 修改此函数来切换策略或传入自定义参数。

    可用策略：
        SmaCrossStrategy       — SMA 交叉，始终持仓
        BollingerBreakoutStrategy — 布林带均值回归
        MomentumStrategy       — 动量 + 成交量过滤
        RsiReversionStrategy   — RSI 均值回归 + 严格风险控制
    """
    strategy = EnhancedMomentumStrategy(config)
    strategy.momentum_period = 8
    strategy.volume_period = 15
    strategy.volume_threshold = 0.0
    strategy.position_size = 1
    strategy.stop_loss_pct = 0.01
    strategy.take_profit_pct = 0.035
    strategy.max_hold_bars = 240
    return strategy
