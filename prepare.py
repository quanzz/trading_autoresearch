"""
Data loading and preparation for Trading Autoresearch.
Reads CSV files with minute-level OHLCV data.
FIXED — do not modify. The agent edits strategy.py instead.
"""

import csv
import os
from typing import Dict, List, Optional

from backtest.account import Bar


def _parse_float(val: str) -> Optional[float]:
    """Parse a string to float, returning None for empty/missing values."""
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
            if bar.open == 0.0 and bar.close == 0.0:
                continue

            bars.append(bar)

    if not bars:
        raise ValueError(f"No valid bars found in {filepath}")

    # Ensure sorted by date
    bars.sort(key=lambda b: b.date)

    # Forward-fill zero prices (use previous bar's close)
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
    """
    data = {}
    for symbol in symbols:
        filepath = os.path.join(data_dir, f"{symbol}.csv")
        print(f"Loading {filepath}...")
        bars = load_csv(filepath)
        print(f"  Loaded {len(bars)} bars for {symbol}")
        data[symbol] = bars
    return data
