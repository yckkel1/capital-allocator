"""
Unit tests for analytics.py
Tests performance metrics calculation and reporting
"""
import pytest
from unittest.mock import Mock, patch, MagicMock, mock_open
from datetime import date, datetime, timedelta
from decimal import Decimal
import os
import sys
import math

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestAnalyticsInit:
    """Test Analytics class initialization"""

    @patch('analytics.psycopg2.connect')
    @patch('analytics.get_settings')
    def test_analytics_init(self, mock_get_settings, mock_connect):
        """Test Analytics initialization"""
        mock_settings = Mock()
        mock_settings.database_url = "postgresql://test:test@localhost:5432/testdb"
        mock_get_settings.return_value = mock_settings

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        from analytics import Analytics

        start = date(2025, 11, 1)
        end = date(2025, 11, 15)
        analytics = Analytics(start, end)

        assert analytics.start_date == start
        assert analytics.end_date == end
        mock_connect.assert_called_once()

    @patch('analytics.psycopg2.connect')
    @patch('analytics.get_settings')
    def test_analytics_close(self, mock_get_settings, mock_connect):
        """Test Analytics close method"""
        mock_settings = Mock()
        mock_settings.database_url = "postgresql://test:test@localhost:5432/testdb"
        mock_get_settings.return_value = mock_settings

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        from analytics import Analytics

        analytics = Analytics(date(2025, 11, 1), date(2025, 11, 15))
        analytics.close()

        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()


class TestCalculateSharpeRatio:
    """Test Sharpe ratio calculation"""

    @patch('analytics.psycopg2.connect')
    @patch('analytics.get_settings')
    def test_sharpe_ratio_calculation(self, mock_get_settings, mock_connect):
        """Test Sharpe ratio calculation with valid data"""
        mock_settings = Mock()
        mock_settings.database_url = "postgresql://test"
        mock_get_settings.return_value = mock_settings
        mock_connect.return_value = MagicMock()

        from analytics import Analytics

        analytics = Analytics(date(2025, 11, 1), date(2025, 11, 15))

        # Daily returns with mean ~0.1% and std ~0.5%
        daily_returns = [0.1, 0.15, -0.05, 0.2, 0.12, 0.08, -0.1, 0.18, 0.05, 0.1]

        sharpe = analytics.calculate_sharpe_ratio(daily_returns, len(daily_returns))

        # Should be a positive number
        assert sharpe > 0
        assert isinstance(sharpe, float)

    @patch('analytics.psycopg2.connect')
    @patch('analytics.get_settings')
    def test_sharpe_ratio_empty_returns(self, mock_get_settings, mock_connect):
        """Test Sharpe ratio with empty returns"""
        mock_settings = Mock()
        mock_settings.database_url = "postgresql://test"
        mock_get_settings.return_value = mock_settings
        mock_connect.return_value = MagicMock()

        from analytics import Analytics

        analytics = Analytics(date(2025, 11, 1), date(2025, 11, 15))

        sharpe = analytics.calculate_sharpe_ratio([], 0)

        assert sharpe == 0.0

    @patch('analytics.psycopg2.connect')
    @patch('analytics.get_settings')
    def test_sharpe_ratio_single_return(self, mock_get_settings, mock_connect):
        """Test Sharpe ratio with single return"""
        mock_settings = Mock()
        mock_settings.database_url = "postgresql://test"
        mock_get_settings.return_value = mock_settings
        mock_connect.return_value = MagicMock()

        from analytics import Analytics

        analytics = Analytics(date(2025, 11, 1), date(2025, 11, 15))

        sharpe = analytics.calculate_sharpe_ratio([0.1], 1)

        assert sharpe == 0.0

    @patch('analytics.psycopg2.connect')
    @patch('analytics.get_settings')
    def test_sharpe_ratio_zero_variance(self, mock_get_settings, mock_connect):
        """Test Sharpe ratio when returns have zero variance"""
        mock_settings = Mock()
        mock_settings.database_url = "postgresql://test"
        mock_get_settings.return_value = mock_settings
        mock_connect.return_value = MagicMock()

        from analytics import Analytics

        analytics = Analytics(date(2025, 11, 1), date(2025, 11, 15))

        # All returns are the same
        daily_returns = [0.1, 0.1, 0.1, 0.1, 0.1]

        sharpe = analytics.calculate_sharpe_ratio(daily_returns, len(daily_returns))

        assert sharpe == 0.0


class TestCalculateMaxDrawdown:
    """Test maximum drawdown calculation"""

    @patch('analytics.psycopg2.connect')
    @patch('analytics.get_settings')
    def test_max_drawdown_calculation(self, mock_get_settings, mock_connect):
        """Test max drawdown with declining values"""
        mock_settings = Mock()
        mock_settings.database_url = "postgresql://test"
        mock_get_settings.return_value = mock_settings
        mock_connect.return_value = MagicMock()

        from analytics import Analytics

        analytics = Analytics(date(2025, 11, 1), date(2025, 11, 15))

        # Simulate peak to trough
        performance_data = [
            {'date': date(2025, 11, 1), 'total_value': 10000},
            {'date': date(2025, 11, 2), 'total_value': 10500},  # Peak
            {'date': date(2025, 11, 3), 'total_value': 10200},
            {'date': date(2025, 11, 4), 'total_value': 9800},   # Trough
            {'date': date(2025, 11, 5), 'total_value': 10100},
        ]

        result = analytics.calculate_max_drawdown(performance_data)

        # Drawdown from 10500 to 9800 = 6.67%
        expected_dd = (10500 - 9800) / 10500 * 100
        assert abs(result['max_drawdown'] - expected_dd) < 0.1
        assert result['peak_date'] == date(2025, 11, 2)
        assert result['trough_date'] == date(2025, 11, 4)

    @patch('analytics.psycopg2.connect')
    @patch('analytics.get_settings')
    def test_max_drawdown_empty_data(self, mock_get_settings, mock_connect):
        """Test max drawdown with empty data"""
        mock_settings = Mock()
        mock_settings.database_url = "postgresql://test"
        mock_get_settings.return_value = mock_settings
        mock_connect.return_value = MagicMock()

        from analytics import Analytics

        analytics = Analytics(date(2025, 11, 1), date(2025, 11, 15))

        result = analytics.calculate_max_drawdown([])

        assert result['max_drawdown'] == 0
        assert result['peak_date'] is None
        assert result['trough_date'] is None

    @patch('analytics.psycopg2.connect')
    @patch('analytics.get_settings')
    def test_max_drawdown_no_decline(self, mock_get_settings, mock_connect):
        """Test max drawdown when values only increase"""
        mock_settings = Mock()
        mock_settings.database_url = "postgresql://test"
        mock_get_settings.return_value = mock_settings
        mock_connect.return_value = MagicMock()

        from analytics import Analytics

        analytics = Analytics(date(2025, 11, 1), date(2025, 11, 15))

        # Always increasing
        performance_data = [
            {'date': date(2025, 11, 1), 'total_value': 10000},
            {'date': date(2025, 11, 2), 'total_value': 10100},
            {'date': date(2025, 11, 3), 'total_value': 10200},
        ]

        result = analytics.calculate_max_drawdown(performance_data)

        assert result['max_drawdown'] == 0.0


class TestCalculateCalmarRatio:
    """Test Calmar ratio calculation"""

    @patch('analytics.psycopg2.connect')
    @patch('analytics.get_settings')
    def test_calmar_ratio_normal_case(self, mock_get_settings, mock_connect):
        """Test Calmar ratio calculation"""
        mock_settings = Mock()
        mock_settings.database_url = "postgresql://test"
        mock_get_settings.return_value = mock_settings
        mock_connect.return_value = MagicMock()

        from analytics import Analytics

        analytics = Analytics(date(2025, 11, 1), date(2025, 11, 15))

        total_return_pct = 20.0  # 20% return
        max_drawdown = 10.0      # 10% drawdown
        years = 1.0

        calmar = analytics.calculate_calmar_ratio(total_return_pct, max_drawdown, years)

        # 20% / 10% = 2.0
        assert calmar == 2.0

    @patch('analytics.psycopg2.connect')
    @patch('analytics.get_settings')
    def test_calmar_ratio_zero_drawdown(self, mock_get_settings, mock_connect):
        """Test Calmar ratio when drawdown is zero"""
        mock_settings = Mock()
        mock_settings.database_url = "postgresql://test"
        mock_get_settings.return_value = mock_settings
        mock_connect.return_value = MagicMock()

        from analytics import Analytics

        analytics = Analytics(date(2025, 11, 1), date(2025, 11, 15))

        calmar = analytics.calculate_calmar_ratio(10.0, 0.0, 1.0)

        assert math.isinf(calmar)

    @patch('analytics.psycopg2.connect')
    @patch('analytics.get_settings')
    def test_calmar_ratio_annualized(self, mock_get_settings, mock_connect):
        """Test Calmar ratio annualization"""
        mock_settings = Mock()
        mock_settings.database_url = "postgresql://test"
        mock_get_settings.return_value = mock_settings
        mock_connect.return_value = MagicMock()

        from analytics import Analytics

        analytics = Analytics(date(2025, 11, 1), date(2025, 11, 15))

        # 10% return over 0.5 years = 20% annualized
        calmar = analytics.calculate_calmar_ratio(10.0, 5.0, 0.5)

        # (10/0.5) / 5 = 4.0
        assert calmar == 4.0


class TestGetPerformanceData:
    """Test performance data retrieval"""

    @patch('analytics.psycopg2.connect')
    @patch('analytics.get_settings')
    def test_get_performance_data(self, mock_get_settings, mock_connect):
        """Test fetching performance data"""
        mock_settings = Mock()
        mock_settings.database_url = "postgresql://test"
        mock_get_settings.return_value = mock_settings

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.fetchall.return_value = [
            {'date': date(2025, 11, 1), 'total_value': 1000},
            {'date': date(2025, 11, 2), 'total_value': 1010},
        ]

        from analytics import Analytics

        analytics = Analytics(date(2025, 11, 1), date(2025, 11, 15))
        result = analytics.get_performance_data()

        assert len(result) == 2
        mock_cursor.execute.assert_called_once()


class TestGetTradingDays:
    """Test trading days retrieval"""

    @patch('analytics.psycopg2.connect')
    @patch('analytics.get_settings')
    def test_get_trading_days(self, mock_get_settings, mock_connect):
        """Test fetching trading days"""
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

        from analytics import Analytics

        analytics = Analytics(date(2025, 11, 1), date(2025, 11, 15))
        result = analytics.get_trading_days()

        assert len(result) == 3
        assert result[0] == date(2025, 11, 1)


class TestMainFunction:
    """Test main entry point"""

    @patch('analytics.argparse.ArgumentParser')
    @patch('analytics.Analytics')
    def test_main_success(self, mock_analytics_class, mock_parser):
        """Test main function with valid arguments"""
        mock_args = Mock()
        mock_args.start_date = "2025-11-01"
        mock_args.end_date = "2025-11-15"
        mock_parser.return_value.parse_args.return_value = mock_args

        mock_analytics = Mock()
        mock_analytics_class.return_value = mock_analytics

        from analytics import main

        result = main()

        assert result == 0
        mock_analytics.run.assert_called_once()
        mock_analytics.close.assert_called_once()

    @patch('analytics.argparse.ArgumentParser')
    def test_main_invalid_date_order(self, mock_parser):
        """Test main function with end date before start date"""
        mock_args = Mock()
        mock_args.start_date = "2025-11-15"
        mock_args.end_date = "2025-11-01"
        mock_parser.return_value.parse_args.return_value = mock_args

        from analytics import main

        result = main()

        assert result == 1  # Error exit code


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
