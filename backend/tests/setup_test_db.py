"""
Standalone test database setup - completely isolated from prod.

This script:
1. Drops all test_* tables
2. Creates fresh test_* tables
3. Seeds with minimal test data

Run before each test suite to ensure clean state.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg2
from config import get_settings

settings = get_settings()


def drop_test_tables():
    """Drop all test tables"""
    conn = psycopg2.connect(settings.database_url)
    cursor = conn.cursor()

    try:
        print("Dropping test tables...")
        cursor.execute("""
            DROP TABLE IF EXISTS test_performance_metrics CASCADE;
            DROP TABLE IF EXISTS test_trades CASCADE;
            DROP TABLE IF EXISTS test_daily_signals CASCADE;
            DROP TABLE IF EXISTS test_portfolio CASCADE;
            DROP TABLE IF EXISTS test_price_history CASCADE;
            DROP TABLE IF EXISTS test_trading_config CASCADE;
            DROP TYPE IF EXISTS test_actiontype CASCADE;
        """)
        conn.commit()
        print("  ✓ Dropped all test tables")
    finally:
        cursor.close()
        conn.close()


def create_test_tables():
    """Create fresh test tables"""
    conn = psycopg2.connect(settings.database_url)
    cursor = conn.cursor()

    try:
        print("Creating test tables...")

        # Create enum type
        cursor.execute("""
            CREATE TYPE test_actiontype AS ENUM ('BUY', 'SELL', 'HOLD');
        """)

        # test_price_history
        cursor.execute("""
            CREATE TABLE test_price_history (
                id SERIAL PRIMARY KEY,
                date DATE NOT NULL,
                symbol VARCHAR(10) NOT NULL,
                open_price FLOAT NOT NULL,
                high_price FLOAT NOT NULL,
                low_price FLOAT NOT NULL,
                close_price FLOAT NOT NULL,
                volume FLOAT NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX idx_test_price_history_date ON test_price_history(date);
            CREATE INDEX idx_test_price_history_symbol ON test_price_history(symbol);
        """)

        # test_daily_signals
        cursor.execute("""
            CREATE TABLE test_daily_signals (
                id SERIAL PRIMARY KEY,
                trade_date DATE NOT NULL UNIQUE,
                generated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                allocations JSON NOT NULL,
                model_type VARCHAR(50) NOT NULL,
                confidence_score FLOAT,
                features_used JSON
            );
            CREATE INDEX idx_test_daily_signals_trade_date ON test_daily_signals(trade_date);
        """)

        # test_trades
        cursor.execute("""
            CREATE TABLE test_trades (
                id SERIAL PRIMARY KEY,
                trade_date DATE NOT NULL,
                executed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                symbol VARCHAR(10) NOT NULL,
                action test_actiontype NOT NULL,
                quantity FLOAT NOT NULL,
                price FLOAT NOT NULL,
                amount FLOAT NOT NULL,
                signal_id INTEGER
            );
            CREATE INDEX idx_test_trades_trade_date ON test_trades(trade_date);
        """)

        # test_portfolio
        cursor.execute("""
            CREATE TABLE test_portfolio (
                id SERIAL PRIMARY KEY,
                symbol VARCHAR(10) NOT NULL UNIQUE,
                quantity FLOAT NOT NULL DEFAULT 0,
                avg_cost FLOAT NOT NULL DEFAULT 0,
                last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # test_performance_metrics
        cursor.execute("""
            CREATE TABLE test_performance_metrics (
                id SERIAL PRIMARY KEY,
                date DATE NOT NULL UNIQUE,
                portfolio_value FLOAT NOT NULL,
                cash_balance FLOAT NOT NULL,
                total_value FLOAT NOT NULL,
                daily_return FLOAT,
                cumulative_return FLOAT,
                sharpe_ratio FLOAT,
                max_drawdown FLOAT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX idx_test_performance_metrics_date ON test_performance_metrics(date);
        """)

        # test_trading_config
        cursor.execute("""
            CREATE TABLE test_trading_config (
                id SERIAL PRIMARY KEY,
                start_date DATE NOT NULL,
                end_date DATE,
                daily_capital FLOAT NOT NULL DEFAULT 1000.0,
                assets JSONB NOT NULL,
                lookback_days INTEGER NOT NULL DEFAULT 252,
                regime_bullish_threshold FLOAT NOT NULL DEFAULT 0.3,
                regime_bearish_threshold FLOAT NOT NULL DEFAULT -0.3,
                risk_high_threshold FLOAT NOT NULL DEFAULT 70.0,
                risk_medium_threshold FLOAT NOT NULL DEFAULT 40.0,
                allocation_low_risk FLOAT NOT NULL DEFAULT 0.8,
                allocation_medium_risk FLOAT NOT NULL DEFAULT 0.5,
                allocation_high_risk FLOAT NOT NULL DEFAULT 0.3,
                allocation_neutral FLOAT NOT NULL DEFAULT 0.2,
                sell_percentage FLOAT NOT NULL DEFAULT 0.7,
                momentum_weight FLOAT NOT NULL DEFAULT 0.6,
                price_momentum_weight FLOAT NOT NULL DEFAULT 0.4,
                max_drawdown_tolerance FLOAT NOT NULL DEFAULT 15.0,
                min_sharpe_target FLOAT NOT NULL DEFAULT 1.0,
                rsi_oversold_threshold FLOAT NOT NULL DEFAULT 30.0,
                rsi_overbought_threshold FLOAT NOT NULL DEFAULT 70.0,
                bollinger_std_multiplier FLOAT NOT NULL DEFAULT 2.0,
                mean_reversion_allocation FLOAT NOT NULL DEFAULT 0.4,
                volatility_adjustment_factor FLOAT NOT NULL DEFAULT 0.4,
                base_volatility FLOAT NOT NULL DEFAULT 0.01,
                min_confidence_threshold FLOAT NOT NULL DEFAULT 0.3,
                confidence_scaling_factor FLOAT NOT NULL DEFAULT 0.5,
                intramonth_drawdown_limit FLOAT NOT NULL DEFAULT 0.10,
                circuit_breaker_reduction FLOAT NOT NULL DEFAULT 0.5,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                created_by VARCHAR(100),
                notes VARCHAR(500)
            );
        """)

        conn.commit()
        print("  ✓ Created all test tables")
    finally:
        cursor.close()
        conn.close()


def seed_minimal_test_data():
    """Insert minimal test data for basic tests"""
    conn = psycopg2.connect(settings.database_url)
    cursor = conn.cursor()

    try:
        print("Seeding minimal test data...")

        # Insert test config
        cursor.execute("""
            INSERT INTO test_trading_config (
                start_date, assets, created_by, notes
            ) VALUES (
                '2020-01-01', '["SPY", "QQQ", "DIA"]'::jsonb,
                'test_setup', 'Minimal test configuration'
            );
        """)

        conn.commit()
        print("  ✓ Seeded test data")
    finally:
        cursor.close()
        conn.close()


def main():
    """Setup test database"""
    print("=" * 60)
    print("Test Database Setup - Standalone & Isolated")
    print("=" * 60)
    print()

    drop_test_tables()
    create_test_tables()
    seed_minimal_test_data()

    print()
    print("✓ Test database ready!")
    print("  All test_* tables are fresh and isolated from prod")


if __name__ == "__main__":
    main()
