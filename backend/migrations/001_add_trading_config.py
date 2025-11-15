"""
Migration: Add trading_config table for versioned configuration
Created: 2025-11-13

This migration creates the trading_config table and populates it with
initial configuration from the current .env.dev file.
"""
import os
import sys
from datetime import date
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def run_migration():
    """Execute the migration"""
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:
        print("Starting migration: Add trading_config table...")

        # Create the trading_config table
        print("  Creating trading_config table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trading_config (
                id SERIAL PRIMARY KEY,
                start_date DATE NOT NULL,
                end_date DATE,

                -- Basic Trading Parameters
                daily_capital DOUBLE PRECISION NOT NULL DEFAULT 1000.0,
                assets JSONB NOT NULL,
                lookback_days INTEGER NOT NULL DEFAULT 252,

                -- Regime Detection Thresholds
                regime_bullish_threshold DOUBLE PRECISION NOT NULL DEFAULT 0.3,
                regime_bearish_threshold DOUBLE PRECISION NOT NULL DEFAULT -0.3,

                -- Risk Level Thresholds
                risk_high_threshold DOUBLE PRECISION NOT NULL DEFAULT 70.0,
                risk_medium_threshold DOUBLE PRECISION NOT NULL DEFAULT 40.0,

                -- Allocation Percentages (Bullish Regime)
                allocation_low_risk DOUBLE PRECISION NOT NULL DEFAULT 0.8,
                allocation_medium_risk DOUBLE PRECISION NOT NULL DEFAULT 0.5,
                allocation_high_risk DOUBLE PRECISION NOT NULL DEFAULT 0.3,

                -- Neutral Regime Allocation
                allocation_neutral DOUBLE PRECISION NOT NULL DEFAULT 0.2,

                -- Sell Percentage (Bearish Regime)
                sell_percentage DOUBLE PRECISION NOT NULL DEFAULT 0.7,

                -- Asset Ranking Weights
                momentum_weight DOUBLE PRECISION NOT NULL DEFAULT 0.6,
                price_momentum_weight DOUBLE PRECISION NOT NULL DEFAULT 0.4,

                -- Risk Management Targets
                max_drawdown_tolerance DOUBLE PRECISION NOT NULL DEFAULT 15.0,
                min_sharpe_target DOUBLE PRECISION NOT NULL DEFAULT 1.0,

                -- Metadata
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                created_by VARCHAR(100),
                notes VARCHAR(500)
            )
        """)

        # Create indexes
        print("  Creating indexes...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_trading_config_start_date
            ON trading_config(start_date)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_trading_config_end_date
            ON trading_config(end_date)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_trading_config_active
            ON trading_config(start_date, end_date)
            WHERE end_date IS NULL
        """)

        # Insert initial configuration (from .env.dev defaults)
        print("  Inserting initial configuration...")
        cursor.execute("""
            INSERT INTO trading_config (
                start_date,
                end_date,
                daily_capital,
                assets,
                lookback_days,
                regime_bullish_threshold,
                regime_bearish_threshold,
                risk_high_threshold,
                risk_medium_threshold,
                allocation_low_risk,
                allocation_medium_risk,
                allocation_high_risk,
                allocation_neutral,
                sell_percentage,
                momentum_weight,
                price_momentum_weight,
                max_drawdown_tolerance,
                min_sharpe_target,
                created_by,
                notes
            ) VALUES (
                %s, NULL, 1000.0, %s, 252,
                0.3, -0.3,
                70.0, 40.0,
                0.8, 0.5, 0.3,
                0.2, 0.7,
                0.6, 0.4,
                15.0, 1.0,
                'migration_001',
                'Initial configuration migrated from .env.dev'
            )
        """, (date(1970, 1, 1), '["SPY", "QQQ", "DIA"]'))

        conn.commit()
        print("Migration completed successfully!")

        # Display the inserted config
        cursor.execute("""
            SELECT * FROM trading_config ORDER BY id DESC LIMIT 1
        """)
        config = cursor.fetchone()
        print(f"\nInitial config created with ID: {config['id']}")
        print(f"  Start Date: {config['start_date']}")
        print(f"  End Date: {config['end_date']} (NULL = active)")
        print(f"  Daily Capital: ${config['daily_capital']}")
        print(f"  Assets: {config['assets']}")

    except Exception as e:
        conn.rollback()
        print(f"Migration failed: {e}")
        raise
    finally:
        cursor.close()
        conn.close()


def rollback_migration():
    """Rollback the migration"""
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    try:
        print("Rolling back migration: Add trading_config table...")
        cursor.execute("DROP TABLE IF EXISTS trading_config CASCADE")
        conn.commit()
        print("Rollback completed successfully!")
    except Exception as e:
        conn.rollback()
        print(f"Rollback failed: {e}")
        raise
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        rollback_migration()
    else:
        run_migration()
