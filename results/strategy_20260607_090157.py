"""
Trading Autoresearch — Active Strategy Selection.

This is a thin wrapper that re-exports from the strategies/ directory.
The agent creates and edits strategy files under strategies/, and switches
the active strategy by modifying strategies/__init__.py.

Importing from this file is equivalent to importing from strategies/ directly.

Trading Autoresearch — 活跃策略选择。

这是对 strategies/ 目录的薄封装重新导出。
Agent 在 strategies/ 下创建和编辑策略文件，通过修改 strategies/__init__.py 切换活跃策略。

从此文件导入等同于直接从 strategies/ 导入。
"""

# Re-export everything from strategies for backward compatibility
# 从 strategies 重新导出所有内容以保持向后兼容
from strategies import (
    SmaCrossStrategy,
    BollingerBreakoutStrategy,
    MomentumStrategy,
    RsiReversionStrategy,
    Strategy,
    sma,
    ema,
    stddev,
    rsi,
    create_strategy,
)

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
