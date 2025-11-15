"""
Unit tests for config_loader.py
Tests configuration loading and version management with mocked database
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import date, timedelta
import json

# Import the modules to test
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config_loader import TradingConfig, ConfigLoader, get_active_trading_config


class TestTradingConfig:
    """Test TradingConfig dataclass"""

    def test_create_config_with_all_fields(self):
        """Test creating a config with all required fields"""
        config = TradingConfig(
            daily_capital=1000.0,
            assets=["SPY", "QQQ", "DIA"],
            lookback_days=252,
            regime_bullish_threshold=0.3,
            regime_bearish_threshold=-0.3,
            risk_high_threshold=70.0,
            risk_medium_threshold=40.0,
            allocation_low_risk=0.8,
            allocation_medium_risk=0.5,
            allocation_high_risk=0.3,
            allocation_neutral=0.2,
            sell_percentage=0.7,
            momentum_weight=0.6,
            price_momentum_weight=0.4,
            max_drawdown_tolerance=15.0,
            min_sharpe_target=1.0
        )

        assert config.daily_capital == 1000.0
        assert config.assets == ["SPY", "QQQ", "DIA"]
        assert config.lookback_days == 252
        assert config.regime_bullish_threshold == 0.3
        assert config.regime_bearish_threshold == -0.3
        assert config.allocation_low_risk == 0.8

    def test_to_dict(self):
        """Test converting config to dictionary"""
        config = TradingConfig(
            daily_capital=1500.0,
            assets=["SPY", "QQQ"],
            lookback_days=200,
            regime_bullish_threshold=0.35,
            regime_bearish_threshold=-0.25,
            risk_high_threshold=65.0,
            risk_medium_threshold=35.0,
            allocation_low_risk=0.9,
            allocation_medium_risk=0.6,
            allocation_high_risk=0.25,
            allocation_neutral=0.15,
            sell_percentage=0.8,
            momentum_weight=0.7,
            price_momentum_weight=0.3,
            max_drawdown_tolerance=12.0,
            min_sharpe_target=1.2
        )

        result = config.to_dict()

        assert isinstance(result, dict)
        assert result['daily_capital'] == 1500.0
        assert result['assets'] == ["SPY", "QQQ"]
        assert result['lookback_days'] == 200
        assert result['regime_bullish_threshold'] == 0.35
        assert result['min_sharpe_target'] == 1.2

    def test_from_db_row(self):
        """Test creating config from database row"""
        mock_row = {
            'id': 1,
            'start_date': date(2025, 11, 1),
            'end_date': None,
            'daily_capital': 1000.0,
            'assets': ["SPY", "QQQ", "DIA"],
            'lookback_days': 252,
            'regime_bullish_threshold': 0.3,
            'regime_bearish_threshold': -0.3,
            'risk_high_threshold': 70.0,
            'risk_medium_threshold': 40.0,
            'allocation_low_risk': 0.8,
            'allocation_medium_risk': 0.5,
            'allocation_high_risk': 0.3,
            'allocation_neutral': 0.2,
            'sell_percentage': 0.7,
            'momentum_weight': 0.6,
            'price_momentum_weight': 0.4,
            'max_drawdown_tolerance': 15.0,
            'min_sharpe_target': 1.0,
            'created_by': 'test',
            'notes': 'test notes'
        }

        config = TradingConfig.from_db_row(mock_row)

        assert config.id == 1
        assert config.start_date == date(2025, 11, 1)
        assert config.end_date is None
        assert config.daily_capital == 1000.0
        assert config.assets == ["SPY", "QQQ", "DIA"]
        assert config.created_by == 'test'
        assert config.notes == 'test notes'

    def test_to_dict_serializes_dates(self):
        """Test that dates are properly serialized in to_dict"""
        config = TradingConfig(
            id=1,
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30),
            daily_capital=1000.0,
            assets=["SPY"],
            lookback_days=252,
            regime_bullish_threshold=0.3,
            regime_bearish_threshold=-0.3,
            risk_high_threshold=70.0,
            risk_medium_threshold=40.0,
            allocation_low_risk=0.8,
            allocation_medium_risk=0.5,
            allocation_high_risk=0.3,
            allocation_neutral=0.2,
            sell_percentage=0.7,
            momentum_weight=0.6,
            price_momentum_weight=0.4,
            max_drawdown_tolerance=15.0,
            min_sharpe_target=1.0
        )

        result = config.to_dict()

        # Should be serializable to JSON with default=str
        json_str = json.dumps(result, default=str)
        assert '2025-11-01' in json_str
        assert '2025-11-30' in json_str


class TestConfigLoader:
    """Test ConfigLoader database operations"""

    @patch('config_loader.psycopg2.connect')
    def test_get_active_config_success(self, mock_connect):
        """Test loading active configuration from database"""
        # Setup mock
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Mock database return
        mock_cursor.fetchone.return_value = {
            'id': 1,
            'start_date': date(2025, 11, 1),
            'end_date': None,
            'daily_capital': 1000.0,
            'assets': ["SPY", "QQQ", "DIA"],
            'lookback_days': 252,
            'regime_bullish_threshold': 0.3,
            'regime_bearish_threshold': -0.3,
            'risk_high_threshold': 70.0,
            'risk_medium_threshold': 40.0,
            'allocation_low_risk': 0.8,
            'allocation_medium_risk': 0.5,
            'allocation_high_risk': 0.3,
            'allocation_neutral': 0.2,
            'sell_percentage': 0.7,
            'momentum_weight': 0.6,
            'price_momentum_weight': 0.4,
            'max_drawdown_tolerance': 15.0,
            'min_sharpe_target': 1.0,
            'created_by': 'migration',
            'notes': None
        }

        loader = ConfigLoader("postgresql://test")
        config = loader.get_active_config()

        # Verify
        assert config.id == 1
        assert config.daily_capital == 1000.0
        assert config.assets == ["SPY", "QQQ", "DIA"]

        # Check query was called correctly
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args[0]
        assert 'SELECT * FROM trading_config' in call_args[0]
        assert 'WHERE start_date <=' in call_args[0]

    @patch('config_loader.psycopg2.connect')
    def test_get_active_config_no_result(self, mock_connect):
        """Test loading config when no active config exists"""
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None

        loader = ConfigLoader("postgresql://test")

        with pytest.raises(ValueError) as exc_info:
            loader.get_active_config()

        assert "No active trading configuration found" in str(exc_info.value)

    @patch('config_loader.psycopg2.connect')
    def test_get_active_config_for_specific_date(self, mock_connect):
        """Test loading config for a specific historical date"""
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.fetchone.return_value = {
            'id': 2,
            'start_date': date(2025, 10, 1),
            'end_date': date(2025, 10, 31),
            'daily_capital': 900.0,
            'assets': ["SPY", "QQQ"],
            'lookback_days': 252,
            'regime_bullish_threshold': 0.25,
            'regime_bearish_threshold': -0.25,
            'risk_high_threshold': 70.0,
            'risk_medium_threshold': 40.0,
            'allocation_low_risk': 0.75,
            'allocation_medium_risk': 0.45,
            'allocation_high_risk': 0.25,
            'allocation_neutral': 0.2,
            'sell_percentage': 0.7,
            'momentum_weight': 0.6,
            'price_momentum_weight': 0.4,
            'max_drawdown_tolerance': 15.0,
            'min_sharpe_target': 1.0,
            'created_by': 'test',
            'notes': None
        }

        loader = ConfigLoader("postgresql://test")
        config = loader.get_active_config(date(2025, 10, 15))

        assert config.id == 2
        assert config.daily_capital == 900.0
        assert config.assets == ["SPY", "QQQ"]

        # Verify date was passed to query
        call_args = mock_cursor.execute.call_args[0]
        assert date(2025, 10, 15) in call_args[1]

    @patch('config_loader.psycopg2.connect')
    def test_create_new_version_basic(self, mock_connect):
        """Test creating a new config version"""
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Mock returning new ID
        mock_cursor.fetchone.return_value = {'id': 3}

        new_config = TradingConfig(
            daily_capital=1100.0,
            assets=["SPY", "QQQ", "DIA"],
            lookback_days=252,
            regime_bullish_threshold=0.35,
            regime_bearish_threshold=-0.3,
            risk_high_threshold=70.0,
            risk_medium_threshold=40.0,
            allocation_low_risk=0.85,
            allocation_medium_risk=0.55,
            allocation_high_risk=0.3,
            allocation_neutral=0.2,
            sell_percentage=0.7,
            momentum_weight=0.6,
            price_momentum_weight=0.4,
            max_drawdown_tolerance=15.0,
            min_sharpe_target=1.0
        )

        loader = ConfigLoader("postgresql://test")
        new_id = loader.create_new_version(
            new_config,
            start_date=date(2025, 12, 1),
            created_by='strategy_tuning',
            notes='Monthly tuning'
        )

        assert new_id == 3

        # Verify UPDATE was called to close previous config
        calls = mock_cursor.execute.call_args_list
        assert len(calls) == 2  # UPDATE + INSERT

        # First call: UPDATE to close previous
        update_call = calls[0][0]
        assert 'UPDATE trading_config' in update_call[0]
        assert 'SET end_date' in update_call[0]

        # Second call: INSERT new config
        insert_call = calls[1][0]
        assert 'INSERT INTO trading_config' in insert_call[0]

    @patch('config_loader.psycopg2.connect')
    def test_create_new_version_assets_json_conversion(self, mock_connect):
        """Test that assets list is wrapped in Json() for JSONB column"""
        from psycopg2.extras import Json as PsycopgJson

        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = {'id': 5}

        new_config = TradingConfig(
            daily_capital=1000.0,
            assets=["SPY", "QQQ", "DIA"],
            lookback_days=252,
            regime_bullish_threshold=0.3,
            regime_bearish_threshold=-0.3,
            risk_high_threshold=70.0,
            risk_medium_threshold=40.0,
            allocation_low_risk=0.8,
            allocation_medium_risk=0.5,
            allocation_high_risk=0.3,
            allocation_neutral=0.2,
            sell_percentage=0.7,
            momentum_weight=0.6,
            price_momentum_weight=0.4,
            max_drawdown_tolerance=15.0,
            min_sharpe_target=1.0
        )

        loader = ConfigLoader("postgresql://test")
        loader.create_new_version(
            new_config,
            start_date=date(2025, 12, 1),
            close_previous=False
        )

        # Get the INSERT call parameters
        insert_call = mock_cursor.execute.call_args_list[0][0]
        insert_params = insert_call[1]

        # The third parameter (index 2) should be the assets wrapped in Json
        # Parameters: start_date, daily_capital, assets, lookback_days, ...
        assets_param = insert_params[2]

        # Verify it's wrapped in Json
        assert isinstance(assets_param, PsycopgJson), f"Assets should be wrapped in Json(), got {type(assets_param)}"
        # Verify the underlying value
        assert assets_param.adapted == ["SPY", "QQQ", "DIA"]

    @patch('config_loader.psycopg2.connect')
    def test_create_new_version_without_closing_previous(self, mock_connect):
        """Test creating new version without closing previous"""
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = {'id': 4}

        new_config = TradingConfig(
            daily_capital=1000.0,
            assets=["SPY"],
            lookback_days=252,
            regime_bullish_threshold=0.3,
            regime_bearish_threshold=-0.3,
            risk_high_threshold=70.0,
            risk_medium_threshold=40.0,
            allocation_low_risk=0.8,
            allocation_medium_risk=0.5,
            allocation_high_risk=0.3,
            allocation_neutral=0.2,
            sell_percentage=0.7,
            momentum_weight=0.6,
            price_momentum_weight=0.4,
            max_drawdown_tolerance=15.0,
            min_sharpe_target=1.0
        )

        loader = ConfigLoader("postgresql://test")
        new_id = loader.create_new_version(
            new_config,
            start_date=date(2025, 12, 1),
            close_previous=False
        )

        assert new_id == 4

        # Only INSERT should be called, not UPDATE
        calls = mock_cursor.execute.call_args_list
        assert len(calls) == 1  # Only INSERT
        assert 'INSERT INTO trading_config' in calls[0][0][0]

    @patch('config_loader.psycopg2.connect')
    def test_create_new_version_rollback_on_error(self, mock_connect):
        """Test that transaction is rolled back on error"""
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Make INSERT raise an error
        mock_cursor.execute.side_effect = [None, Exception("DB Error")]

        new_config = TradingConfig(
            daily_capital=1000.0,
            assets=["SPY"],
            lookback_days=252,
            regime_bullish_threshold=0.3,
            regime_bearish_threshold=-0.3,
            risk_high_threshold=70.0,
            risk_medium_threshold=40.0,
            allocation_low_risk=0.8,
            allocation_medium_risk=0.5,
            allocation_high_risk=0.3,
            allocation_neutral=0.2,
            sell_percentage=0.7,
            momentum_weight=0.6,
            price_momentum_weight=0.4,
            max_drawdown_tolerance=15.0,
            min_sharpe_target=1.0
        )

        loader = ConfigLoader("postgresql://test")

        with pytest.raises(Exception):
            loader.create_new_version(new_config, start_date=date(2025, 12, 1))

        # Verify rollback was called
        mock_conn.rollback.assert_called_once()


class TestGetActiveTradingConfig:
    """Test the convenience function"""

    @patch('config_loader.get_config_loader')
    def test_convenience_function_uses_cached_loader(self, mock_get_loader):
        """Test that convenience function uses cached loader"""
        mock_loader = MagicMock()
        mock_get_loader.return_value = mock_loader

        mock_loader.get_active_config.return_value = TradingConfig(
            daily_capital=1000.0,
            assets=["SPY"],
            lookback_days=252,
            regime_bullish_threshold=0.3,
            regime_bearish_threshold=-0.3,
            risk_high_threshold=70.0,
            risk_medium_threshold=40.0,
            allocation_low_risk=0.8,
            allocation_medium_risk=0.5,
            allocation_high_risk=0.3,
            allocation_neutral=0.2,
            sell_percentage=0.7,
            momentum_weight=0.6,
            price_momentum_weight=0.4,
            max_drawdown_tolerance=15.0,
            min_sharpe_target=1.0
        )

        config = get_active_trading_config()

        mock_get_loader.assert_called_once()
        mock_loader.get_active_config.assert_called_once_with(None)
        assert config.daily_capital == 1000.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
