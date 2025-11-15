"""
Unit tests for run_monthly_tuning.py
Tests the monthly strategy tuning orchestration script
"""
import pytest
from unittest.mock import Mock, patch, MagicMock, mock_open
from datetime import date
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestIsFirstTradingDayOfMonth:
    """Test is_first_trading_day_of_month function"""

    @patch('run_monthly_tuning.date')
    def test_first_day_weekday(self, mock_date):
        """Test first day of month on weekday"""
        mock_today = Mock()
        mock_today.day = 3
        mock_today.weekday.return_value = 0  # Monday
        mock_date.today.return_value = mock_today

        from run_monthly_tuning import is_first_trading_day_of_month

        result = is_first_trading_day_of_month()
        assert result is True

    @patch('run_monthly_tuning.date')
    def test_weekend_returns_false(self, mock_date):
        """Test weekend returns false"""
        mock_today = Mock()
        mock_today.day = 1
        mock_today.weekday.return_value = 5  # Saturday
        mock_date.today.return_value = mock_today

        from run_monthly_tuning import is_first_trading_day_of_month

        result = is_first_trading_day_of_month()
        assert result is False

    @patch('run_monthly_tuning.date')
    def test_after_third_returns_false(self, mock_date):
        """Test day after 3rd returns false"""
        mock_today = Mock()
        mock_today.day = 4
        mock_today.weekday.return_value = 0  # Monday
        mock_date.today.return_value = mock_today

        from run_monthly_tuning import is_first_trading_day_of_month

        result = is_first_trading_day_of_month()
        assert result is False


class TestRunTuning:
    """Test run_tuning function"""

    @patch('run_monthly_tuning.subprocess.run')
    def test_run_tuning_success(self, mock_subprocess):
        """Test successful tuning run"""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        from run_monthly_tuning import run_tuning

        result = run_tuning(3)

        assert result is True
        mock_subprocess.assert_called_once()

    @patch('run_monthly_tuning.subprocess.run')
    def test_run_tuning_failure(self, mock_subprocess):
        """Test tuning failure"""
        from subprocess import CalledProcessError
        mock_subprocess.side_effect = CalledProcessError(1, 'cmd')

        from run_monthly_tuning import run_tuning

        result = run_tuning(3)

        assert result is False

    @patch('run_monthly_tuning.subprocess.run')
    def test_run_tuning_exception(self, mock_subprocess):
        """Test tuning exception"""
        mock_subprocess.side_effect = Exception("Tuning error")

        from run_monthly_tuning import run_tuning

        result = run_tuning(3)

        assert result is False


class TestShowParameterDiff:
    """Test show_parameter_diff function"""

    @patch('builtins.open', mock_open(read_data='{"regime_bullish_threshold": 0.3}'))
    @patch('run_monthly_tuning.Path')
    def test_show_parameter_diff_exists(self, mock_path):
        """Test showing parameter diff when file exists"""
        mock_path_instance = MagicMock()
        mock_path.return_value = mock_path_instance
        mock_json_path = MagicMock()
        mock_json_path.exists.return_value = True
        mock_path_instance.parent.parent.__truediv__.return_value.__truediv__.return_value = mock_json_path

        from run_monthly_tuning import show_parameter_diff

        # Should not raise
        show_parameter_diff()

    @patch('run_monthly_tuning.Path')
    def test_show_parameter_diff_not_exists(self, mock_path):
        """Test showing parameter diff when file doesn't exist"""
        # Create a complete mock path chain
        mock_path_instance = MagicMock()
        mock_path.return_value = mock_path_instance

        # Create the path to the JSON file
        mock_json_path = MagicMock()
        mock_json_path.exists.return_value = False

        # Setup the path traversal: backend_dir.parent / 'data' / 'strategy-tuning' / 'tuned_parameters.json'
        mock_path_instance.parent.parent.__truediv__.return_value.__truediv__.return_value.__truediv__.return_value = mock_json_path

        from run_monthly_tuning import show_parameter_diff

        # Should not raise - just silently exit when file doesn't exist
        show_parameter_diff()


class TestMainFunction:
    """Test main function"""

    @patch('run_monthly_tuning.show_parameter_diff')
    @patch('run_monthly_tuning.run_tuning')
    @patch('run_monthly_tuning.is_first_trading_day_of_month')
    @patch('run_monthly_tuning.sys.argv', ['script', '--force'])
    def test_main_success_with_force(self, mock_is_first, mock_run_tuning, mock_show_diff):
        """Test successful main execution with force flag"""
        mock_is_first.return_value = False
        mock_run_tuning.return_value = True

        from run_monthly_tuning import main

        result = main()

        assert result == 0
        mock_run_tuning.assert_called_once_with(3)

    @patch('run_monthly_tuning.is_first_trading_day_of_month')
    @patch('run_monthly_tuning.sys.argv', ['script'])
    def test_main_not_first_trading_day(self, mock_is_first):
        """Test main when not first trading day"""
        mock_is_first.return_value = False

        from run_monthly_tuning import main

        result = main()

        assert result == 1

    @patch('run_monthly_tuning.show_parameter_diff')
    @patch('run_monthly_tuning.run_tuning')
    @patch('run_monthly_tuning.is_first_trading_day_of_month')
    @patch('run_monthly_tuning.sys.argv', ['script'])
    def test_main_on_first_trading_day(self, mock_is_first, mock_run_tuning, mock_show_diff):
        """Test main on first trading day"""
        mock_is_first.return_value = True
        mock_run_tuning.return_value = True

        from run_monthly_tuning import main

        result = main()

        assert result == 0

    @patch('run_monthly_tuning.run_tuning')
    @patch('run_monthly_tuning.sys.argv', ['script', '--force'])
    def test_main_tuning_failure(self, mock_run_tuning):
        """Test main when tuning fails"""
        mock_run_tuning.return_value = False

        from run_monthly_tuning import main

        result = main()

        assert result == 1

    @patch('run_monthly_tuning.show_parameter_diff')
    @patch('run_monthly_tuning.run_tuning')
    @patch('run_monthly_tuning.sys.argv', ['script', '--force', '--lookback-months', '6'])
    def test_main_custom_lookback(self, mock_run_tuning, mock_show_diff):
        """Test main with custom lookback"""
        mock_run_tuning.return_value = True

        from run_monthly_tuning import main

        main()

        mock_run_tuning.assert_called_once_with(6)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
