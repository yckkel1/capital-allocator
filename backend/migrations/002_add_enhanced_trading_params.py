"""
Migration: Add enhanced trading parameters
- Mean reversion signals (RSI, Bollinger Bands)
- Adaptive thresholds
- Confidence-based position sizing
- Circuit breaker parameters
"""
import os
import sys
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")


def upgrade():
    """Add new columns to trading_config table"""
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    try:
        # Add mean reversion parameters
        cursor.execute("""
            ALTER TABLE trading_config
            ADD COLUMN IF NOT EXISTS rsi_oversold_threshold FLOAT NOT NULL DEFAULT 30.0,
            ADD COLUMN IF NOT EXISTS rsi_overbought_threshold FLOAT NOT NULL DEFAULT 70.0,
            ADD COLUMN IF NOT EXISTS bollinger_std_multiplier FLOAT NOT NULL DEFAULT 2.0,
            ADD COLUMN IF NOT EXISTS mean_reversion_allocation FLOAT NOT NULL DEFAULT 0.4;
        """)

        # Add adaptive threshold parameters
        cursor.execute("""
            ALTER TABLE trading_config
            ADD COLUMN IF NOT EXISTS volatility_adjustment_factor FLOAT NOT NULL DEFAULT 0.4,
            ADD COLUMN IF NOT EXISTS base_volatility FLOAT NOT NULL DEFAULT 0.01;
        """)

        # Add confidence-based position sizing parameters
        cursor.execute("""
            ALTER TABLE trading_config
            ADD COLUMN IF NOT EXISTS min_confidence_threshold FLOAT NOT NULL DEFAULT 0.3,
            ADD COLUMN IF NOT EXISTS confidence_scaling_factor FLOAT NOT NULL DEFAULT 0.5;
        """)

        # Add circuit breaker parameters
        cursor.execute("""
            ALTER TABLE trading_config
            ADD COLUMN IF NOT EXISTS intramonth_drawdown_limit FLOAT NOT NULL DEFAULT 0.10,
            ADD COLUMN IF NOT EXISTS circuit_breaker_reduction FLOAT NOT NULL DEFAULT 0.5;
        """)

        conn.commit()
        print("Migration 002: Added enhanced trading parameters successfully")

    except Exception as e:
        conn.rollback()
        print(f"Migration 002 failed: {e}")
        raise
    finally:
        cursor.close()
        conn.close()


def downgrade():
    """Remove new columns from trading_config table"""
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    try:
        cursor.execute("""
            ALTER TABLE trading_config
            DROP COLUMN IF EXISTS rsi_oversold_threshold,
            DROP COLUMN IF EXISTS rsi_overbought_threshold,
            DROP COLUMN IF EXISTS bollinger_std_multiplier,
            DROP COLUMN IF EXISTS mean_reversion_allocation,
            DROP COLUMN IF EXISTS volatility_adjustment_factor,
            DROP COLUMN IF EXISTS base_volatility,
            DROP COLUMN IF EXISTS min_confidence_threshold,
            DROP COLUMN IF EXISTS confidence_scaling_factor,
            DROP COLUMN IF EXISTS intramonth_drawdown_limit,
            DROP COLUMN IF EXISTS circuit_breaker_reduction;
        """)

        conn.commit()
        print("Migration 002: Removed enhanced trading parameters successfully")

    except Exception as e:
        conn.rollback()
        print(f"Downgrade 002 failed: {e}")
        raise
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "downgrade":
        downgrade()
    else:
        upgrade()
