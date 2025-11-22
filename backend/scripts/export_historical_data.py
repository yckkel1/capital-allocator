"""
Export 10 years of historical price data for initial deployment seeding.

This script exports existing price history data from your local PostgreSQL database
and generates a SQL file that can be used in the seed migration on Railway.
"""
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import get_settings


def export_from_database(years: int = 10) -> list:
    """
    Export price history from local PostgreSQL database.

    Args:
        years: Number of years of historical data to export (default: 10)

    Returns:
        List of dict with keys: date, symbol, open, high, low, close, volume
    """
    settings = get_settings()
    cutoff_date = datetime.now() - timedelta(days=years * 365)
    cutoff_str = cutoff_date.strftime('%Y-%m-%d')

    print(f"Connecting to database: {settings.database_url.split('@')[1] if '@' in settings.database_url else 'local'}")

    try:
        # Connect to database
        conn = psycopg2.connect(settings.database_url)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Query price history from the last N years
        query = """
            SELECT
                date,
                symbol,
                open_price as open,
                high_price as high,
                low_price as low,
                close_price as close,
                volume
            FROM price_history
            WHERE date >= %s
            ORDER BY date ASC, symbol ASC
        """

        print(f"Querying price history from {cutoff_str} onwards...")
        cursor.execute(query, (cutoff_str,))

        records = []
        for row in cursor.fetchall():
            records.append({
                'date': row['date'].strftime('%Y-%m-%d'),
                'symbol': row['symbol'],
                'open': float(row['open']),
                'high': float(row['high']),
                'low': float(row['low']),
                'close': float(row['close']),
                'volume': float(row['volume'])
            })

        cursor.close()
        conn.close()

        print(f"  ✓ Exported {len(records)} records")

        # Show breakdown by symbol
        symbols = {}
        for record in records:
            symbols[record['symbol']] = symbols.get(record['symbol'], 0) + 1

        for symbol, count in sorted(symbols.items()):
            print(f"    {symbol}: {count} records")

        return records

    except psycopg2.Error as e:
        print(f"Database error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


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
    """Main function to export historical data from local database."""
    print("=" * 60)
    print("Exporting Price History for Railway Deployment")
    print("=" * 60)
    print()

    # Export from local database
    try:
        all_records = export_from_database(years=10)
    except Exception as e:
        print(f"\nError: Failed to export data from database")
        print(f"Make sure:")
        print(f"  1. DATABASE_URL is set in .env")
        print(f"  2. PostgreSQL is running")
        print(f"  3. price_history table has data")
        sys.exit(1)

    if not all_records:
        print("\n⚠ Warning: No records found in database!")
        print("Make sure your price_history table has data for the last 10 years.")
        sys.exit(1)

    # Generate SQL file
    output_dir = Path(__file__).parent.parent / "alembic" / "seed_data"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "price_history_10y.sql"

    generate_sql_inserts(all_records, str(output_file))

    print(f"\n✓ Successfully exported {len(all_records)} records")
    print(f"✓ SQL file: {output_file}")
    print(f"\nNext steps:")
    print(f"  1. Review the generated file")
    print(f"  2. Commit to git:")
    print(f"       git add backend/alembic/seed_data/price_history_10y.sql")
    print(f"       git commit -m 'Add 10 years of historical price data'")
    print(f"  3. Deploy to Railway - migrations will load this data automatically!")


if __name__ == "__main__":
    main()
