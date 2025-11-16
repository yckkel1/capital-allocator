#!/usr/bin/env python3
"""
Generate realistic test price history data for E2E testing.
Creates 1 year of synthetic but realistic price data for SPY, QQQ, DIA.
"""
import json
from datetime import date, timedelta
from pathlib import Path
import random
import math


def generate_realistic_prices(start_date: date, end_date: date, symbols: list) -> list:
    """Generate realistic price data with proper market behavior"""
    data = []

    # Initial prices for each symbol
    base_prices = {
        'SPY': 550.0,  # S&P 500 ETF
        'QQQ': 480.0,  # NASDAQ 100 ETF
        'DIA': 420.0   # Dow Jones ETF
    }

    # Correlation factors (assets should move somewhat together)
    market_volatility = 0.01  # 1% base daily volatility

    current_date = start_date
    prices = base_prices.copy()

    # Track trading days (skip weekends)
    while current_date <= end_date:
        # Skip weekends
        if current_date.weekday() >= 5:
            current_date += timedelta(days=1)
            continue

        # Market-wide factor (affects all assets)
        market_move = random.gauss(0.0003, market_volatility)  # Slight upward bias

        for symbol in symbols:
            # Asset-specific volatility
            if symbol == 'QQQ':
                asset_vol = market_volatility * 1.3  # QQQ more volatile
            elif symbol == 'SPY':
                asset_vol = market_volatility * 1.0
            else:  # DIA
                asset_vol = market_volatility * 0.9  # DIA less volatile

            # Asset-specific move (correlated with market)
            asset_move = market_move * 0.7 + random.gauss(0, asset_vol) * 0.3

            # Calculate daily prices
            prev_close = prices[symbol]

            # Open price (gap from previous close)
            gap = random.gauss(0, 0.002)  # Small overnight gap
            open_price = prev_close * (1 + gap)

            # High and low (intraday range)
            intraday_range = abs(random.gauss(0, asset_vol * 1.5))

            # Close price with daily return
            close_price = open_price * (1 + asset_move)

            # High is max of open/close plus some
            high_price = max(open_price, close_price) * (1 + intraday_range * 0.3)

            # Low is min of open/close minus some
            low_price = min(open_price, close_price) * (1 - intraday_range * 0.3)

            # Volume (higher on volatile days)
            base_volume = {
                'SPY': 80000000,
                'QQQ': 50000000,
                'DIA': 3000000
            }
            volume = base_volume[symbol] * (1 + abs(asset_move) * 10 + random.gauss(0, 0.2))

            data.append({
                'date': current_date.isoformat(),
                'symbol': symbol,
                'open_price': round(open_price, 2),
                'high_price': round(high_price, 2),
                'low_price': round(low_price, 2),
                'close_price': round(close_price, 2),
                'volume': round(volume)
            })

            # Update price for next day
            prices[symbol] = close_price

        current_date += timedelta(days=1)

    return data


def main():
    """Generate and save test price data"""
    # Generate 1 year of data (2024-11-11 to 2025-11-10)
    start_date = date(2024, 11, 11)
    end_date = date(2025, 11, 10)
    symbols = ['SPY', 'QQQ', 'DIA']

    print(f"Generating price data from {start_date} to {end_date}...")

    data = generate_realistic_prices(start_date, end_date, symbols)

    # Get date range info
    min_date = min(d['date'] for d in data)
    max_date = max(d['date'] for d in data)

    # Create output structure
    output = {
        'metadata': {
            'generated_at': date.today().isoformat(),
            'min_date': min_date,
            'max_date': max_date,
            'symbols': symbols,
            'total_records': len(data),
            'note': 'Synthetic test data for E2E testing'
        },
        'data': data
    }

    # Save to fixtures directory
    fixtures_dir = Path(__file__).parent
    output_file = fixtures_dir / 'price_history_test_data.json'

    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"Generated {len(data)} price history records")
    print(f"Date range: {min_date} to {max_date}")
    print(f"Symbols: {', '.join(symbols)}")
    print(f"Saved to: {output_file}")


if __name__ == "__main__":
    main()
