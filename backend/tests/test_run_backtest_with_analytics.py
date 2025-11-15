"""
Unit tests for run_backtest_with_analytics.py
Tests the main backtest orchestration script
"""
import pytest
from unittest.mock import Mock, patch, MagicMock, call
from datetime import date
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestValidateDate:
    """Test validate_date function"""

    def test_valid_date(self):
        """Test valid date parsing"""
        from run_backtest_with_analytics import validate_date

        result = validate_date("2025-11-15")
        assert result == date(2025, 11, 15)

    def test_invalid_date_format(self):
        """Test invalid date format raises error"""
        from run_backtest_with_analytics import validate_date

        with pytest.raises(ValueError) as exc_info:
            validate_date("11-15-2025")

        assert "Invalid date format" in str(exc_info.value)

    def test_invalid_date_string(self):
        """Test invalid date string raises error"""
        from run_backtest_with_analytics import validate_date

        with pytest.raises(ValueError):
            validate_date("not-a-date")


class TestRunCommand:
    """Test run_command function"""

    @patch('run_backtest_with_analytics.subprocess.run')
    def test_run_command_success(self, mock_subprocess):
        """Test successful command execution"""
        mock_subprocess.return_value = Mock(returncode=0)

        from run_backtest_with_analytics import run_command

        result = run_command(['echo', 'test'], 'Test command')

        assert result is True
        mock_subprocess.assert_called_once()

    @patch('run_backtest_with_analytics.subprocess.run')
    def test_run_command_failure(self, mock_subprocess):
        """Test command execution failure"""
        from subprocess import CalledProcessError
        mock_subprocess.side_effect = CalledProcessError(1, 'cmd')

        from run_backtest_with_analytics import run_command

        result = run_command(['false'], 'Test command')

        assert result is False

    @patch('run_backtest_with_analytics.subprocess.run')
    def test_run_command_exception(self, mock_subprocess):
        """Test command execution exception"""
        mock_subprocess.side_effect = Exception("Command error")

        from run_backtest_with_analytics import run_command

        result = run_command(['invalid'], 'Test command')

        assert result is False


class TestMainFunction:
    """Test main function"""

    @patch('run_backtest_with_analytics.run_command')
    @patch('run_backtest_with_analytics.sys.argv', ['script', '--start-date', '2025-11-01', '--end-date', '2025-11-15'])
    def test_main_success(self, mock_run_command):
        """Test successful main execution"""
        mock_run_command.return_value = True

        from run_backtest_with_analytics import main

        result = main()

        assert result == 0
        # Should run backtest and analytics
        assert mock_run_command.call_count >= 1

    @patch('run_backtest_with_analytics.sys.argv', ['script', '--start-date', '2025-11-15', '--end-date', '2025-11-01'])
    def test_main_invalid_date_order(self):
        """Test main with end date before start date"""
        from run_backtest_with_analytics import main

        result = main()

        assert result == 1

    @patch('run_backtest_with_analytics.run_command')
    @patch('run_backtest_with_analytics.sys.argv', ['script', '--start-date', '2025-11-01', '--end-date', '2025-11-15', '--skip-analytics'])
    def test_main_skip_analytics(self, mock_run_command):
        """Test main with skip analytics flag"""
        mock_run_command.return_value = True

        from run_backtest_with_analytics import main

        result = main()

        assert result == 0

    @patch('run_backtest_with_analytics.run_command')
    @patch('run_backtest_with_analytics.sys.argv', ['script', '--start-date', '2025-11-01', '--end-date', '2025-11-15', '--skip-backtest'])
    def test_main_skip_backtest(self, mock_run_command):
        """Test main with skip backtest flag"""
        mock_run_command.return_value = True

        from run_backtest_with_analytics import main

        result = main()

        assert result == 0

    @patch('run_backtest_with_analytics.run_command')
    @patch('run_backtest_with_analytics.sys.argv', ['script', '--start-date', '2025-11-01', '--end-date', '2025-11-15'])
    def test_main_backtest_failure(self, mock_run_command):
        """Test main when backtest fails"""
        mock_run_command.return_value = False

        from run_backtest_with_analytics import main

        result = main()

        assert result == 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
