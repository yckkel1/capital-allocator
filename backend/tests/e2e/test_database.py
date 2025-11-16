"""
Test database operations for E2E testing.
Provides utilities to set up and tear down test database tables.
"""
import json
import os
from datetime import date
from pathlib import Path

import psycopg2
from psycopg2.extras import RealDictCursor, execute_values


class E2ETestDatabaseManager:
    """Manages test database tables for E2E testing"""

    # Mapping from production to test table names
    TABLE_MAPPING = {
        'price_history': 'test_price_history',
        'daily_signals': 'test_daily_signals',
        'trades': 'test_trades',
        'portfolio': 'test_portfolio',
        'performance_metrics': 'test_performance_metrics',
        'trading_config': 'test_trading_config'
    }

    def __init__(self, database_url: str = None):
        if database_url is None:
            # Load from .env in repo root if DATABASE_URL not set
            if not os.getenv("DATABASE_URL"):
                env_file = Path(__file__).parent.parent.parent.parent / '.env'
                if env_file.exists():
                    with open(env_file) as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith('#') and '=' in line:
                                key, value = line.split('=', 1)
                                os.environ[key] = value
            database_url = os.getenv("DATABASE_URL")
        self.database_url = database_url
        self.conn = None
        self.cursor = None

    def connect(self):
        """Establish database connection"""
        self.conn = psycopg2.connect(self.database_url)
        self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)

    def close(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def clear_all_test_tables(self):
        """Clear all data from test tables"""
        tables = [
            'test_performance_metrics',
            'test_trades',
            'test_daily_signals',
            'test_portfolio',
            'test_price_history',
            # Don't clear test_trading_config as it has default config
        ]

        for table in tables:
            self.cursor.execute(f"DELETE FROM {table}")

        self.conn.commit()

    def clear_test_trading_data(self):
        """Clear only trading data (signals, trades, portfolio, metrics) - keep price history"""
        tables = [
            'test_performance_metrics',
            'test_trades',
            'test_daily_signals',
            'test_portfolio'
        ]

        for table in tables:
            self.cursor.execute(f"DELETE FROM {table}")

        self.conn.commit()

    def load_price_history_from_file(self, json_file: str = None):
        """Load price history data from JSON fixture file"""
        if json_file is None:
            json_file = Path(__file__).parent.parent / 'fixtures' / 'price_history_test_data.json'

        with open(json_file, 'r') as f:
            data = json.load(f)

        records = data['data']

        # Clear existing test price history
        self.cursor.execute("DELETE FROM test_price_history")

        # Insert price history in batches
        insert_query = """
            INSERT INTO test_price_history
            (date, symbol, open_price, high_price, low_price, close_price, volume)
            VALUES %s
        """

        values = [
            (
                record['date'],
                record['symbol'],
                record['open_price'],
                record['high_price'],
                record['low_price'],
                record['close_price'],
                record['volume']
            )
            for record in records
        ]

        execute_values(self.cursor, insert_query, values)
        self.conn.commit()

        return len(records)

    def reset_test_trading_config(self):
        """Reset test trading config to default values"""
        self.cursor.execute("DELETE FROM test_trading_config")

        self.cursor.execute("""
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
                rsi_oversold_threshold,
                rsi_overbought_threshold,
                bollinger_std_multiplier,
                mean_reversion_allocation,
                volatility_adjustment_factor,
                base_volatility,
                min_confidence_threshold,
                confidence_scaling_factor,
                intramonth_drawdown_limit,
                circuit_breaker_reduction,
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
                30.0, 70.0, 2.0, 0.4,
                0.4, 0.01,
                0.3, 0.5,
                0.10, 0.5,
                'e2e_test_reset',
                'Default test configuration for E2E testing'
            )
        """, (date(1970, 1, 1), '["SPY", "QQQ", "DIA"]'))

        self.conn.commit()

    def get_test_price_history_range(self):
        """Get the date range of test price history data"""
        self.cursor.execute("""
            SELECT MIN(date) as min_date, MAX(date) as max_date, COUNT(*) as count
            FROM test_price_history
        """)
        return self.cursor.fetchone()

    def get_test_trading_days(self, start_date: date, end_date: date):
        """Get trading days from test price history"""
        self.cursor.execute("""
            SELECT DISTINCT date
            FROM test_price_history
            WHERE date >= %s AND date <= %s
            AND symbol = 'SPY'
            ORDER BY date
        """, (start_date, end_date))
        return [row['date'] for row in self.cursor.fetchall()]

    def get_test_performance_summary(self, start_date: date, end_date: date):
        """Get performance metrics summary from test tables"""
        self.cursor.execute("""
            SELECT
                COUNT(*) as total_days,
                MIN(date) as first_date,
                MAX(date) as last_date,
                MIN(total_value) as min_value,
                MAX(total_value) as max_value
            FROM test_performance_metrics
            WHERE date >= %s AND date <= %s
        """, (start_date, end_date))
        return self.cursor.fetchone()

    def verify_test_tables_exist(self):
        """Verify all test tables exist"""
        for test_table in self.TABLE_MAPPING.values():
            self.cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = %s
                )
            """, (test_table,))

            if not self.cursor.fetchone()['exists']:
                return False, f"Table {test_table} does not exist"

        return True, "All test tables exist"


def get_test_table_name(production_table: str) -> str:
    """Get the test table name for a production table"""
    return E2ETestDatabaseManager.TABLE_MAPPING.get(production_table, production_table)


def create_test_sql_replacements() -> dict:
    """Create SQL replacement patterns for test tables"""
    replacements = {}
    for prod, test in E2ETestDatabaseManager.TABLE_MAPPING.items():
        replacements[f'FROM {prod}'] = f'FROM {test}'
        replacements[f'INTO {prod}'] = f'INTO {test}'
        replacements[f'UPDATE {prod}'] = f'UPDATE {test}'
        replacements[f'DELETE FROM {prod}'] = f'DELETE FROM {test}'
        replacements[f'"{prod}"'] = f'"{test}"'
    return replacements
