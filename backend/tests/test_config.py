"""
Unit tests for config.py
Tests Settings class and configuration loading functions
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import date
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestSettings:
    """Test Settings class"""

    @patch.dict(os.environ, {
        "DATABASE_URL": "postgresql://test:test@localhost:5432/testdb",
        "ALPHAVANTAGE_API_KEY": "TEST_API_KEY"
    }, clear=True)
    def test_settings_loads_required_fields(self):
        """Test that settings loads required environment variables"""
        # Clear the cache to force reload
        from config import get_settings
        get_settings.cache_clear()

        settings = get_settings()

        assert settings.database_url == "postgresql://test:test@localhost:5432/testdb"
        assert settings.alphavantage_api_key == "TEST_API_KEY"

    @patch.dict(os.environ, {
        "DATABASE_URL": "postgresql://test:test@localhost:5432/testdb",
        "ALPHAVANTAGE_API_KEY": "TEST_API_KEY"
    }, clear=True)
    def test_settings_default_values(self):
        """Test that settings has correct default values"""
        from config import get_settings
        get_settings.cache_clear()

        settings = get_settings()

        assert settings.api_title == "Capital Allocator API"
        assert settings.api_version == "1.0.0"
        assert settings.model_type == "momentum"
        assert settings.market_close_time == "16:30"
        assert settings.signal_generation_time == "06:00"

    @patch.dict(os.environ, {
        "DATABASE_URL": "postgresql://custom:custom@db:5432/prod",
        "ALPHAVANTAGE_API_KEY": "CUSTOM_KEY",
        "API_TITLE": "Custom API",
        "API_VERSION": "2.0.0",
        "MODEL_TYPE": "mean_reversion"
    }, clear=True)
    def test_settings_custom_values(self):
        """Test that settings respects custom environment values"""
        from config import get_settings
        get_settings.cache_clear()

        settings = get_settings()

        assert settings.database_url == "postgresql://custom:custom@db:5432/prod"
        assert settings.alphavantage_api_key == "CUSTOM_KEY"
        assert settings.api_title == "Custom API"
        assert settings.api_version == "2.0.0"
        assert settings.model_type == "mean_reversion"

    @patch.dict(os.environ, {
        "DATABASE_URL": "postgresql://test:test@localhost:5432/testdb",
        "ALPHAVANTAGE_API_KEY": "TEST_API_KEY"
    }, clear=True)
    def test_get_settings_is_cached(self):
        """Test that get_settings returns cached instance"""
        from config import get_settings
        get_settings.cache_clear()

        settings1 = get_settings()
        settings2 = get_settings()

        # Should be the same instance
        assert settings1 is settings2


class TestGetTradingConfig:
    """Test get_trading_config function"""

    @patch('config_loader.get_active_trading_config')
    def test_get_trading_config_no_date(self, mock_get_active):
        """Test getting trading config without date"""
        from config import get_trading_config
        from config_loader import TradingConfig

        mock_config = TradingConfig(
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
        mock_get_active.return_value = mock_config

        result = get_trading_config()

        mock_get_active.assert_called_once_with(None)
        assert result.daily_capital == 1000.0
        assert result.assets == ["SPY", "QQQ", "DIA"]

    @patch('config_loader.get_active_trading_config')
    def test_get_trading_config_with_date(self, mock_get_active):
        """Test getting trading config for specific date"""
        from config import get_trading_config
        from config_loader import TradingConfig

        mock_config = TradingConfig(
            id=2,
            start_date=date(2025, 10, 1),
            end_date=date(2025, 10, 31),
            daily_capital=900.0,
            assets=["SPY", "QQQ"],
            lookback_days=200,
            regime_bullish_threshold=0.25,
            regime_bearish_threshold=-0.25,
            risk_high_threshold=65.0,
            risk_medium_threshold=35.0,
            allocation_low_risk=0.75,
            allocation_medium_risk=0.45,
            allocation_high_risk=0.25,
            allocation_neutral=0.15,
            sell_percentage=0.6,
            momentum_weight=0.7,
            price_momentum_weight=0.3,
            max_drawdown_tolerance=12.0,
            min_sharpe_target=1.2
        )
        mock_get_active.return_value = mock_config

        target_date = date(2025, 10, 15)
        result = get_trading_config(target_date)

        mock_get_active.assert_called_once_with(target_date)
        assert result.id == 2
        assert result.daily_capital == 900.0
        assert result.assets == ["SPY", "QQQ"]

    @patch('config_loader.get_active_trading_config')
    def test_get_trading_config_propagates_error(self, mock_get_active):
        """Test that errors are propagated correctly"""
        from config import get_trading_config

        mock_get_active.side_effect = ValueError("No active configuration found")

        with pytest.raises(ValueError) as exc_info:
            get_trading_config()

        assert "No active configuration found" in str(exc_info.value)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
