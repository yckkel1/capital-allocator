#!/usr/bin/env python3
"""
Export price_history data for E2E testing
Exports all price history data to a JSON file for test fixtures
"""
import os
import sys
import json
from datetime import date
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg2
from psycopg2.extras import RealDictCursor

# Load environment variables from .env file in repo root if DATABASE_URL not set
if not os.getenv("DATABASE_URL"):
    # .env is in repository root (parent of backend/)
    env_file = Path(__file__).parent.parent.parent / '.env'
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value

DATABASE_URL = os.getenv("DATABASE_URL")


def export_price_history():
    """Export all price_history data to JSON file"""
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # Get all price history data
        cursor.execute("""
            SELECT
                date,
                symbol,
                open_price,
                high_price,
                low_price,
                close_price,
                volume
            FROM price_history
            ORDER BY date, symbol
        """)

        rows = cursor.fetchall()

        if not rows:
            print("No price history data found!")
            return

        # Convert to JSON-serializable format
        data = []
        for row in rows:
            data.append({
                'date': row['date'].isoformat(),
                'symbol': row['symbol'],
                'open_price': float(row['open_price']),
                'high_price': float(row['high_price']),
                'low_price': float(row['low_price']),
                'close_price': float(row['close_price']),
                'volume': float(row['volume'])
            })

        # Get date range info
        min_date = min(d['date'] for d in data)
        max_date = max(d['date'] for d in data)
        symbols = sorted(set(d['symbol'] for d in data))

        # Create output structure
        output = {
            'metadata': {
                'exported_at': date.today().isoformat(),
                'min_date': min_date,
                'max_date': max_date,
                'symbols': symbols,
                'total_records': len(data)
            },
            'data': data
        }

        # Save to test fixtures directory
        fixtures_dir = Path(__file__).parent.parent / 'tests' / 'fixtures'
        fixtures_dir.mkdir(parents=True, exist_ok=True)

        output_file = fixtures_dir / 'price_history_test_data.json'

        with open(output_file, 'w') as f:
            json.dump(output, f, indent=2)

        print(f"Exported {len(data)} price history records")
        print(f"Date range: {min_date} to {max_date}")
        print(f"Symbols: {', '.join(symbols)}")
        print(f"Saved to: {output_file}")

    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    export_price_history()
