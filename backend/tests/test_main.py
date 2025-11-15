"""
Unit tests for main.py
Tests FastAPI endpoints and API functionality
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def mock_app_setup():
    """Setup mocks for FastAPI app initialization"""
    with patch('main.get_settings') as mock_settings, \
         patch('main.models') as mock_models, \
         patch('main.engine') as mock_engine:

        settings = Mock()
        settings.api_title = "Capital Allocator API"
        settings.api_version = "1.0.0"
        mock_settings.return_value = settings

        yield {
            'settings': mock_settings,
            'models': mock_models,
            'engine': mock_engine
        }


class TestRootEndpoint:
    """Test root health check endpoint"""

    @patch('main.get_settings')
    def test_root_returns_status(self, mock_get_settings):
        """Test root endpoint returns status"""
        settings = Mock()
        settings.api_title = "Capital Allocator API"
        settings.api_version = "1.0.0"
        mock_get_settings.return_value = settings

        from main import root

        response = root()

        assert response['status'] == 'online'
        assert response['app'] == "Capital Allocator API"
        assert response['version'] == "1.0.0"


class TestGetLatestPrices:
    """Test get_latest_prices endpoint"""

    def test_get_latest_prices_with_data(self, mock_db_session):
        """Test getting latest prices when data exists"""
        from main import get_latest_prices

        # Setup mock
        mock_date_result = Mock()
        mock_date_result.__getitem__ = Mock(return_value=date(2025, 11, 15))

        mock_db_session.query.return_value.order_by.return_value.first.return_value = mock_date_result

        mock_price1 = Mock()
        mock_price1.symbol = 'SPY'
        mock_price1.close_price = 581.25
        mock_price1.open_price = 580.50
        mock_price1.high_price = 582.00
        mock_price1.low_price = 579.00
        mock_price1.volume = 55000000.0

        mock_price2 = Mock()
        mock_price2.symbol = 'QQQ'
        mock_price2.close_price = 502.50
        mock_price2.open_price = 501.00
        mock_price2.high_price = 503.00
        mock_price2.low_price = 500.00
        mock_price2.volume = 42000000.0

        mock_db_session.query.return_value.filter.return_value.all.return_value = [mock_price1, mock_price2]

        response = get_latest_prices(mock_db_session)

        assert response['date'] == '2025-11-15'
        assert len(response['prices']) == 2
        assert response['prices'][0]['symbol'] == 'SPY'
        assert response['prices'][0]['close'] == 581.25

    def test_get_latest_prices_no_data(self, mock_db_session):
        """Test getting latest prices when no data exists"""
        from main import get_latest_prices

        mock_db_session.query.return_value.order_by.return_value.first.return_value = None

        response = get_latest_prices(mock_db_session)

        assert response['prices'] == []
        assert response['date'] is None


class TestGetPriceHistory:
    """Test get_price_history endpoint"""

    def test_get_price_history_success(self, mock_db_session):
        """Test getting price history for a symbol"""
        from main import get_price_history

        mock_price = Mock()
        mock_price.date = date(2025, 11, 15)
        mock_price.close_price = 581.25
        mock_price.open_price = 580.50
        mock_price.high_price = 582.00
        mock_price.low_price = 579.00
        mock_price.volume = 55000000.0

        mock_db_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_price]

        response = get_price_history('SPY', days=30, db=mock_db_session)

        assert response['symbol'] == 'SPY'
        assert len(response['data']) == 1
        assert response['data'][0]['date'] == '2025-11-15'

    def test_get_price_history_empty(self, mock_db_session):
        """Test getting price history when empty"""
        from main import get_price_history

        mock_db_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = []

        response = get_price_history('XYZ', days=30, db=mock_db_session)

        assert response['symbol'] == 'XYZ'
        assert response['data'] == []


class TestGetLatestSignal:
    """Test get_latest_signal endpoint"""

    def test_get_latest_signal_exists(self, mock_db_session):
        """Test getting latest signal when it exists"""
        from main import get_latest_signal

        mock_signal = Mock()
        mock_signal.trade_date = date(2025, 11, 15)
        mock_signal.generated_at = datetime(2025, 11, 15, 6, 0, 0, tzinfo=timezone.utc)
        mock_signal.allocations = {'SPY': 400.0, 'QQQ': 300.0, 'DIA': 100.0}
        mock_signal.model_type = 'regime_based'
        mock_signal.confidence_score = 0.75

        mock_db_session.query.return_value.order_by.return_value.first.return_value = mock_signal

        response = get_latest_signal(mock_db_session)

        assert response['trade_date'] == '2025-11-15'
        assert response['allocations']['SPY'] == 400.0
        assert response['model_type'] == 'regime_based'
        assert response['confidence'] == 0.75

    def test_get_latest_signal_none(self, mock_db_session):
        """Test getting latest signal when none exists"""
        from main import get_latest_signal

        mock_db_session.query.return_value.order_by.return_value.first.return_value = None

        response = get_latest_signal(mock_db_session)

        assert response['signal'] is None
        assert 'No signals' in response['message']


class TestGetPortfolio:
    """Test get_portfolio endpoint"""

    def test_get_portfolio_with_holdings(self, mock_db_session):
        """Test getting portfolio with holdings"""
        from main import get_portfolio

        mock_holding = Mock()
        mock_holding.symbol = 'SPY'
        mock_holding.quantity = 1.5
        mock_holding.avg_cost = 575.0

        mock_price = Mock()
        mock_price.close_price = 581.25

        mock_db_session.query.return_value.all.return_value = [mock_holding]
        mock_db_session.query.return_value.filter.return_value.order_by.return_value.first.return_value = mock_price

        response = get_portfolio(mock_db_session)

        assert len(response['positions']) == 1
        assert response['positions'][0]['symbol'] == 'SPY'
        assert response['positions'][0]['quantity'] == 1.5
        assert response['total_value'] > 0

    def test_get_portfolio_empty(self, mock_db_session):
        """Test getting empty portfolio"""
        from main import get_portfolio

        mock_db_session.query.return_value.all.return_value = []

        response = get_portfolio(mock_db_session)

        assert response['positions'] == []
        assert response['total_value'] == 0


class TestGetTradeHistory:
    """Test get_trade_history endpoint"""

    def test_get_trade_history_with_trades(self, mock_db_session):
        """Test getting trade history"""
        from main import get_trade_history
        from models import ActionType

        mock_trade = Mock()
        mock_trade.trade_date = date(2025, 11, 15)
        mock_trade.symbol = 'SPY'
        mock_trade.action = ActionType.BUY
        mock_trade.quantity = 0.69
        mock_trade.price = 580.0
        mock_trade.amount = 400.2

        mock_db_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_trade]

        response = get_trade_history(days=30, db=mock_db_session)

        assert len(response['trades']) == 1
        assert response['trades'][0]['symbol'] == 'SPY'
        assert response['trades'][0]['action'] == 'BUY'

    def test_get_trade_history_empty(self, mock_db_session):
        """Test getting empty trade history"""
        from main import get_trade_history

        mock_db_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = []

        response = get_trade_history(days=30, db=mock_db_session)

        assert response['trades'] == []


class TestGetPerformance:
    """Test get_performance endpoint"""

    def test_get_performance_with_metrics(self, mock_db_session):
        """Test getting performance metrics"""
        from main import get_performance

        mock_metric = Mock()
        mock_metric.date = date(2025, 11, 15)
        mock_metric.portfolio_value = 1000.0
        mock_metric.total_value = 1100.0
        mock_metric.daily_return = 0.5
        mock_metric.cumulative_return = 1.5
        mock_metric.sharpe_ratio = 1.2
        mock_metric.max_drawdown = 2.5

        mock_db_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_metric]

        response = get_performance(days=90, db=mock_db_session)

        assert len(response['performance']) == 1
        assert response['performance'][0]['date'] == '2025-11-15'
        assert response['summary']['total_return'] == 1.5
        assert response['summary']['sharpe_ratio'] == 1.2

    def test_get_performance_empty(self, mock_db_session):
        """Test getting empty performance metrics"""
        from main import get_performance

        mock_db_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = []

        response = get_performance(days=90, db=mock_db_session)

        assert response['performance'] == []
        assert response['summary'] is None


class TestAPIIntegration:
    """Integration-style tests for API"""

    @patch('main.get_settings')
    def test_app_configuration(self, mock_get_settings):
        """Test that app is configured correctly"""
        settings = Mock()
        settings.api_title = "Capital Allocator API"
        settings.api_version = "1.0.0"
        mock_get_settings.return_value = settings

        from main import app

        assert app.title == "Capital Allocator API"
        assert app.version == "1.0.0"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
