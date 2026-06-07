"""
Data loading and preparation for Trading Autoresearch.
Reads CSV files with minute-level OHLCV data.

Trading Autoresearch 数据加载与预处理。
读取分钟级 OHLCV 数据的 CSV 文件。

FIXED — do not modify. The agent edits files under strategies/ instead.
固定模块 — 请勿修改。agent 在 strategies/ 目录下编辑策略文件。
"""

import csv
import os
from typing import Dict, List, Optional

from backtest.account import Bar


def _parse_float(val: str) -> Optional[float]:
    """Parse a string to float, returning None for empty/missing values.

    将字符串解析为浮点数，空值/缺失值返回 None。"""
    if val is None:
        return None
    val = val.strip()
    if val == "" or val.lower() == "nan" or val.lower() == "null":
        return None
    try:
        return float(val)
    except ValueError:
        return None


def load_csv(filepath: str) -> List[Bar]:
    """
    Load a single CSV file of minute-level OHLCV data.

    Expected columns (comma-separated):
        date, open, high, low, close, volume, amt, oi

    Empty/missing values are handled gracefully.

    Args:
        filepath: Path to the CSV file.

    Returns:
        List of Bar objects sorted by date.

    加载单个分钟级 OHLCV 数据的 CSV 文件。

    预期列（逗号分隔）：
        date, open, high, low, close, volume, amt, oi

    空值/缺失值会被优雅处理。

    Args:
        filepath: CSV 文件路径。

    Returns:
        按日期排序的 Bar 对象列表。
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Data file not found: {filepath}")

    bars = []
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            date = row.get("date", "").strip()
            if not date:
                continue

            bar = Bar(
                date=date,
                open=_parse_float(row.get("open", "")) or 0.0,
                high=_parse_float(row.get("high", "")) or 0.0,
                low=_parse_float(row.get("low", "")) or 0.0,
                close=_parse_float(row.get("close", "")) or 0.0,
                volume=_parse_float(row.get("volume", "")) or 0.0,
                amt=_parse_float(row.get("amt", "")) or 0.0,
                oi=_parse_float(row.get("oi", "")) or 0.0,
            )

            # Skip bars with no price data
            # 跳过没有价格数据的 K 线
            if bar.open == 0.0 and bar.close == 0.0:
                continue

            bars.append(bar)

    if not bars:
        raise ValueError(f"No valid bars found in {filepath}")

    # Ensure sorted by date
    # 确保按日期排序
    bars.sort(key=lambda b: b.date)

    # Forward-fill zero prices (use previous bar's close)
    # 前向填充零价格（使用前一根 K 线的收盘价）
    for i in range(1, len(bars)):
        if bars[i].open == 0.0:
            bars[i].open = bars[i - 1].close
        if bars[i].high == 0.0:
            bars[i].high = bars[i].open
        if bars[i].low == 0.0:
            bars[i].low = bars[i].open
        if bars[i].close == 0.0:
            bars[i].close = bars[i].open

    return bars


def load_all_data(data_dir: str, symbols: List[str]) -> Dict[str, List[Bar]]:
    """
    Load data for multiple symbols from a directory.

    Args:
        data_dir: Directory containing CSV files.
        symbols: List of symbol names (e.g., ["au2607", "rb2601"]).

    Returns:
        Dict mapping symbol → list of Bar objects.

    从目录中加载多个品种的数据。

    Args:
        data_dir: 包含 CSV 文件的目录。
        symbols: 品种名称列表（如 ["au2607", "rb2601"]）。

    Returns:
        品种 → Bar 对象列表的映射字典。
    """
    data = {}
    for symbol in symbols:
        filepath = os.path.join(data_dir, f"{symbol}.csv")
        print(f"Loading {filepath}...")
        bars = load_csv(filepath)
        print(f"  Loaded {len(bars)} bars for {symbol}")
        data[symbol] = bars
    return data
