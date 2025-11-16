"""
End-to-End Tests for Capital Allocator
These tests use isolated test database tables to run complete workflows.
"""
import pytest
import json
import os
import shutil
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

# Import test fixtures and utilities
from tests.e2e.test_database import E2ETestDatabaseManager


class TestE2EBacktestWorkflow:
    """E2E tests for complete backtest workflows using test tables"""

    @pytest.fixture
    def mock_db_connection(self):
        """Mock database connection for E2E tests"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        # Setup default responses
        mock_cursor.fetchone.return_value = {
            'daily_capital': 1000.0,
            'min_date': date(2024, 11, 11),
            'max_date': date(2025, 11, 10),
            'count': 783,
            'exists': True,
            'total_injected': 1000.0,
            'total_proceeds': 0.0,
            'total_value': 1000.0,
            'total_spent': 1000.0,
            'invested_today': 333.33,
            'portfolio_value': 1050.0
        }

        mock_cursor.fetchall.return_value = []

        with patch('psycopg2.connect', return_value=mock_conn):
            yield mock_conn, mock_cursor

    @pytest.fixture
    def test_price_data_file(self, tmp_path):
        """Create temporary test price data file"""
        # Generate sample price data for 5 trading days
        data = {
            'metadata': {
                'generated_at': '2025-11-15',
                'min_date': '2024-12-01',
                'max_date': '2024-12-05',
                'symbols': ['SPY', 'QQQ', 'DIA'],
                'total_records': 15
            },
            'data': []
        }

        # Create 5 days of data for 3 symbols
        base_prices = {'SPY': 550.0, 'QQQ': 480.0, 'DIA': 420.0}

        for day_offset in range(5):
            trade_date = date(2024, 12, 1) + timedelta(days=day_offset)
            # Skip weekends
            if trade_date.weekday() >= 5:
                continue

            for symbol in ['SPY', 'QQQ', 'DIA']:
                base = base_prices[symbol] * (1 + day_offset * 0.001)
                data['data'].append({
                    'date': trade_date.isoformat(),
                    'symbol': symbol,
                    'open_price': round(base, 2),
                    'high_price': round(base * 1.01, 2),
                    'low_price': round(base * 0.99, 2),
                    'close_price': round(base * 1.005, 2),
                    'volume': 50000000
                })

        json_file = tmp_path / 'test_prices.json'
        with open(json_file, 'w') as f:
            json.dump(data, f)

        return json_file

    @pytest.fixture
    def test_report_dir(self, tmp_path):
        """Create temporary report directory"""
        report_dir = tmp_path / 'test-reports'
        report_dir.mkdir(parents=True, exist_ok=True)
        return report_dir

    def test_test_database_manager_initialization(self, mock_db_connection):
        """Test that E2ETestDatabaseManager initializes correctly"""
        mock_conn, mock_cursor = mock_db_connection

        with patch.dict(os.environ, {'DATABASE_URL': 'postgresql://test:test@localhost/test'}):
            manager = E2ETestDatabaseManager()
            assert manager.database_url == 'postgresql://test:test@localhost/test'
            assert manager.conn is None
            assert manager.cursor is None

    def test_table_mapping_completeness(self):
        """Test that all production tables have test equivalents"""
        expected_tables = [
            'price_history',
            'daily_signals',
            'trades',
            'portfolio',
            'performance_metrics',
            'trading_config'
        ]

        for table in expected_tables:
            assert table in E2ETestDatabaseManager.TABLE_MAPPING
            assert E2ETestDatabaseManager.TABLE_MAPPING[table].startswith('test_')

    def test_clear_all_test_tables(self, mock_db_connection):
        """Test clearing all test tables"""
        mock_conn, mock_cursor = mock_db_connection

        with patch.dict(os.environ, {'DATABASE_URL': 'postgresql://test:test@localhost/test'}):
            with E2ETestDatabaseManager() as manager:
                manager.clear_all_test_tables()

        # Verify DELETE was called for each table
        delete_calls = [
            call for call in mock_cursor.execute.call_args_list
            if 'DELETE FROM' in str(call)
        ]
        assert len(delete_calls) >= 5  # At least 5 tables cleared

    def test_clear_test_trading_data(self, mock_db_connection):
        """Test clearing only trading data (not price history)"""
        mock_conn, mock_cursor = mock_db_connection

        with patch.dict(os.environ, {'DATABASE_URL': 'postgresql://test:test@localhost/test'}):
            with E2ETestDatabaseManager() as manager:
                manager.clear_test_trading_data()

        # Verify DELETE was called but NOT for price_history
        delete_calls = [str(call) for call in mock_cursor.execute.call_args_list]
        delete_strs = ''.join(delete_calls)

        assert 'test_performance_metrics' in delete_strs
        assert 'test_trades' in delete_strs
        assert 'test_daily_signals' in delete_strs
        assert 'test_portfolio' in delete_strs
        # Should not delete price history
        price_history_deletes = [
            call for call in delete_calls
            if 'test_price_history' in call and 'DELETE' in call
        ]
        assert len(price_history_deletes) == 0

    def test_load_price_history_from_file(self, mock_db_connection, test_price_data_file):
        """Test loading price history from JSON fixture"""
        mock_conn, mock_cursor = mock_db_connection

        with patch.dict(os.environ, {'DATABASE_URL': 'postgresql://test:test@localhost/test'}):
            with patch('tests.e2e.test_database.execute_values') as mock_execute_values:
                with E2ETestDatabaseManager() as manager:
                    records_loaded = manager.load_price_history_from_file(str(test_price_data_file))

        # Should have loaded records for 5 trading days * 3 symbols
        # But we skip weekends, so actual count depends on the days
        assert records_loaded > 0
        mock_execute_values.assert_called_once()

    def test_reset_test_trading_config(self, mock_db_connection):
        """Test resetting test trading config to defaults"""
        mock_conn, mock_cursor = mock_db_connection

        with patch.dict(os.environ, {'DATABASE_URL': 'postgresql://test:test@localhost/test'}):
            with E2ETestDatabaseManager() as manager:
                manager.reset_test_trading_config()

        # Verify INSERT was called with default config
        insert_calls = [
            call for call in mock_cursor.execute.call_args_list
            if 'INSERT INTO test_trading_config' in str(call)
        ]
        assert len(insert_calls) == 1

    def test_verify_test_tables_exist_all_present(self, mock_db_connection):
        """Test verification when all test tables exist"""
        mock_conn, mock_cursor = mock_db_connection
        mock_cursor.fetchone.return_value = {'exists': True}

        with patch.dict(os.environ, {'DATABASE_URL': 'postgresql://test:test@localhost/test'}):
            with E2ETestDatabaseManager() as manager:
                exists, message = manager.verify_test_tables_exist()

        assert exists is True
        assert message == "All test tables exist"

    def test_verify_test_tables_exist_missing_table(self, mock_db_connection):
        """Test verification when a test table is missing"""
        mock_conn, mock_cursor = mock_db_connection
        # First table check returns False
        mock_cursor.fetchone.side_effect = [{'exists': False}]

        with patch.dict(os.environ, {'DATABASE_URL': 'postgresql://test:test@localhost/test'}):
            with E2ETestDatabaseManager() as manager:
                exists, message = manager.verify_test_tables_exist()

        assert exists is False
        assert "does not exist" in message

    def test_get_test_price_history_range(self, mock_db_connection):
        """Test getting date range from test price history"""
        mock_conn, mock_cursor = mock_db_connection
        mock_cursor.fetchone.return_value = {
            'min_date': date(2024, 11, 11),
            'max_date': date(2025, 11, 10),
            'count': 783
        }

        with patch.dict(os.environ, {'DATABASE_URL': 'postgresql://test:test@localhost/test'}):
            with E2ETestDatabaseManager() as manager:
                result = manager.get_test_price_history_range()

        assert result['min_date'] == date(2024, 11, 11)
        assert result['max_date'] == date(2025, 11, 10)
        assert result['count'] == 783

    def test_get_test_trading_days(self, mock_db_connection):
        """Test getting trading days from test tables"""
        mock_conn, mock_cursor = mock_db_connection
        mock_cursor.fetchall.return_value = [
            {'date': date(2024, 12, 2)},
            {'date': date(2024, 12, 3)},
            {'date': date(2024, 12, 4)},
        ]

        with patch.dict(os.environ, {'DATABASE_URL': 'postgresql://test:test@localhost/test'}):
            with E2ETestDatabaseManager() as manager:
                days = manager.get_test_trading_days(date(2024, 12, 1), date(2024, 12, 5))

        assert len(days) == 3
        assert days[0] == date(2024, 12, 2)

    def test_get_test_performance_summary(self, mock_db_connection):
        """Test getting performance summary from test tables"""
        mock_conn, mock_cursor = mock_db_connection
        mock_cursor.fetchone.return_value = {
            'total_days': 21,
            'first_date': date(2024, 12, 1),
            'last_date': date(2024, 12, 31),
            'min_value': 20000.0,
            'max_value': 25000.0
        }

        with patch.dict(os.environ, {'DATABASE_URL': 'postgresql://test:test@localhost/test'}):
            with E2ETestDatabaseManager() as manager:
                summary = manager.get_test_performance_summary(date(2024, 12, 1), date(2024, 12, 31))

        assert summary['total_days'] == 21
        assert summary['min_value'] == 20000.0
        assert summary['max_value'] == 25000.0


class TestE2EBacktest:
    """Tests for E2E Backtest functionality"""

    @pytest.fixture
    def mock_db_for_backtest(self):
        """Mock database for backtest tests"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        # Default responses
        mock_cursor.fetchone.return_value = {
            'daily_capital': 1000.0,
            'id': 1,
            'allocations': {'SPY': 333.33, 'QQQ': 333.33, 'DIA': 333.33},
            'total_injected': 1000.0,
            'total_proceeds': 0.0,
            'total_value': 1000.0
        }

        mock_cursor.fetchall.return_value = [
            {'date': date(2024, 12, 2)},
            {'date': date(2024, 12, 3)},
        ]

        with patch('psycopg2.connect', return_value=mock_conn):
            yield mock_conn, mock_cursor

    def test_e2e_backtest_initialization(self, mock_db_for_backtest):
        """Test E2E backtest initializes with test tables"""
        mock_conn, mock_cursor = mock_db_for_backtest

        with patch.dict(os.environ, {'DATABASE_URL': 'postgresql://test:test@localhost/test'}):
            from tests.e2e.e2e_backtest import E2EBacktest

            backtest = E2EBacktest(date(2024, 12, 1), date(2024, 12, 31))

            assert backtest.start_date == date(2024, 12, 1)
            assert backtest.end_date == date(2024, 12, 31)
            assert backtest.daily_budget > 0
            backtest.close()

    def test_e2e_backtest_uses_test_config_table(self, mock_db_for_backtest):
        """Test that backtest reads from test_trading_config"""
        mock_conn, mock_cursor = mock_db_for_backtest

        with patch.dict(os.environ, {'DATABASE_URL': 'postgresql://test:test@localhost/test'}):
            from tests.e2e.e2e_backtest import E2EBacktest

            backtest = E2EBacktest(date(2024, 12, 1), date(2024, 12, 31))
            backtest.close()

        # Verify test_trading_config was queried
        sql_queries = [str(call) for call in mock_cursor.execute.call_args_list]
        test_config_queries = [q for q in sql_queries if 'test_trading_config' in q]
        assert len(test_config_queries) > 0


class TestE2EAnalytics:
    """Tests for E2E Analytics functionality"""

    @pytest.fixture
    def mock_db_for_analytics(self):
        """Mock database for analytics tests"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.fetchone.return_value = {
            'daily_capital': 1000.0,
            'total_spent': 21000.0,
            'total_proceeds': 0.0,
            'invested_today': 1000.0
        }

        mock_cursor.fetchall.return_value = [
            {
                'date': date(2024, 12, 2),
                'portfolio_value': 21500.0,
                'cash_balance': 0.0,
                'total_value': 21500.0,
                'daily_return': 0.5,
                'cumulative_return': 2.38
            },
        ]

        with patch('psycopg2.connect', return_value=mock_conn):
            yield mock_conn, mock_cursor

    def test_e2e_analytics_initialization(self, mock_db_for_analytics):
        """Test E2E analytics initializes correctly"""
        mock_conn, mock_cursor = mock_db_for_analytics

        with patch.dict(os.environ, {'DATABASE_URL': 'postgresql://test:test@localhost/test'}):
            from tests.e2e.e2e_analytics import E2EAnalytics

            analytics = E2EAnalytics(date(2024, 12, 1), date(2024, 12, 31))

            assert analytics.start_date == date(2024, 12, 1)
            assert analytics.end_date == date(2024, 12, 31)
            assert analytics.daily_budget > 0
            analytics.close()

    def test_e2e_analytics_uses_test_tables(self, mock_db_for_analytics):
        """Test that analytics queries test tables"""
        mock_conn, mock_cursor = mock_db_for_analytics

        with patch.dict(os.environ, {'DATABASE_URL': 'postgresql://test:test@localhost/test'}):
            from tests.e2e.e2e_analytics import E2EAnalytics

            analytics = E2EAnalytics(date(2024, 12, 1), date(2024, 12, 31))
            analytics.get_performance_data()
            analytics.close()

        # Verify test_performance_metrics was queried
        sql_queries = [str(call) for call in mock_cursor.execute.call_args_list]
        test_metrics_queries = [q for q in sql_queries if 'test_performance_metrics' in q]
        assert len(test_metrics_queries) > 0

    def test_sharpe_ratio_calculation(self, mock_db_for_analytics):
        """Test Sharpe ratio calculation"""
        mock_conn, mock_cursor = mock_db_for_analytics

        with patch.dict(os.environ, {'DATABASE_URL': 'postgresql://test:test@localhost/test'}):
            from tests.e2e.e2e_analytics import E2EAnalytics

            analytics = E2EAnalytics(date(2024, 12, 1), date(2024, 12, 31))

            # Test with sample returns
            daily_returns = [0.5, 0.3, -0.2, 0.4, 0.1]
            sharpe = analytics.calculate_sharpe_ratio(daily_returns)

            assert isinstance(sharpe, float)
            # Sharpe should be a reasonable value (can be high with small sample size)
            assert -20 < sharpe < 20

            analytics.close()

    def test_max_drawdown_calculation(self, mock_db_for_analytics):
        """Test max drawdown calculation"""
        mock_conn, mock_cursor = mock_db_for_analytics

        with patch.dict(os.environ, {'DATABASE_URL': 'postgresql://test:test@localhost/test'}):
            from tests.e2e.e2e_analytics import E2EAnalytics

            analytics = E2EAnalytics(date(2024, 12, 1), date(2024, 12, 31))

            # Test data with a clear drawdown
            performance_data = [
                {'total_value': 1000.0, 'date': date(2024, 12, 1)},
                {'total_value': 1050.0, 'date': date(2024, 12, 2)},  # Peak
                {'total_value': 945.0, 'date': date(2024, 12, 3)},   # 10% drawdown
                {'total_value': 980.0, 'date': date(2024, 12, 4)},
            ]

            result = analytics.calculate_max_drawdown(performance_data)

            assert 'max_drawdown' in result
            assert result['max_drawdown'] == pytest.approx(10.0, rel=0.1)
            assert result['peak_date'] == date(2024, 12, 2)
            assert result['trough_date'] == date(2024, 12, 3)

            analytics.close()


class TestE2EReportGeneration:
    """Tests for E2E report file generation and cleanup"""

    @pytest.fixture
    def test_reports_dir(self, tmp_path):
        """Create temporary test reports directory structure"""
        base_dir = tmp_path / 'data' / 'test-reports'
        (base_dir / 'backtest').mkdir(parents=True, exist_ok=True)
        (base_dir / 'analytics').mkdir(parents=True, exist_ok=True)
        (base_dir / 'tuning').mkdir(parents=True, exist_ok=True)

        # Create some dummy report files
        (base_dir / 'backtest' / 'old_report.txt').write_text("Old report")
        (base_dir / 'analytics' / 'old_analysis.txt').write_text("Old analysis")

        return base_dir

    def test_report_directories_created(self, test_reports_dir):
        """Test that report directories are properly created"""
        assert (test_reports_dir / 'backtest').exists()
        assert (test_reports_dir / 'analytics').exists()
        assert (test_reports_dir / 'tuning').exists()

    def test_old_reports_can_be_cleared(self, test_reports_dir):
        """Test that old reports can be cleared"""
        # Files exist before clearing
        assert (test_reports_dir / 'backtest' / 'old_report.txt').exists()
        assert (test_reports_dir / 'analytics' / 'old_analysis.txt').exists()

        # Clear reports
        for subdir in ['backtest', 'analytics', 'tuning']:
            subdir_path = test_reports_dir / subdir
            for file in subdir_path.glob('*'):
                if file.is_file():
                    file.unlink()

        # Verify files are gone
        assert not (test_reports_dir / 'backtest' / 'old_report.txt').exists()
        assert not (test_reports_dir / 'analytics' / 'old_analysis.txt').exists()

        # Directories still exist
        assert (test_reports_dir / 'backtest').exists()
        assert (test_reports_dir / 'analytics').exists()


class TestE2EIntegration:
    """Integration tests for the complete E2E workflow"""

    def test_table_mapping_consistency(self):
        """Test that table mapping is consistent and complete"""
        from tests.e2e.test_database import E2ETestDatabaseManager, create_test_sql_replacements

        replacements = create_test_sql_replacements()

        # Verify all standard SQL operations are mapped
        for prod_table in E2ETestDatabaseManager.TABLE_MAPPING.keys():
            assert f'FROM {prod_table}' in replacements
            assert f'INTO {prod_table}' in replacements
            assert f'UPDATE {prod_table}' in replacements
            assert f'DELETE FROM {prod_table}' in replacements

    def test_test_fixture_file_structure(self):
        """Test that test fixture files are properly structured"""
        fixtures_dir = Path(__file__).parent.parent / 'fixtures'

        # Check fixture directory exists
        assert fixtures_dir.exists()

        # Check price history fixture exists
        price_fixture = fixtures_dir / 'price_history_test_data.json'
        assert price_fixture.exists()

        # Validate JSON structure
        with open(price_fixture, 'r') as f:
            data = json.load(f)

        assert 'metadata' in data
        assert 'data' in data
        assert 'min_date' in data['metadata']
        assert 'max_date' in data['metadata']
        assert 'symbols' in data['metadata']
        assert 'total_records' in data['metadata']

        # Verify data records have required fields
        if data['data']:
            record = data['data'][0]
            required_fields = ['date', 'symbol', 'open_price', 'high_price',
                              'low_price', 'close_price', 'volume']
            for field in required_fields:
                assert field in record
