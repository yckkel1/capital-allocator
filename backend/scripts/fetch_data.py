"""
Daily data fetching script
Run this at market close (4:30 PM ET) to update price database
Uses Alpha Vantage API
"""

from alpha_vantage.timeseries import TimeSeries
import requests
from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session
import sys
import os
import time
import pandas as pd

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models import PriceHistory
from config import get_settings, get_trading_config

settings = get_settings()
trading_config = get_trading_config()  # Load trading parameters from database


def fetch_and_store_prices(target_date: date = None):
    """
    Fetch latest prices for all assets and store in database using Alpha Vantage
    
    Args:
        target_date: Date to fetch (defaults to today)
    """
    if target_date is None:
        target_date = date.today()
    
    db = SessionLocal()
    
    try:
        print(f"Fetching data for {target_date}...")
        
        # Initialize Alpha Vantage
        ts = TimeSeries(key=settings.alphavantage_api_key, output_format='pandas')
        
        for symbol in trading_config.assets:
            print(f"  Fetching {symbol}...")
            
            # Check if data already exists
            existing = db.query(PriceHistory).filter(
                PriceHistory.symbol == symbol,
                PriceHistory.date == target_date
            ).first()
            
            if existing:
                print(f"    {symbol} data already exists for {target_date}")
                continue
            
            # Retry logic for Alpha Vantage
            max_retries = 3
            data = None
            
            for attempt in range(max_retries):
                try:
                    # Fetch daily data (compact = last 100 days)
                    data, meta_data = ts.get_daily(symbol=symbol, outputsize='compact')
                    
                    if data is not None and not data.empty:
                        break
                    
                    if attempt < max_retries - 1:
                        print(f"    No data returned, retrying in 15 seconds... (attempt {attempt + 1}/{max_retries})")
                        time.sleep(15)  # Alpha Vantage rate limit: 5 calls/min
                except Exception as e:
                    if attempt < max_retries - 1:
                        print(f"    Error: {e}, retrying in 15 seconds... (attempt {attempt + 1}/{max_retries})")
                        time.sleep(15)
                    else:
                        print(f"    ERROR: Failed after {max_retries} attempts: {e}")
            
            if data is None or data.empty:
                print(f"    WARNING: No data returned for {symbol}")
                continue
            
            # Alpha Vantage returns data with index as datetime, columns: 1. open, 2. high, 3. low, 4. close, 5. volume
            # Convert index to date
            data.index = pd.to_datetime(data.index).date
            
            # Check if target_date exists in data
            if target_date not in data.index:
                print(f"    WARNING: {target_date} not in data for {symbol} (market closed?)")
                # Use the latest available date
                target_date = data.index[0]
                print(f"    Using latest available date: {target_date}")
            
            row = data.loc[target_date]
            
            # Store in database
            price_record = PriceHistory(
                date=target_date,
                symbol=symbol,
                open_price=float(row['1. open']),
                high_price=float(row['2. high']),
                low_price=float(row['3. low']),
                close_price=float(row['4. close']),
                volume=float(row['5. volume'])
            )
            
            db.add(price_record)
            db.commit()
            
            print(f"    ✓ {symbol}: Close=${row['4. close']:.2f}")
            
            # Alpha Vantage free tier: 5 calls/min, sleep between symbols
            time.sleep(13)  # ~12 seconds between calls to stay under limit
        
        print(f"\n✓ Data fetch complete for {target_date}")
        
    except Exception as e:
        print(f"ERROR: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def backfill_historical_data(days: int = 365):
    """
    Backfill historical data for model training using Alpha Vantage
    Note: Alpha Vantage free tier has 25 calls/day limit
    
    Args:
        days: Number of days to backfill (max ~100 for compact, ~20 years for full)
    """
    print(f"Backfilling historical data...")
    print(f"NOTE: Alpha Vantage free tier allows 5 calls/min, 25 calls/day")
    print(f"This will take approximately {len(trading_config.assets) * 13} seconds for {len(trading_config.assets)} symbols\n")
    
    db = SessionLocal()
    
    try:
        # Initialize Alpha Vantage
        # Use 'full' outputsize to get up to 20 years of data
        ts = TimeSeries(key=settings.alphavantage_api_key, output_format='pandas')
        outputsize = 'full' if days > 100 else 'compact'
        
        for symbol in trading_config.assets:
            print(f"Fetching {symbol}...")
            
            max_retries = 3
            data = None
            
            for attempt in range(max_retries):
                try:
                    data, meta_data = ts.get_daily(symbol=symbol, outputsize=outputsize)
                    
                    if data is not None and not data.empty:
                        break
                    
                    if attempt < max_retries - 1:
                        print(f"  No data returned, retrying in 15 seconds... (attempt {attempt + 1}/{max_retries})")
                        time.sleep(15)
                except Exception as e:
                    if attempt < max_retries - 1:
                        print(f"  Error: {e}, retrying in 15 seconds... (attempt {attempt + 1}/{max_retries})")
                        time.sleep(15)
                    else:
                        print(f"  ERROR: Failed after {max_retries} attempts: {e}")
            
            if data is None or data.empty:
                print(f"  WARNING: No data for {symbol}")
                continue
            
            # Convert index to date
            data.index = pd.to_datetime(data.index).date
            
            # Limit to requested number of days
            cutoff_date = date.today() - timedelta(days=days)
            data = data[data.index >= cutoff_date]
            
            count = 0
            for idx in range(len(data)):
                trade_date = data.index[idx]
                row = data.iloc[idx]
                
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
                    open_price=float(row['1. open']),
                    high_price=float(row['2. high']),
                    low_price=float(row['3. low']),
                    close_price=float(row['4. close']),
                    volume=float(row['5. volume'])
                )
                
                db.add(price_record)
                count += 1
            
            db.commit()
            print(f"  ✓ Added {count} records for {symbol}")
            
            # Sleep between symbols to respect rate limit (5 calls/min)
            if symbol != trading_config.assets[-1]:  # Don't sleep after last symbol
                print(f"  Waiting 13 seconds for rate limit...\n")
                time.sleep(13)
        
        print(f"\n✓ Backfill complete!")
        
    except Exception as e:
        print(f"ERROR: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Fetch market data")
    parser.add_argument("--backfill", type=int, help="Backfill N days of historical data")
    parser.add_argument("--date", type=str, help="Specific date to fetch (YYYY-MM-DD)")
    
    args = parser.parse_args()
    
    if args.backfill:
        backfill_historical_data(args.backfill)
    elif args.date:
        target = datetime.strptime(args.date, "%Y-%m-%d").date()
        fetch_and_store_prices(target)
    else:
        # Default: fetch today's data
        fetch_and_store_prices()