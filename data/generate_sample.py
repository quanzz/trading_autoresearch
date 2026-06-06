#!/usr/bin/env python
"""Generate synthetic minute-level OHLCV data for testing the backtest framework."""
import csv
import random
import os

random.seed(42)

def generate_bars(n_bars=5000, start_price=450.0, volatility=0.001):
    """Generate synthetic minute bars with trends, mean reversion, and noise."""
    bars = []
    price = start_price
    trend = 0.0
    trend_duration = 0

    for i in range(n_bars):
        # Occasionally change trend direction
        trend_duration -= 1
        if trend_duration <= 0:
            trend = random.uniform(-0.0003, 0.0003)
            trend_duration = random.randint(100, 500)

        # Generate bar
        noise = random.gauss(0, volatility)
        price_change = trend + noise

        open_price = price
        close_price = price * (1 + price_change)
        high_price = max(open_price, close_price) * (1 + abs(random.gauss(0, volatility * 0.5)))
        low_price = min(open_price, close_price) * (1 - abs(random.gauss(0, volatility * 0.5)))
        volume = max(10, int(random.gauss(1000, 300)))
        amt = volume * close_price
        oi = max(10000, int(random.gauss(50000, 5000)))

        # Format date as minute bars for a trading day
        day = i // 240 + 1
        minute = i % 240
        hour = 9 + minute // 60
        if hour >= 11:
            hour += 1  # lunch break 11:30-13:00
            if hour >= 13:
                actual_minute = minute - 90  # adjust for lunch break
                if actual_minute < 0:
                    actual_minute += 60
                    hour -= 1
            else:
                actual_minute = minute % 60
        else:
            actual_minute = minute % 60

        # Cap trading hours: 09:00-11:30, 13:00-15:00
        total_trading_minutes = 240  # 4 hours
        effective_minute = i % total_trading_minutes
        market_hour = 9 + effective_minute // 60
        market_min = effective_minute % 60
        if market_hour >= 11:
            market_hour = 13 + (market_hour - 11)
            if market_hour > 15 or (market_hour == 15 and market_min > 0):
                continue

        hour_str = f"{market_hour:02d}"
        min_str = f"{market_min:02d}"
        date_str = f"2026-06-{(day % 28) + 1:02d} {hour_str}:{min_str}:00"

        bars.append({
            "date": date_str,
            "open": round(open_price, 2),
            "high": round(high_price, 2),
            "low": round(low_price, 2),
            "close": round(close_price, 2),
            "volume": volume,
            "amt": round(amt, 2),
            "oi": oi,
        })

        price = close_price

    return bars


def main():
    output_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(output_dir, "au2607.csv")

    bars = generate_bars(n_bars=5000, start_price=450.0, volatility=0.0015)

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "date", "open", "high", "low", "close", "volume", "amt", "oi"
        ])
        writer.writeheader()
        writer.writerows(bars)

    print(f"Generated {len(bars)} bars at {output_path}")


if __name__ == "__main__":
    main()
