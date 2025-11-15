"""
Unit tests for models.py
Tests SQLAlchemy ORM models
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import date, datetime, timezone
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestActionType:
    """Test ActionType enum"""

    def test_action_type_values(self):
        """Test that ActionType has correct values"""
        from models import ActionType

        assert ActionType.BUY == "BUY"
        assert ActionType.SELL == "SELL"
        assert ActionType.HOLD == "HOLD"

    def test_action_type_is_str(self):
        """Test that ActionType values are strings"""
        from models import ActionType

        assert isinstance(ActionType.BUY, str)
        assert isinstance(ActionType.SELL, str)
        assert isinstance(ActionType.HOLD, str)

    def test_action_type_membership(self):
        """Test ActionType membership"""
        from models import ActionType

        assert "BUY" in [a.value for a in ActionType]
        assert "SELL" in [a.value for a in ActionType]
        assert "HOLD" in [a.value for a in ActionType]


class TestPriceHistory:
    """Test PriceHistory model"""

    def test_price_history_columns_exist(self):
        """Test that PriceHistory has all required columns"""
        from models import PriceHistory

        # Check column names
        columns = [c.name for c in PriceHistory.__table__.columns]

        assert "id" in columns
        assert "date" in columns
        assert "symbol" in columns
        assert "open_price" in columns
        assert "high_price" in columns
        assert "low_price" in columns
        assert "close_price" in columns
        assert "volume" in columns
        assert "created_at" in columns

    def test_price_history_table_name(self):
        """Test PriceHistory table name"""
        from models import PriceHistory

        assert PriceHistory.__tablename__ == "price_history"

    def test_price_history_primary_key(self):
        """Test PriceHistory has correct primary key"""
        from models import PriceHistory

        pk_columns = [c.name for c in PriceHistory.__table__.primary_key.columns]
        assert "id" in pk_columns

    def test_price_history_indexes(self):
        """Test PriceHistory has proper indexes"""
        from models import PriceHistory

        # Check that date and symbol columns are indexed
        date_col = PriceHistory.__table__.columns['date']
        symbol_col = PriceHistory.__table__.columns['symbol']

        assert date_col.index is True
        assert symbol_col.index is True


class TestDailySignal:
    """Test DailySignal model"""

    def test_daily_signal_columns_exist(self):
        """Test that DailySignal has all required columns"""
        from models import DailySignal

        columns = [c.name for c in DailySignal.__table__.columns]

        assert "id" in columns
        assert "trade_date" in columns
        assert "generated_at" in columns
        assert "allocations" in columns
        assert "model_type" in columns
        assert "confidence_score" in columns
        assert "features_used" in columns

    def test_daily_signal_table_name(self):
        """Test DailySignal table name"""
        from models import DailySignal

        assert DailySignal.__tablename__ == "daily_signals"

    def test_daily_signal_unique_constraint(self):
        """Test that trade_date is unique"""
        from models import DailySignal

        trade_date_col = DailySignal.__table__.columns['trade_date']
        assert trade_date_col.unique is True

    def test_daily_signal_json_columns(self):
        """Test that JSON columns are defined correctly"""
        from models import DailySignal
        from sqlalchemy import JSON

        allocations_col = DailySignal.__table__.columns['allocations']
        features_col = DailySignal.__table__.columns['features_used']

        assert isinstance(allocations_col.type, JSON)
        assert isinstance(features_col.type, JSON)


class TestTrade:
    """Test Trade model"""

    def test_trade_columns_exist(self):
        """Test that Trade has all required columns"""
        from models import Trade

        columns = [c.name for c in Trade.__table__.columns]

        assert "id" in columns
        assert "trade_date" in columns
        assert "executed_at" in columns
        assert "symbol" in columns
        assert "action" in columns
        assert "quantity" in columns
        assert "price" in columns
        assert "amount" in columns
        assert "signal_id" in columns

    def test_trade_table_name(self):
        """Test Trade table name"""
        from models import Trade

        assert Trade.__tablename__ == "trades"

    def test_trade_action_enum(self):
        """Test that action column uses ActionType enum"""
        from models import Trade
        from sqlalchemy import Enum

        action_col = Trade.__table__.columns['action']
        # The column type should be an Enum
        assert "Enum" in str(type(action_col.type))


class TestPortfolio:
    """Test Portfolio model"""

    def test_portfolio_columns_exist(self):
        """Test that Portfolio has all required columns"""
        from models import Portfolio

        columns = [c.name for c in Portfolio.__table__.columns]

        assert "id" in columns
        assert "symbol" in columns
        assert "quantity" in columns
        assert "avg_cost" in columns
        assert "last_updated" in columns

    def test_portfolio_table_name(self):
        """Test Portfolio table name"""
        from models import Portfolio

        assert Portfolio.__tablename__ == "portfolio"

    def test_portfolio_symbol_unique(self):
        """Test that symbol is unique"""
        from models import Portfolio

        symbol_col = Portfolio.__table__.columns['symbol']
        assert symbol_col.unique is True

    def test_portfolio_defaults(self):
        """Test Portfolio column defaults"""
        from models import Portfolio

        quantity_col = Portfolio.__table__.columns['quantity']
        avg_cost_col = Portfolio.__table__.columns['avg_cost']

        assert quantity_col.default.arg == 0
        assert avg_cost_col.default.arg == 0


class TestPerformanceMetrics:
    """Test PerformanceMetrics model"""

    def test_performance_metrics_columns_exist(self):
        """Test that PerformanceMetrics has all required columns"""
        from models import PerformanceMetrics

        columns = [c.name for c in PerformanceMetrics.__table__.columns]

        assert "id" in columns
        assert "date" in columns
        assert "portfolio_value" in columns
        assert "cash_balance" in columns
        assert "total_value" in columns
        assert "daily_return" in columns
        assert "cumulative_return" in columns
        assert "sharpe_ratio" in columns
        assert "max_drawdown" in columns
        assert "created_at" in columns

    def test_performance_metrics_table_name(self):
        """Test PerformanceMetrics table name"""
        from models import PerformanceMetrics

        assert PerformanceMetrics.__tablename__ == "performance_metrics"

    def test_performance_metrics_date_unique(self):
        """Test that date is unique"""
        from models import PerformanceMetrics

        date_col = PerformanceMetrics.__table__.columns['date']
        assert date_col.unique is True


class TestTradingConfig:
    """Test TradingConfig model"""

    def test_trading_config_columns_exist(self):
        """Test that TradingConfig has all required columns"""
        from models import TradingConfig

        columns = [c.name for c in TradingConfig.__table__.columns]

        assert "id" in columns
        assert "start_date" in columns
        assert "end_date" in columns
        assert "daily_capital" in columns
        assert "assets" in columns
        assert "lookback_days" in columns
        assert "regime_bullish_threshold" in columns
        assert "regime_bearish_threshold" in columns
        assert "risk_high_threshold" in columns
        assert "risk_medium_threshold" in columns
        assert "allocation_low_risk" in columns
        assert "allocation_medium_risk" in columns
        assert "allocation_high_risk" in columns
        assert "allocation_neutral" in columns
        assert "sell_percentage" in columns
        assert "momentum_weight" in columns
        assert "price_momentum_weight" in columns
        assert "max_drawdown_tolerance" in columns
        assert "min_sharpe_target" in columns
        assert "created_at" in columns
        assert "created_by" in columns
        assert "notes" in columns

    def test_trading_config_table_name(self):
        """Test TradingConfig table name"""
        from models import TradingConfig

        assert TradingConfig.__tablename__ == "trading_config"

    def test_trading_config_defaults(self):
        """Test TradingConfig default values"""
        from models import TradingConfig

        daily_capital_col = TradingConfig.__table__.columns['daily_capital']
        lookback_days_col = TradingConfig.__table__.columns['lookback_days']

        assert daily_capital_col.default.arg == 1000.0
        assert lookback_days_col.default.arg == 252

    def test_trading_config_json_column(self):
        """Test that assets is a JSON column"""
        from models import TradingConfig
        from sqlalchemy import JSON

        assets_col = TradingConfig.__table__.columns['assets']
        assert isinstance(assets_col.type, JSON)

    def test_trading_config_nullable_end_date(self):
        """Test that end_date is nullable (for active configs)"""
        from models import TradingConfig

        end_date_col = TradingConfig.__table__.columns['end_date']
        assert end_date_col.nullable is True


class TestModelRelationships:
    """Test relationships and constraints between models"""

    def test_all_models_inherit_base(self):
        """Test that all models inherit from Base"""
        from database import Base
        from models import (
            PriceHistory, DailySignal, Trade,
            Portfolio, PerformanceMetrics, TradingConfig
        )

        assert issubclass(PriceHistory, Base)
        assert issubclass(DailySignal, Base)
        assert issubclass(Trade, Base)
        assert issubclass(Portfolio, Base)
        assert issubclass(PerformanceMetrics, Base)
        assert issubclass(TradingConfig, Base)

    def test_trade_signal_id_reference(self):
        """Test that Trade has signal_id column"""
        from models import Trade

        signal_id_col = Trade.__table__.columns['signal_id']
        assert signal_id_col is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
