"""
Export 10 years of historical price data for initial deployment seeding.

This script fetches 10 years of historical data for SPY, QQQ, and DIA
and generates a SQL file that can be used in the seed migration.
"""
import os
import sys
from pathlib import Path
import requests
import time
from datetime import datetime, timedelta
import csv
from io import StringIO

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import get_settings

def fetch_full_history(symbol: str, api_key: str, output_size: str = "full") -> list:
    """
    Fetch full historical data for a symbol from Alpha Vantage.

    Args:
        symbol: Stock symbol (e.g., 'SPY')
        api_key: Alpha Vantage API key
        output_size: 'compact' (100 days) or 'full' (20+ years)

    Returns:
        List of dict with keys: date, symbol, open, high, low, close, volume
    """
    url = "https://www.alphavantage.co/query"
    params = {
        "function": "TIME_SERIES_DAILY_ADJUSTED",
        "symbol": symbol,
        "outputsize": output_size,
        "apikey": api_key,
        "datatype": "csv"
    }

    print(f"Fetching {output_size} history for {symbol}...")
    response = requests.get(url, params=params)

    if response.status_code != 200:
        raise Exception(f"API request failed with status {response.status_code}: {response.text}")

    # Parse CSV response
    csv_data = StringIO(response.text)
    reader = csv.DictReader(csv_data)

    records = []
    for row in reader:
        records.append({
            'date': row['timestamp'],
            'symbol': symbol,
            'open': float(row['open']),
            'high': float(row['high']),
            'low': float(row['low']),
            'close': float(row['adjusted_close']),  # Use adjusted close for splits/dividends
            'volume': float(row['volume'])
        })

    print(f"  Fetched {len(records)} records for {symbol}")
    return records


def filter_last_n_years(records: list, years: int = 10) -> list:
    """Filter records to only include last N years of data."""
    cutoff_date = datetime.now() - timedelta(days=years * 365)
    cutoff_str = cutoff_date.strftime('%Y-%m-%d')

    filtered = [r for r in records if r['date'] >= cutoff_str]
    print(f"  Filtered to {len(filtered)} records from {cutoff_str} onwards")
    return filtered


def generate_sql_inserts(records: list, output_file: str):
    """Generate SQL INSERT statements for price history data."""

    # Sort by date ascending (oldest first)
    records_sorted = sorted(records, key=lambda x: (x['date'], x['symbol']))

    with open(output_file, 'w') as f:
        f.write("-- Historical price data for initial deployment\n")
        f.write("-- Generated on: {}\n".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        f.write(f"-- Total records: {len(records_sorted)}\n\n")

        # Use batch inserts for efficiency (500 records at a time)
        batch_size = 500
        for i in range(0, len(records_sorted), batch_size):
            batch = records_sorted[i:i+batch_size]

            f.write("INSERT INTO price_history (date, symbol, open_price, high_price, low_price, close_price, volume) VALUES\n")

            for idx, record in enumerate(batch):
                values = (
                    f"  ('{record['date']}', '{record['symbol']}', "
                    f"{record['open']}, {record['high']}, {record['low']}, "
                    f"{record['close']}, {record['volume']})"
                )

                if idx < len(batch) - 1:
                    f.write(values + ",\n")
                else:
                    f.write(values + "\n")

            f.write("ON CONFLICT DO NOTHING;\n\n")

    print(f"\nGenerated SQL file: {output_file}")
    print(f"Total records: {len(records_sorted)}")


def main():
    """Main function to export historical data."""
    settings = get_settings()
    api_key = settings.alphavantage_api_key

    # Symbols to fetch
    symbols = ["SPY", "QQQ", "DIA"]
    all_records = []

    for idx, symbol in enumerate(symbols):
        try:
            records = fetch_full_history(symbol, api_key, output_size="full")
            filtered_records = filter_last_n_years(records, years=10)
            all_records.extend(filtered_records)

            # Rate limiting: Alpha Vantage free tier allows 5 calls/min
            if idx < len(symbols) - 1:
                print("  Waiting 15 seconds for rate limiting...")
                time.sleep(15)

        except Exception as e:
            print(f"Error fetching {symbol}: {e}")
            sys.exit(1)

    # Generate SQL file
    output_dir = Path(__file__).parent.parent / "alembic" / "seed_data"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "price_history_10y.sql"

    generate_sql_inserts(all_records, str(output_file))

    print(f"\n✓ Successfully exported {len(all_records)} records to {output_file}")
    print(f"\nThis file will be used by the seed data migration on first deployment.")


if __name__ == "__main__":
    main()
