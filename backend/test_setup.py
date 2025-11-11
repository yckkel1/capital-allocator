"""
Quick test script to verify backend setup
"""

import sys
from datetime import date

print("Testing backend setup...\n")

# Test 1: Import dependencies
print("1. Testing imports...")
try:
    import fastapi
    import sqlalchemy
    import pandas
    import yfinance
    import sklearn
    print("   ✓ All dependencies imported successfully")
except ImportError as e:
    print(f"   ✗ Import error: {e}")
    print("   Run: pip install -r requirements.txt")
    sys.exit(1)

# Test 2: Load config
print("\n2. Testing configuration...")
try:
    from config import get_settings
    settings = get_settings()
    print(f"   ✓ Config loaded")
    print(f"   - Assets: {settings.assets}")
    print(f"   - Daily capital: ${settings.daily_capital}")
except Exception as e:
    print(f"   ✗ Config error: {e}")
    sys.exit(1)

# Test 3: Database connection
print("\n3. Testing database connection...")
try:
    from database import engine, Base
    from sqlalchemy import text
    import models  # Import models so they register with Base
    
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        result.fetchone()
    print("   ✓ Database connection successful")
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    print("   ✓ Database tables created")
    
except Exception as e:
    print(f"   ✗ Database error: {e}")
    print("   Make sure PostgreSQL is running and DATABASE_URL is correct in .env")
    sys.exit(1)

# Test 4: Check data
print("\n4. Checking for existing data...")
try:
    from database import SessionLocal
    from models import PriceHistory
    
    db = SessionLocal()
    count = db.query(PriceHistory).count()
    print(f"   - Price records in database: {count}")
    
    if count == 0:
        print("   ! Run: python scripts/fetch_data.py --backfill 365")
    else:
        latest = db.query(PriceHistory).order_by(
            PriceHistory.date.desc()
        ).first()
        print(f"   - Latest data: {latest.date}")
    
    db.close()
    
except Exception as e:
    print(f"   ✗ Data check error: {e}")

print("\n" + "="*50)
print("Setup verification complete!")
print("="*50)
print("\nNext steps:")
print("1. Start API: uvicorn main:app --reload")
print("2. Backfill data: python scripts/fetch_data.py --backfill 365")
print("3. Generate signal: python scripts/generate_signal.py")
print("4. Visit: http://localhost:8000/docs")