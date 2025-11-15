"""
Unit tests for backtest.py
Tests backtesting simulation engine
"""
import pytest
from unittest.mock import Mock, patch, MagicMock, mock_open
from datetime import date, datetime, timedelta
from decimal import Decimal
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestBacktestInit:
    """Test Backtest class initialization"""

    @patch('backtest.psycopg2.connect')
    @patch('backtest.get_settings')
    def test_backtest_init(self, mock_get_settings, mock_connect):
        """Test Backtest initialization"""
        mock_settings = Mock()
        mock_settings.database_url = "postgresql://test:test@localhost:5432/testdb"
        mock_get_settings.return_value = mock_settings

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        from backtest import Backtest

        start = date(2025, 11, 1)
        end = date(2025, 11, 15)
        backtest = Backtest(start, end)

        assert backtest.start_date == start
        assert backtest.end_date == end
        assert backtest.trading_days == []
        mock_connect.assert_called_once()

    @patch('backtest.psycopg2.connect')
    @patch('backtest.get_settings')
    def test_backtest_close(self, mock_get_settings, mock_connect):
        """Test Backtest close method"""
        mock_settings = Mock()
        mock_settings.database_url = "postgresql://test"
        mock_get_settings.return_value = mock_settings

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        from backtest import Backtest

        backtest = Backtest(date(2025, 11, 1), date(2025, 11, 15))
        backtest.close()

        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()


class TestGetTradingDays:
    """Test get_trading_days method"""

    @patch('backtest.psycopg2.connect')
    @patch('backtest.get_settings')
    def test_get_trading_days_success(self, mock_get_settings, mock_connect):
        """Test getting trading days successfully"""
        mock_settings = Mock()
        mock_settings.database_url = "postgresql://test"
        mock_get_settings.return_value = mock_settings

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.fetchall.return_value = [
            {'date': date(2025, 11, 1)},
            {'date': date(2025, 11, 4)},
            {'date': date(2025, 11, 5)},
        ]

        from backtest import Backtest

        backtest = Backtest(date(2025, 11, 1), date(2025, 11, 15))
        days = backtest.get_trading_days()

        assert len(days) == 3
        assert days[0] == date(2025, 11, 1)

    @patch('backtest.psycopg2.connect')
    @patch('backtest.get_settings')
    def test_get_trading_days_no_data(self, mock_get_settings, mock_connect):
        """Test getting trading days with no data"""
        mock_settings = Mock()
        mock_settings.database_url = "postgresql://test"
        mock_get_settings.return_value = mock_settings

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = []

        from backtest import Backtest

        backtest = Backtest(date(2025, 11, 1), date(2025, 11, 15))

        with pytest.raises(Exception) as exc_info:
            backtest.get_trading_days()

        assert "No data found" in str(exc_info.value)


class TestClearBacktestData:
    """Test clear_backtest_data method"""

    @patch('backtest.psycopg2.connect')
    @patch('backtest.get_settings')
    def test_clear_backtest_data(self, mock_get_settings, mock_connect):
        """Test clearing backtest data"""
        mock_settings = Mock()
        mock_settings.database_url = "postgresql://test"
        mock_get_settings.return_value = mock_settings

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        from backtest import Backtest

        backtest = Backtest(date(2025, 11, 1), date(2025, 11, 15))
        backtest.clear_backtest_data()

        # Should execute multiple DELETE queries
        assert mock_cursor.execute.call_count >= 4
        mock_conn.commit.assert_called_once()


class TestGenerateSignal:
    """Test generate_signal method"""

    @patch('backtest.subprocess.run')
    @patch('backtest.psycopg2.connect')
    @patch('backtest.get_settings')
    def test_generate_signal_success(self, mock_get_settings, mock_connect, mock_subprocess):
        """Test signal generation success"""
        mock_settings = Mock()
        mock_settings.database_url = "postgresql://test"
        mock_get_settings.return_value = mock_settings
        mock_connect.return_value = MagicMock()

        mock_result = Mock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        from backtest import Backtest

        backtest = Backtest(date(2025, 11, 1), date(2025, 11, 15))
        result = backtest.generate_signal(date(2025, 11, 15))

        assert result is True
        mock_subprocess.assert_called_once()

    @patch('backtest.subprocess.run')
    @patch('backtest.psycopg2.connect')
    @patch('backtest.get_settings')
    def test_generate_signal_failure(self, mock_get_settings, mock_connect, mock_subprocess):
        """Test signal generation failure"""
        mock_settings = Mock()
        mock_settings.database_url = "postgresql://test"
        mock_get_settings.return_value = mock_settings
        mock_connect.return_value = MagicMock()

        mock_result = Mock()
        mock_result.returncode = 1
        mock_subprocess.return_value = mock_result

        from backtest import Backtest

        backtest = Backtest(date(2025, 11, 1), date(2025, 11, 15))
        result = backtest.generate_signal(date(2025, 11, 15))

        assert result is False


class TestExecuteTrades:
    """Test execute_trades method"""

    @patch('backtest.subprocess.run')
    @patch('backtest.psycopg2.connect')
    @patch('backtest.get_settings')
    def test_execute_trades_success(self, mock_get_settings, mock_connect, mock_subprocess):
        """Test trade execution success"""
        mock_settings = Mock()
        mock_settings.database_url = "postgresql://test"
        mock_get_settings.return_value = mock_settings
        mock_connect.return_value = MagicMock()

        mock_result = Mock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        from backtest import Backtest

        backtest = Backtest(date(2025, 11, 1), date(2025, 11, 15))
        result = backtest.execute_trades(date(2025, 11, 15))

        assert result is True

    @patch('backtest.subprocess.run')
    @patch('backtest.psycopg2.connect')
    @patch('backtest.get_settings')
    def test_execute_trades_failure(self, mock_get_settings, mock_connect, mock_subprocess):
        """Test trade execution failure"""
        mock_settings = Mock()
        mock_settings.database_url = "postgresql://test"
        mock_get_settings.return_value = mock_settings
        mock_connect.return_value = MagicMock()

        mock_result = Mock()
        mock_result.returncode = 1
        mock_subprocess.return_value = mock_result

        from backtest import Backtest

        backtest = Backtest(date(2025, 11, 1), date(2025, 11, 15))
        result = backtest.execute_trades(date(2025, 11, 15))

        assert result is False


class TestCalculateDailyMetrics:
    """Test calculate_daily_metrics method"""

    @patch('backtest.psycopg2.connect')
    @patch('backtest.get_settings')
    def test_calculate_daily_metrics(self, mock_get_settings, mock_connect):
        """Test daily metrics calculation"""
        mock_settings = Mock()
        mock_settings.database_url = "postgresql://test"
        mock_get_settings.return_value = mock_settings

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Mock portfolio positions
        mock_cursor.fetchall.side_effect = [
            # Portfolio query
            [
                {'symbol': 'SPY', 'quantity': 1.0, 'avg_cost': 575.0},
                {'symbol': 'QQQ', 'quantity': 0.5, 'avg_cost': 495.0}
            ],
            # Prices query
            [
                {'symbol': 'SPY', 'close_price': 580.0},
                {'symbol': 'QQQ', 'close_price': 500.0}
            ]
        ]

        # Mock other queries
        mock_cursor.fetchone.side_effect = [
            {'total_injected': 1000.0},  # BUY trades total
            {'total_proceeds': 0.0},      # SELL trades total
            None  # Previous day metrics
        ]

        from backtest import Backtest

        backtest = Backtest(date(2025, 11, 1), date(2025, 11, 15))
        backtest.start_date = date(2025, 11, 1)

        metrics = backtest.calculate_daily_metrics(date(2025, 11, 15))

        assert 'date' in metrics
        assert 'portfolio_value' in metrics
        assert 'cash_balance' in metrics
        assert 'total_value' in metrics
        assert 'daily_return' in metrics
        assert 'cumulative_return' in metrics


class TestSaveDailyMetrics:
    """Test save_daily_metrics method"""

    @patch('backtest.psycopg2.connect')
    @patch('backtest.get_settings')
    def test_save_daily_metrics(self, mock_get_settings, mock_connect):
        """Test saving daily metrics"""
        mock_settings = Mock()
        mock_settings.database_url = "postgresql://test"
        mock_get_settings.return_value = mock_settings

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        from backtest import Backtest

        backtest = Backtest(date(2025, 11, 1), date(2025, 11, 15))

        metrics = {
            'date': date(2025, 11, 15),
            'portfolio_value': Decimal('1000.0'),
            'cash_balance': Decimal('100.0'),
            'total_value': Decimal('1100.0'),
            'daily_return': Decimal('0.5'),
            'cumulative_return': Decimal('1.5')
        }

        backtest.save_daily_metrics(metrics)

        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called_once()


class TestGenerateReport:
    """Test generate_report method"""

    @patch('backtest.os.makedirs')
    @patch('backtest.open', new_callable=mock_open)
    @patch('backtest.psycopg2.connect')
    @patch('backtest.get_settings')
    def test_generate_report(self, mock_get_settings, mock_connect, mock_file, mock_makedirs):
        """Test report generation"""
        mock_settings = Mock()
        mock_settings.database_url = "postgresql://test"
        mock_get_settings.return_value = mock_settings

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Mock performance metrics
        mock_cursor.fetchall.side_effect = [
            # Performance metrics
            [
                {
                    'date': date(2025, 11, 1),
                    'portfolio_value': 1000.0,
                    'total_value': 1000.0,
                    'daily_return': 0.0,
                    'cumulative_return': 0.0
                },
                {
                    'date': date(2025, 11, 4),
                    'portfolio_value': 1010.0,
                    'total_value': 1010.0,
                    'daily_return': 1.0,
                    'cumulative_return': 1.0
                }
            ],
            # Portfolio positions
            []
        ]

        mock_cursor.fetchone.side_effect = [
            {'total_injected': 1000.0},  # Total injected
            {'open_price': 580.0},        # SPY open
            {'close_price': 581.0},       # SPY close
            {'open_price': 500.0},        # QQQ open
            {'close_price': 501.0},       # QQQ close
            {'open_price': 420.0},        # DIA open
            {'close_price': 421.0},       # DIA close
        ]

        from backtest import Backtest

        backtest = Backtest(date(2025, 11, 1), date(2025, 11, 4))
        backtest.trading_days = [date(2025, 11, 1), date(2025, 11, 4)]

        backtest.generate_report()

        mock_file.assert_called()


class TestMainFunction:
    """Test main entry point"""

    @patch('backtest.argparse.ArgumentParser')
    @patch('backtest.Backtest')
    def test_main_success(self, mock_backtest_class, mock_parser):
        """Test main function with valid arguments"""
        mock_args = Mock()
        mock_args.start_date = "2025-11-01"
        mock_args.end_date = "2025-11-15"
        mock_parser.return_value.parse_args.return_value = mock_args

        mock_backtest = Mock()
        mock_backtest_class.return_value = mock_backtest

        from backtest import main

        result = main()

        assert result == 0
        mock_backtest.run.assert_called_once()
        mock_backtest.close.assert_called_once()

    @patch('backtest.argparse.ArgumentParser')
    def test_main_invalid_date_order(self, mock_parser):
        """Test main function with invalid date order"""
        mock_args = Mock()
        mock_args.start_date = "2025-11-15"
        mock_args.end_date = "2025-11-01"
        mock_parser.return_value.parse_args.return_value = mock_args

        from backtest import main

        result = main()

        assert result == 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
