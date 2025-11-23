"""Tests for train_config_locally.py"""
import sys
from pathlib import Path
from datetime import date, timedelta
from unittest.mock import MagicMock, patch
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.train_config_locally import run_continuous_backtest_with_tuning


def test_variable_naming_consistency():
    """Test that all variable names are consistent (no NameErrors)"""
    # This test validates the script can at least be parsed and has consistent variable names

    with patch('scripts.train_config_locally.psycopg2.connect') as mock_connect, \
         patch('scripts.train_config_locally.subprocess.run') as mock_run, \
         patch('scripts.train_config_locally.create_initial_config'):

        # Mock database cursor
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        # Mock database results
        oldest_date = date(2015, 11, 25)
        newest_date = date(2025, 11, 21)

        # First call: get date range
        mock_cursor.fetchone.side_effect = [
            (oldest_date, newest_date, 2500),  # MIN, MAX, COUNT from price_history
            (date(2016, 11, 1), date(2016, 11, 30)),  # month dates
            (10,),  # metrics count
        ]

        # Mock subprocess to succeed immediately
        mock_run.return_value.returncode = 0

        try:
            # This should not raise NameError
            result = run_continuous_backtest_with_tuning()
            # Should return (trading_start, trading_end)
            assert result is not None
            assert len(result) == 2

            # Verify trading_start is 365 days after oldest_date
            trading_start, trading_end = result
            expected_start = oldest_date + timedelta(days=365)
            assert trading_start == expected_start
            assert trading_end == newest_date

        except NameError as e:
            pytest.fail(f"NameError in script: {e}")


def test_config_created_with_oldest_date():
    """Test that config is created with oldest_date, not trading_start"""

    with patch('scripts.train_config_locally.psycopg2.connect') as mock_connect, \
         patch('scripts.train_config_locally.subprocess.run') as mock_run, \
         patch('scripts.train_config_locally.create_initial_config') as mock_create_config:

        # Mock database
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        oldest_date = date(2015, 11, 25)
        newest_date = date(2025, 11, 21)

        mock_cursor.fetchone.side_effect = [
            (oldest_date, newest_date, 2500),
            (date(2016, 11, 1), date(2016, 11, 30)),
            (10,),
        ]

        mock_run.return_value.returncode = 0

        # Run the function
        run_continuous_backtest_with_tuning()

        # Verify create_initial_config was called with oldest_date
        mock_create_config.assert_called_once_with(oldest_date)


def test_trading_starts_365_days_after_min():
    """Test that trading starts 365 days after min(date) for sufficient historical data"""

    with patch('scripts.train_config_locally.psycopg2.connect') as mock_connect, \
         patch('scripts.train_config_locally.subprocess.run') as mock_run, \
         patch('scripts.train_config_locally.create_initial_config'):

        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        oldest_date = date(2015, 11, 25)
        newest_date = date(2025, 11, 21)
        expected_trading_start = oldest_date + timedelta(days=365)

        mock_cursor.fetchone.side_effect = [
            (oldest_date, newest_date, 2500),
            (date(2016, 11, 1), date(2016, 11, 30)),
            (10,),
        ]

        mock_run.return_value.returncode = 0

        trading_start, trading_end = run_continuous_backtest_with_tuning()

        assert trading_start == expected_trading_start
        assert trading_end == newest_date


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
