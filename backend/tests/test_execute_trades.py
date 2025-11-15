"""
Unit tests for execute_trades.py
Tests trade execution logic
"""
import pytest
from unittest.mock import Mock, patch, MagicMock, call
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestTradeExecutorInit:
    """Test TradeExecutor initialization"""

    @patch('execute_trades.psycopg2.connect')
    @patch('execute_trades.get_settings')
    def test_executor_init(self, mock_get_settings, mock_connect):
        """Test TradeExecutor initialization"""
        mock_settings = Mock()
        mock_settings.database_url = "postgresql://test:test@localhost:5432/testdb"
        mock_get_settings.return_value = mock_settings

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        from execute_trades import TradeExecutor

        executor = TradeExecutor()

        mock_connect.assert_called_once()
        assert executor.conn is mock_conn
        assert executor.cursor is mock_cursor

    @patch('execute_trades.psycopg2.connect')
    @patch('execute_trades.get_settings')
    def test_executor_close(self, mock_get_settings, mock_connect):
        """Test TradeExecutor close method"""
        mock_settings = Mock()
        mock_settings.database_url = "postgresql://test"
        mock_get_settings.return_value = mock_settings

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        from execute_trades import TradeExecutor

        executor = TradeExecutor()
        executor.close()

        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()


class TestGetLatestSignal:
    """Test get_latest_signal method"""

    @patch('execute_trades.psycopg2.connect')
    @patch('execute_trades.get_settings')
    def test_get_latest_signal_success(self, mock_get_settings, mock_connect):
        """Test getting latest signal successfully"""
        mock_settings = Mock()
        mock_settings.database_url = "postgresql://test"
        mock_get_settings.return_value = mock_settings

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.fetchone.return_value = {
            'id': 1,
            'trade_date': date(2025, 11, 15),
            'allocations': {'SPY': 400.0, 'QQQ': 300.0, 'DIA': 100.0},
            'features_used': {
                'action': 'BUY',
                'allocation_pct': 0.8
            }
        }

        from execute_trades import TradeExecutor

        executor = TradeExecutor()
        signal = executor.get_latest_signal()

        assert signal['id'] == 1
        assert signal['allocations']['SPY'] == 400.0
        assert signal['features_used']['action'] == 'BUY'

    @patch('execute_trades.psycopg2.connect')
    @patch('execute_trades.get_settings')
    def test_get_latest_signal_no_signals(self, mock_get_settings, mock_connect):
        """Test getting latest signal when none exist"""
        mock_settings = Mock()
        mock_settings.database_url = "postgresql://test"
        mock_get_settings.return_value = mock_settings

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None

        from execute_trades import TradeExecutor

        executor = TradeExecutor()

        with pytest.raises(Exception) as exc_info:
            executor.get_latest_signal()

        assert "No signals found" in str(exc_info.value)


class TestGetOpeningPrice:
    """Test get_opening_price method"""

    @patch('execute_trades.psycopg2.connect')
    @patch('execute_trades.get_settings')
    def test_get_opening_price_success(self, mock_get_settings, mock_connect):
        """Test getting opening price successfully"""
        mock_settings = Mock()
        mock_settings.database_url = "postgresql://test"
        mock_get_settings.return_value = mock_settings

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = {'open_price': 580.50}

        from execute_trades import TradeExecutor

        executor = TradeExecutor()
        price = executor.get_opening_price('SPY', '2025-11-15')

        assert price == Decimal('580.50')

    @patch('execute_trades.psycopg2.connect')
    @patch('execute_trades.get_settings')
    def test_get_opening_price_not_found(self, mock_get_settings, mock_connect):
        """Test getting opening price when not found"""
        mock_settings = Mock()
        mock_settings.database_url = "postgresql://test"
        mock_get_settings.return_value = mock_settings

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None

        from execute_trades import TradeExecutor

        executor = TradeExecutor()

        with pytest.raises(Exception) as exc_info:
            executor.get_opening_price('XYZ', '2025-11-15')

        assert "No opening price found" in str(exc_info.value)


class TestGetCurrentPositions:
    """Test get_current_positions method"""

    @patch('execute_trades.psycopg2.connect')
    @patch('execute_trades.get_settings')
    def test_get_current_positions(self, mock_get_settings, mock_connect):
        """Test getting current positions"""
        mock_settings = Mock()
        mock_settings.database_url = "postgresql://test"
        mock_get_settings.return_value = mock_settings

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [
            {
                'symbol': 'SPY',
                'total_quantity': 1.5,
                'avg_cost': 575.0,
                'total_cost': 862.5
            },
            {
                'symbol': 'QQQ',
                'total_quantity': 1.2,
                'avg_cost': 495.0,
                'total_cost': 594.0
            }
        ]

        from execute_trades import TradeExecutor

        executor = TradeExecutor()
        positions = executor.get_current_positions()

        assert 'SPY' in positions
        assert 'QQQ' in positions
        assert positions['SPY']['quantity'] == Decimal('1.5')
        assert positions['QQQ']['avg_cost'] == Decimal('495.0')

    @patch('execute_trades.psycopg2.connect')
    @patch('execute_trades.get_settings')
    def test_get_current_positions_empty(self, mock_get_settings, mock_connect):
        """Test getting empty positions"""
        mock_settings = Mock()
        mock_settings.database_url = "postgresql://test"
        mock_get_settings.return_value = mock_settings

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = []

        from execute_trades import TradeExecutor

        executor = TradeExecutor()
        positions = executor.get_current_positions()

        assert positions == {}


class TestCalculatePortfolioPnL:
    """Test calculate_portfolio_pnl method"""

    @patch('execute_trades.psycopg2.connect')
    @patch('execute_trades.get_settings')
    def test_calculate_pnl_profit(self, mock_get_settings, mock_connect):
        """Test P&L calculation with profit"""
        mock_settings = Mock()
        mock_settings.database_url = "postgresql://test"
        mock_get_settings.return_value = mock_settings
        mock_connect.return_value = MagicMock()

        from execute_trades import TradeExecutor

        executor = TradeExecutor()

        positions = {
            'SPY': {
                'quantity': Decimal('1.0'),
                'avg_cost': Decimal('580.0'),
                'total_cost': Decimal('580.0')
            }
        }

        current_prices = {'SPY': Decimal('590.0')}

        pnl = executor.calculate_portfolio_pnl(positions, current_prices)

        assert pnl['total_cost'] == Decimal('580.0')
        assert pnl['total_value'] == Decimal('590.0')
        assert pnl['pnl'] == Decimal('10.0')
        assert float(pnl['pnl_pct']) > 0

    @patch('execute_trades.psycopg2.connect')
    @patch('execute_trades.get_settings')
    def test_calculate_pnl_loss(self, mock_get_settings, mock_connect):
        """Test P&L calculation with loss"""
        mock_settings = Mock()
        mock_settings.database_url = "postgresql://test"
        mock_get_settings.return_value = mock_settings
        mock_connect.return_value = MagicMock()

        from execute_trades import TradeExecutor

        executor = TradeExecutor()

        positions = {
            'SPY': {
                'quantity': Decimal('1.0'),
                'avg_cost': Decimal('580.0'),
                'total_cost': Decimal('580.0')
            }
        }

        current_prices = {'SPY': Decimal('570.0')}

        pnl = executor.calculate_portfolio_pnl(positions, current_prices)

        assert pnl['pnl'] == Decimal('-10.0')
        assert float(pnl['pnl_pct']) < 0


class TestExecuteBuyTrades:
    """Test execute_buy_trades method"""

    @patch('execute_trades.psycopg2.connect')
    @patch('execute_trades.get_settings')
    def test_execute_buy_trades(self, mock_get_settings, mock_connect):
        """Test executing buy trades"""
        mock_settings = Mock()
        mock_settings.database_url = "postgresql://test"
        mock_get_settings.return_value = mock_settings

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = {'open_price': 580.0}

        from execute_trades import TradeExecutor

        executor = TradeExecutor()

        signal = {
            'allocations': {'SPY': 400.0, 'QQQ': 300.0}
        }

        trades = executor.execute_buy_trades(signal, 1, '2025-11-15')

        # Should have executed 2 buy trades
        assert len(trades) == 2
        assert trades[0]['side'] == 'BUY'
        mock_cursor.execute.assert_called()
        mock_conn.commit.assert_called_once()

    @patch('execute_trades.psycopg2.connect')
    @patch('execute_trades.get_settings')
    def test_execute_buy_trades_skip_zero_allocation(self, mock_get_settings, mock_connect):
        """Test that zero allocations are skipped"""
        mock_settings = Mock()
        mock_settings.database_url = "postgresql://test"
        mock_get_settings.return_value = mock_settings

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        from execute_trades import TradeExecutor

        executor = TradeExecutor()

        signal = {
            'allocations': {'SPY': 0.0, 'QQQ': 0.0}
        }

        trades = executor.execute_buy_trades(signal, 1, '2025-11-15')

        assert len(trades) == 0


class TestUpdatePortfolio:
    """Test update_portfolio method"""

    @patch('execute_trades.psycopg2.connect')
    @patch('execute_trades.get_settings')
    def test_update_portfolio_new_position(self, mock_get_settings, mock_connect):
        """Test updating portfolio with new position"""
        mock_settings = Mock()
        mock_settings.database_url = "postgresql://test"
        mock_get_settings.return_value = mock_settings

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None  # No existing position

        from execute_trades import TradeExecutor

        executor = TradeExecutor()

        trades = [{
            'symbol': 'SPY',
            'quantity': Decimal('0.69'),
            'price': Decimal('580.0'),
            'side': 'BUY',
            'total': Decimal('400.2')
        }]

        executor.update_portfolio(trades)

        # Should insert new position
        mock_cursor.execute.assert_called()
        mock_conn.commit.assert_called_once()

    @patch('execute_trades.psycopg2.connect')
    @patch('execute_trades.get_settings')
    def test_update_portfolio_existing_position(self, mock_get_settings, mock_connect):
        """Test updating existing portfolio position"""
        mock_settings = Mock()
        mock_settings.database_url = "postgresql://test"
        mock_get_settings.return_value = mock_settings

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = {
            'quantity': 1.0,
            'avg_cost': 575.0
        }

        from execute_trades import TradeExecutor

        executor = TradeExecutor()

        trades = [{
            'symbol': 'SPY',
            'quantity': Decimal('0.5'),
            'price': Decimal('580.0'),
            'side': 'BUY',
            'total': Decimal('290.0')
        }]

        executor.update_portfolio(trades)

        # Should update existing position with weighted average
        mock_cursor.execute.assert_called()
        mock_conn.commit.assert_called_once()

    @patch('execute_trades.psycopg2.connect')
    @patch('execute_trades.get_settings')
    def test_update_portfolio_sell_partial(self, mock_get_settings, mock_connect):
        """Test selling partial position"""
        mock_settings = Mock()
        mock_settings.database_url = "postgresql://test"
        mock_get_settings.return_value = mock_settings

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = {
            'quantity': 2.0,
            'avg_cost': 575.0
        }

        from execute_trades import TradeExecutor

        executor = TradeExecutor()

        trades = [{
            'symbol': 'SPY',
            'quantity': Decimal('1.0'),
            'price': Decimal('590.0'),
            'side': 'SELL',
            'total': Decimal('590.0')
        }]

        executor.update_portfolio(trades)

        mock_cursor.execute.assert_called()
        mock_conn.commit.assert_called_once()


class TestMainFunction:
    """Test main entry point"""

    @patch('execute_trades.TradeExecutor')
    def test_main_success(self, mock_executor_class):
        """Test main function with success"""
        mock_executor = Mock()
        mock_executor_class.return_value = mock_executor

        from execute_trades import main

        # Mock sys.argv
        with patch('sys.argv', ['execute_trades.py', '2025-11-15']):
            result = main()

        assert result == 0
        mock_executor.run.assert_called_once_with('2025-11-15')
        mock_executor.close.assert_called_once()

    @patch('execute_trades.TradeExecutor')
    def test_main_failure(self, mock_executor_class):
        """Test main function with failure"""
        mock_executor = Mock()
        mock_executor.run.side_effect = Exception("Database error")
        mock_executor_class.return_value = mock_executor

        from execute_trades import main

        with patch('sys.argv', ['execute_trades.py']):
            result = main()

        assert result == 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
