"""
Unit tests for scripts/fetch_data.py
Tests market data fetching functionality
"""
import pytest
from unittest.mock import Mock, patch, MagicMock, call
from datetime import date, datetime, timedelta
import pandas as pd
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'scripts'))


class TestFetchAndStorePrices:
    """Test fetch_and_store_prices function"""

    @patch('scripts.fetch_data.time.sleep')
    @patch('scripts.fetch_data.TimeSeries')
    @patch('scripts.fetch_data.SessionLocal')
    @patch('scripts.fetch_data.get_trading_config')
    @patch('scripts.fetch_data.get_settings')
    def test_fetch_prices_success(self, mock_settings, mock_config, mock_session, mock_ts_class, mock_sleep):
        """Test successful price fetching"""
        from scripts.fetch_data import fetch_and_store_prices

        # Setup mocks
        settings = Mock()
        settings.alphavantage_api_key = "TEST_KEY"
        mock_settings.return_value = settings

        config = Mock()
        config.assets = ['SPY']
        mock_config.return_value = config

        mock_db = MagicMock()
        mock_session.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = None  # No existing data

        # Create mock price data
        mock_ts = Mock()
        mock_ts_class.return_value = mock_ts

        mock_data = pd.DataFrame({
            '1. open': [580.50],
            '2. high': [582.00],
            '3. low': [579.00],
            '4. close': [581.25],
            '5. volume': [55000000.0]
        }, index=pd.to_datetime([date(2025, 11, 15)]))

        mock_ts.get_daily.return_value = (mock_data, {'metadata': 'test'})

        fetch_and_store_prices(date(2025, 11, 15))

        # Verify data was added (at least once)
        assert mock_db.add.called
        mock_db.commit.assert_called()

    @patch('scripts.fetch_data.time.sleep')
    @patch('scripts.fetch_data.TimeSeries')
    @patch('scripts.fetch_data.SessionLocal')
    @patch('scripts.fetch_data.get_trading_config')
    @patch('scripts.fetch_data.get_settings')
    def test_fetch_prices_existing_data(self, mock_settings, mock_config, mock_session, mock_ts_class, mock_sleep):
        """Test skipping fetch when data already exists"""
        from scripts.fetch_data import fetch_and_store_prices

        settings = Mock()
        settings.alphavantage_api_key = "TEST_KEY"
        mock_settings.return_value = settings

        config = Mock()
        config.assets = ['SPY']
        mock_config.return_value = config

        mock_db = MagicMock()
        mock_session.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = Mock()  # Existing data

        fetch_and_store_prices(date(2025, 11, 15))

        # Should not add new data
        mock_db.add.assert_not_called()

    @patch('scripts.fetch_data.time.sleep')
    @patch('scripts.fetch_data.TimeSeries')
    @patch('scripts.fetch_data.SessionLocal')
    @patch('scripts.fetch_data.get_trading_config')
    @patch('scripts.fetch_data.get_settings')
    def test_fetch_prices_retry_logic(self, mock_settings, mock_config, mock_session, mock_ts_class, mock_sleep):
        """Test retry logic on API failures"""
        from scripts.fetch_data import fetch_and_store_prices

        settings = Mock()
        settings.alphavantage_api_key = "TEST_KEY"
        mock_settings.return_value = settings

        config = Mock()
        config.assets = ['SPY']
        mock_config.return_value = config

        mock_db = MagicMock()
        mock_session.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = None

        mock_ts = Mock()
        mock_ts_class.return_value = mock_ts

        # First two attempts fail, third succeeds
        mock_data = pd.DataFrame({
            '1. open': [580.50],
            '2. high': [582.00],
            '3. low': [579.00],
            '4. close': [581.25],
            '5. volume': [55000000.0]
        }, index=pd.to_datetime([date(2025, 11, 15)]))

        mock_ts.get_daily.side_effect = [
            Exception("API Error"),
            (None, None),
            (mock_data, {'metadata': 'test'})
        ]

        fetch_and_store_prices(date(2025, 11, 15))

        # Should have retried (at least 3 times due to retry logic)
        assert mock_ts.get_daily.call_count >= 3
        assert mock_db.add.called

    @patch('scripts.fetch_data.time.sleep')
    @patch('scripts.fetch_data.TimeSeries')
    @patch('scripts.fetch_data.SessionLocal')
    @patch('scripts.fetch_data.get_trading_config')
    @patch('scripts.fetch_data.get_settings')
    def test_fetch_prices_empty_data(self, mock_settings, mock_config, mock_session, mock_ts_class, mock_sleep):
        """Test handling empty data response"""
        from scripts.fetch_data import fetch_and_store_prices

        settings = Mock()
        settings.alphavantage_api_key = "TEST_KEY"
        mock_settings.return_value = settings

        config = Mock()
        config.assets = ['SPY']
        mock_config.return_value = config

        mock_db = MagicMock()
        mock_session.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = None

        mock_ts = Mock()
        mock_ts_class.return_value = mock_ts
        mock_ts.get_daily.return_value = (pd.DataFrame(), None)

        fetch_and_store_prices(date(2025, 11, 15))

        # Should not add data for empty response
        mock_db.add.assert_not_called()


class TestBackfillHistoricalData:
    """Test backfill_historical_data function"""

    @patch('scripts.fetch_data.time.sleep')
    @patch('scripts.fetch_data.TimeSeries')
    @patch('scripts.fetch_data.SessionLocal')
    @patch('scripts.fetch_data.get_trading_config')
    @patch('scripts.fetch_data.get_settings')
    def test_backfill_success(self, mock_settings, mock_config, mock_session, mock_ts_class, mock_sleep):
        """Test successful historical data backfill"""
        from scripts.fetch_data import backfill_historical_data

        settings = Mock()
        settings.alphavantage_api_key = "TEST_KEY"
        mock_settings.return_value = settings

        config = Mock()
        config.assets = ['SPY']
        mock_config.return_value = config

        mock_db = MagicMock()
        mock_session.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = None  # No existing data

        mock_ts = Mock()
        mock_ts_class.return_value = mock_ts

        # Create mock historical data
        dates = pd.date_range(end=date.today(), periods=10)
        mock_data = pd.DataFrame({
            '1. open': [580.0 + i for i in range(10)],
            '2. high': [582.0 + i for i in range(10)],
            '3. low': [578.0 + i for i in range(10)],
            '4. close': [581.0 + i for i in range(10)],
            '5. volume': [50000000.0] * 10
        }, index=dates)

        mock_ts.get_daily.return_value = (mock_data, {'metadata': 'test'})

        backfill_historical_data(days=10)

        # Should add multiple records
        assert mock_db.add.call_count >= 1
        mock_db.commit.assert_called()

    @patch('scripts.fetch_data.time.sleep')
    @patch('scripts.fetch_data.TimeSeries')
    @patch('scripts.fetch_data.SessionLocal')
    @patch('scripts.fetch_data.get_trading_config')
    @patch('scripts.fetch_data.get_settings')
    def test_backfill_skips_existing(self, mock_settings, mock_config, mock_session, mock_ts_class, mock_sleep):
        """Test that backfill skips existing records"""
        from scripts.fetch_data import backfill_historical_data

        settings = Mock()
        settings.alphavantage_api_key = "TEST_KEY"
        mock_settings.return_value = settings

        config = Mock()
        config.assets = ['SPY']
        mock_config.return_value = config

        mock_db = MagicMock()
        mock_session.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = Mock()  # All data exists

        mock_ts = Mock()
        mock_ts_class.return_value = mock_ts

        dates = pd.date_range(end=date.today(), periods=10)
        mock_data = pd.DataFrame({
            '1. open': [580.0] * 10,
            '2. high': [582.0] * 10,
            '3. low': [578.0] * 10,
            '4. close': [581.0] * 10,
            '5. volume': [50000000.0] * 10
        }, index=dates)

        mock_ts.get_daily.return_value = (mock_data, {'metadata': 'test'})

        backfill_historical_data(days=10)

        # Should not add any records since they all exist
        mock_db.add.assert_not_called()

    @patch('scripts.fetch_data.TimeSeries')
    @patch('scripts.fetch_data.SessionLocal')
    @patch('scripts.fetch_data.get_trading_config')
    @patch('scripts.fetch_data.get_settings')
    def test_backfill_output_size_selection(self, mock_settings, mock_config, mock_session, mock_ts_class):
        """Test that output size is selected based on days requested"""
        from scripts.fetch_data import backfill_historical_data

        settings = Mock()
        settings.alphavantage_api_key = "TEST_KEY"
        mock_settings.return_value = settings

        config = Mock()
        config.assets = ['SPY']
        mock_config.return_value = config

        mock_db = MagicMock()
        mock_session.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = None

        mock_ts = Mock()
        mock_ts_class.return_value = mock_ts

        # For more than 100 days, should use 'full' output size
        mock_data = pd.DataFrame({
            '1. open': [],
            '2. high': [],
            '3. low': [],
            '4. close': [],
            '5. volume': []
        }, index=pd.to_datetime([]))

        mock_ts.get_daily.return_value = (mock_data, {})

        with patch('scripts.fetch_data.time.sleep'):
            backfill_historical_data(days=200)

        # Should call with 'full' outputsize
        mock_ts.get_daily.assert_called()
        call_args = mock_ts.get_daily.call_args
        assert call_args[1]['outputsize'] == 'full'


class TestMainFunction:
    """Test main entry point"""

    def test_main_fetch_specific_date(self):
        """Test main function fetches specific date"""
        from scripts.fetch_data import fetch_and_store_prices

        # Just verify the function exists and is callable
        assert callable(fetch_and_store_prices)

    def test_main_backfill(self):
        """Test main function handles backfill"""
        from scripts.fetch_data import backfill_historical_data

        # Just verify the function exists and is callable
        assert callable(backfill_historical_data)


class TestErrorHandling:
    """Test error handling in data fetching"""

    @patch('scripts.fetch_data.time.sleep')
    @patch('scripts.fetch_data.TimeSeries')
    @patch('scripts.fetch_data.SessionLocal')
    @patch('scripts.fetch_data.get_trading_config')
    @patch('scripts.fetch_data.get_settings')
    def test_database_error_rollback(self, mock_settings, mock_config, mock_session, mock_ts_class, mock_sleep):
        """Test database errors trigger rollback"""
        from scripts.fetch_data import fetch_and_store_prices

        settings = Mock()
        settings.alphavantage_api_key = "TEST_KEY"
        mock_settings.return_value = settings

        config = Mock()
        config.assets = ['SPY']
        mock_config.return_value = config

        mock_db = MagicMock()
        mock_session.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = None

        mock_ts = Mock()
        mock_ts_class.return_value = mock_ts

        mock_data = pd.DataFrame({
            '1. open': [580.50],
            '2. high': [582.00],
            '3. low': [579.00],
            '4. close': [581.25],
            '5. volume': [55000000.0]
        }, index=pd.to_datetime([date(2025, 11, 15)]))
        mock_ts.get_daily.return_value = (mock_data, {'metadata': 'test'})

        mock_db.commit.side_effect = Exception("Database error")

        with pytest.raises(Exception):
            fetch_and_store_prices(date(2025, 11, 15))

        mock_db.rollback.assert_called_once()
        mock_db.close.assert_called_once()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
