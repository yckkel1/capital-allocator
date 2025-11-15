"""
Migration: Add test tables for E2E testing
Created: 2025-11-15

This migration creates test tables that mirror production tables
for isolated end-to-end testing without affecting production data.
"""
import os
import sys
from datetime import date
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg2
from psycopg2.extras import RealDictCursor

# Load environment variables from .env file if DATABASE_URL not set
if not os.getenv("DATABASE_URL"):
    env_file = Path(__file__).parent.parent / '.env.dev'
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value

DATABASE_URL = os.getenv("DATABASE_URL")


def run_migration():
    """Execute the migration to create test tables"""
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:
        print("Starting migration: Add test tables for E2E testing...")

        # Create ActionType enum if not exists (for test_trades table)
        print("  Ensuring ActionType enum exists...")
        cursor.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'actiontype') THEN
                    CREATE TYPE actiontype AS ENUM ('BUY', 'SELL', 'HOLD');
                END IF;
            END$$;
        """)

        # Create test_price_history table
        print("  Creating test_price_history table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS test_price_history (
                id SERIAL PRIMARY KEY,
                date DATE NOT NULL,
                symbol VARCHAR(10) NOT NULL,
                open_price DOUBLE PRECISION NOT NULL,
                high_price DOUBLE PRECISION NOT NULL,
                low_price DOUBLE PRECISION NOT NULL,
                close_price DOUBLE PRECISION NOT NULL,
                volume DOUBLE PRECISION NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_test_price_history_date
            ON test_price_history(date)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_test_price_history_symbol
            ON test_price_history(symbol)
        """)

        # Create test_daily_signals table
        print("  Creating test_daily_signals table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS test_daily_signals (
                id SERIAL PRIMARY KEY,
                trade_date DATE NOT NULL UNIQUE,
                generated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                allocations JSONB NOT NULL,
                model_type VARCHAR(50) NOT NULL,
                confidence_score DOUBLE PRECISION,
                features_used JSONB
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_test_daily_signals_trade_date
            ON test_daily_signals(trade_date)
        """)

        # Create test_trades table
        print("  Creating test_trades table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS test_trades (
                id SERIAL PRIMARY KEY,
                trade_date DATE NOT NULL,
                executed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                symbol VARCHAR(10) NOT NULL,
                action actiontype NOT NULL,
                quantity DOUBLE PRECISION NOT NULL,
                price DOUBLE PRECISION NOT NULL,
                amount DOUBLE PRECISION NOT NULL,
                signal_id INTEGER
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_test_trades_trade_date
            ON test_trades(trade_date)
        """)

        # Create test_portfolio table
        print("  Creating test_portfolio table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS test_portfolio (
                id SERIAL PRIMARY KEY,
                symbol VARCHAR(10) NOT NULL UNIQUE,
                quantity DOUBLE PRECISION NOT NULL DEFAULT 0,
                avg_cost DOUBLE PRECISION NOT NULL DEFAULT 0,
                last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create test_performance_metrics table
        print("  Creating test_performance_metrics table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS test_performance_metrics (
                id SERIAL PRIMARY KEY,
                date DATE NOT NULL UNIQUE,
                portfolio_value DOUBLE PRECISION NOT NULL,
                cash_balance DOUBLE PRECISION NOT NULL,
                total_value DOUBLE PRECISION NOT NULL,
                daily_return DOUBLE PRECISION,
                cumulative_return DOUBLE PRECISION,
                sharpe_ratio DOUBLE PRECISION,
                max_drawdown DOUBLE PRECISION,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_test_performance_metrics_date
            ON test_performance_metrics(date)
        """)

        # Create test_trading_config table
        print("  Creating test_trading_config table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS test_trading_config (
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

                -- Mean Reversion Parameters
                rsi_oversold_threshold DOUBLE PRECISION NOT NULL DEFAULT 30.0,
                rsi_overbought_threshold DOUBLE PRECISION NOT NULL DEFAULT 70.0,
                bollinger_std_multiplier DOUBLE PRECISION NOT NULL DEFAULT 2.0,
                mean_reversion_allocation DOUBLE PRECISION NOT NULL DEFAULT 0.4,

                -- Adaptive Threshold Parameters
                volatility_adjustment_factor DOUBLE PRECISION NOT NULL DEFAULT 0.4,
                base_volatility DOUBLE PRECISION NOT NULL DEFAULT 0.01,

                -- Confidence-Based Position Sizing
                min_confidence_threshold DOUBLE PRECISION NOT NULL DEFAULT 0.3,
                confidence_scaling_factor DOUBLE PRECISION NOT NULL DEFAULT 0.5,

                -- Circuit Breaker Parameters
                intramonth_drawdown_limit DOUBLE PRECISION NOT NULL DEFAULT 0.10,
                circuit_breaker_reduction DOUBLE PRECISION NOT NULL DEFAULT 0.5,

                -- Metadata
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                created_by VARCHAR(100),
                notes VARCHAR(500)
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_test_trading_config_start_date
            ON test_trading_config(start_date)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_test_trading_config_end_date
            ON test_trading_config(end_date)
        """)

        # Insert default test trading config (start from epoch for all backtest dates)
        print("  Inserting default test trading configuration...")
        cursor.execute("""
            INSERT INTO test_trading_config (
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
                'migration_003',
                'Default test configuration for E2E testing'
            )
        """, (date(1970, 1, 1), '["SPY", "QQQ", "DIA"]'))

        conn.commit()
        print("Migration completed successfully!")

        # Display summary
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name LIKE 'test_%'
            ORDER BY table_name
        """)
        test_tables = [row['table_name'] for row in cursor.fetchall()]
        print(f"\nCreated {len(test_tables)} test tables:")
        for table in test_tables:
            print(f"  - {table}")

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
        print("Rolling back migration: Drop test tables...")

        # Drop all test tables
        cursor.execute("DROP TABLE IF EXISTS test_price_history CASCADE")
        cursor.execute("DROP TABLE IF EXISTS test_daily_signals CASCADE")
        cursor.execute("DROP TABLE IF EXISTS test_trades CASCADE")
        cursor.execute("DROP TABLE IF EXISTS test_portfolio CASCADE")
        cursor.execute("DROP TABLE IF EXISTS test_performance_metrics CASCADE")
        cursor.execute("DROP TABLE IF EXISTS test_trading_config CASCADE")

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
    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        rollback_migration()
    else:
        run_migration()
