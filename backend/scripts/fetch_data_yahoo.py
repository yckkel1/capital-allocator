"""
Backfill historical data using Yahoo Finance (free, no API key needed)

This is an alternative to Alpha Vantage for getting historical price data.
Yahoo Finance provides free historical data without rate limits.

Usage:
    python scripts/fetch_data_yahoo.py --days 3650  # 10 years
"""

import yfinance as yf
from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models import PriceHistory

# Default symbols
DEFAULT_SYMBOLS = ["SPY", "QQQ", "DIA"]


def backfill_from_yahoo(symbols: list = None, days: int = 3650):
    """
    Backfill historical data using Yahoo Finance (free, unlimited history)

    Args:
        symbols: List of ticker symbols (defaults to SPY, QQQ, DIA)
        days: Number of days of history to fetch (default: 3650 = ~10 years)
    """
    if symbols is None:
        symbols = DEFAULT_SYMBOLS

    print(f"=" * 60)
    print(f"Backfilling {days} days of data from Yahoo Finance")
    print(f"=" * 60)
    print(f"Symbols: {', '.join(symbols)}")
    print(f"")

    db = SessionLocal()
    start_date = date.today() - timedelta(days=days)
    end_date = date.today()

    try:
        for symbol in symbols:
            print(f"Fetching {symbol}...")

            # Download data from Yahoo Finance
            ticker = yf.Ticker(symbol)
            hist = ticker.history(start=start_date, end=end_date)

            if hist.empty:
                print(f"  WARNING: No data returned for {symbol}")
                continue

            count = 0
            for idx in range(len(hist)):
                trade_date = hist.index[idx].date()
                row = hist.iloc[idx]

                # Check if exists
                existing = db.query(PriceHistory).filter(
                    PriceHistory.symbol == symbol,
                    PriceHistory.date == trade_date
                ).first()

                if existing:
                    continue

                price_record = PriceHistory(
                    date=trade_date,
                    symbol=symbol,
                    open_price=float(row['Open']),
                    high_price=float(row['High']),
                    low_price=float(row['Low']),
                    close_price=float(row['Close']),
                    volume=float(row['Volume'])
                )

                db.add(price_record)
                count += 1

            db.commit()
            print(f"  ✓ Added {count} records for {symbol}")

        # Show summary
        print(f"\n" + "=" * 60)
        print(f"Backfill Complete!")
        print(f"=" * 60)

        # Query total records
        total = db.query(PriceHistory).count()
        print(f"Total records in database: {total}")

        # Show date range
        oldest = db.query(PriceHistory).order_by(PriceHistory.date.asc()).first()
        newest = db.query(PriceHistory).order_by(PriceHistory.date.desc()).first()

        if oldest and newest:
            print(f"Date range: {oldest.date} to {newest.date}")

    except Exception as e:
        print(f"ERROR: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Fetch historical data from Yahoo Finance (free)")
    parser.add_argument("--days", type=int, default=3650, help="Number of days to backfill (default: 3650 = 10 years)")
    parser.add_argument("--symbols", type=str, help="Comma-separated symbols (default: SPY,QQQ,DIA)")

    args = parser.parse_args()

    symbols = DEFAULT_SYMBOLS
    if args.symbols:
        symbols = [s.strip().upper() for s in args.symbols.split(',')]

    backfill_from_yahoo(symbols=symbols, days=args.days)
