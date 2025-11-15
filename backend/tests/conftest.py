"""
Shared pytest fixtures for all test modules.
Provides mock data, database sessions, and common test utilities.
"""
import os
import sys
from unittest.mock import MagicMock, patch

# CRITICAL: Set environment variables BEFORE any other imports
# This must happen before any module tries to load Settings
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/testdb")
os.environ.setdefault("ALPHAVANTAGE_API_KEY", "TEST_API_KEY")
os.environ.setdefault("API_TITLE", "Capital Allocator API")
os.environ.setdefault("API_VERSION", "1.0.0")
os.environ.setdefault("MODEL_TYPE", "momentum")
os.environ.setdefault("MARKET_CLOSE_TIME", "16:30")
os.environ.setdefault("SIGNAL_GENERATION_TIME", "06:00")

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# CRITICAL: Mock SQLAlchemy engine creation BEFORE database.py is imported
# This prevents actual database connection attempts while keeping models functional
_mock_engine = MagicMock()
_mock_engine.url = "postgresql://test:test@localhost:5432/testdb"

# Only mock create_engine, not sessionmaker or declarative_base
# This allows models to be defined properly
_engine_patch = patch('sqlalchemy.create_engine', return_value=_mock_engine)
_engine_patch.start()

# CRITICAL: Mock psycopg2.connect to prevent database connections
# This is needed for config_loader.py which uses psycopg2 directly
_mock_psycopg2_conn = MagicMock()
_mock_psycopg2_cursor = MagicMock()
_mock_psycopg2_conn.cursor.return_value = _mock_psycopg2_cursor

# Mock the cursor to return a default config
from datetime import date as _date
_mock_psycopg2_cursor.fetchone.return_value = {
    'id': 1,
    'start_date': _date(2025, 11, 1),
    'end_date': None,
    'daily_capital': 1000.0,
    'assets': '["SPY", "QQQ", "DIA"]',
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
    'notes': 'Test configuration'
}

_psycopg2_patch = patch('psycopg2.connect', return_value=_mock_psycopg2_conn)
_psycopg2_patch.start()

import pytest
from unittest.mock import Mock, MagicMock, patch, PropertyMock
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal
import json


@pytest.fixture
def mock_settings():
    """Mock application settings"""
    settings = Mock()
    settings.database_url = "postgresql://test:test@localhost:5432/testdb"
    settings.alphavantage_api_key = "TEST_API_KEY"
    settings.api_title = "Capital Allocator API"
    settings.api_version = "1.0.0"
    settings.model_type = "momentum"
    settings.market_close_time = "16:30"
    settings.signal_generation_time = "06:00"
    return settings


@pytest.fixture
def mock_trading_config():
    """Mock trading configuration from database"""
    from config_loader import TradingConfig
    return TradingConfig(
        id=1,
        start_date=date(2025, 11, 1),
        end_date=None,
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
        min_sharpe_target=1.0,
        created_by='test',
        notes='Test configuration'
    )


@pytest.fixture
def mock_db_session():
    """Mock SQLAlchemy database session"""
    session = MagicMock()
    session.query.return_value.filter.return_value.first.return_value = None
    session.query.return_value.filter.return_value.all.return_value = []
    session.query.return_value.order_by.return_value.first.return_value = None
    session.query.return_value.all.return_value = []
    session.add = MagicMock()
    session.commit = MagicMock()
    session.rollback = MagicMock()
    session.close = MagicMock()
    return session


@pytest.fixture
def mock_psycopg2_connection():
    """Mock psycopg2 database connection"""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.fetchone.return_value = None
    mock_cursor.fetchall.return_value = []
    mock_cursor.execute = MagicMock()
    mock_conn.commit = MagicMock()
    mock_conn.rollback = MagicMock()
    mock_conn.close = MagicMock()
    return mock_conn, mock_cursor


@pytest.fixture
def sample_price_data():
    """Sample historical price data for testing"""
    base_date = date(2025, 11, 1)
    data = []

    for i in range(100):
        trade_date = base_date - timedelta(days=i)
        # Skip weekends
        if trade_date.weekday() >= 5:
            continue

        for symbol in ["SPY", "QQQ", "DIA"]:
            if symbol == "SPY":
                base_price = 580.0
            elif symbol == "QQQ":
                base_price = 500.0
            else:
                base_price = 420.0

            # Add some variation
            variation = (i % 10 - 5) * 0.5
            close = base_price + variation

            data.append({
                "date": trade_date,
                "symbol": symbol,
                "open_price": close - 0.5,
                "high_price": close + 1.0,
                "low_price": close - 1.5,
                "close_price": close,
                "volume": 50000000.0
            })

    return data


@pytest.fixture
def sample_signal_data():
    """Sample daily signal data"""
    return {
        "id": 1,
        "trade_date": date(2025, 11, 15),
        "generated_at": datetime(2025, 11, 15, 6, 0, 0, tzinfo=timezone.utc),
        "allocations": {"SPY": 400.0, "QQQ": 300.0, "DIA": 100.0},
        "model_type": "regime_based",
        "confidence_score": 0.75,
        "features_used": {
            "regime": 0.35,
            "risk": 45.0,
            "action": "BUY",
            "allocation_pct": 0.8,
            "assets": {
                "SPY": {
                    "returns_5d": 0.015,
                    "returns_20d": 0.035,
                    "returns_60d": 0.08,
                    "volatility": 0.012,
                    "score": 3.5
                },
                "QQQ": {
                    "returns_5d": 0.012,
                    "returns_20d": 0.03,
                    "returns_60d": 0.075,
                    "volatility": 0.015,
                    "score": 3.0
                },
                "DIA": {
                    "returns_5d": 0.008,
                    "returns_20d": 0.025,
                    "returns_60d": 0.06,
                    "volatility": 0.01,
                    "score": 2.5
                }
            }
        }
    }


@pytest.fixture
def sample_trade_data():
    """Sample trade records"""
    return [
        {
            "id": 1,
            "trade_date": date(2025, 11, 15),
            "executed_at": datetime(2025, 11, 15, 9, 30, 0, tzinfo=timezone.utc),
            "symbol": "SPY",
            "action": "BUY",
            "quantity": 0.6896,
            "price": 580.0,
            "amount": 399.97,
            "signal_id": 1
        },
        {
            "id": 2,
            "trade_date": date(2025, 11, 15),
            "executed_at": datetime(2025, 11, 15, 9, 30, 0, tzinfo=timezone.utc),
            "symbol": "QQQ",
            "action": "BUY",
            "quantity": 0.6000,
            "price": 500.0,
            "amount": 300.0,
            "signal_id": 1
        }
    ]


@pytest.fixture
def sample_portfolio_data():
    """Sample portfolio holdings"""
    return [
        {
            "id": 1,
            "symbol": "SPY",
            "quantity": 1.5,
            "avg_cost": 575.0,
            "last_updated": datetime(2025, 11, 15, 10, 0, 0, tzinfo=timezone.utc)
        },
        {
            "id": 2,
            "symbol": "QQQ",
            "quantity": 1.2,
            "avg_cost": 495.0,
            "last_updated": datetime(2025, 11, 15, 10, 0, 0, tzinfo=timezone.utc)
        }
    ]


@pytest.fixture
def sample_performance_data():
    """Sample performance metrics data"""
    base_date = date(2025, 11, 1)
    data = []

    for i in range(20):
        trade_date = base_date + timedelta(days=i)
        # Skip weekends
        if trade_date.weekday() >= 5:
            continue

        capital = 1000.0 * (i + 1)
        portfolio_value = capital * (1 + 0.001 * i)  # Small growth
        cash_balance = capital * 0.1  # 10% cash
        total_value = portfolio_value + cash_balance
        daily_return = 0.1 if i > 0 else 0
        cumulative_return = 0.1 * i

        data.append({
            "id": i + 1,
            "date": trade_date,
            "portfolio_value": portfolio_value,
            "cash_balance": cash_balance,
            "total_value": total_value,
            "daily_return": daily_return,
            "cumulative_return": cumulative_return,
            "sharpe_ratio": 1.2,
            "max_drawdown": 2.5
        })

    return data


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set mock environment variables for testing"""
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost:5432/testdb")
    monkeypatch.setenv("ALPHAVANTAGE_API_KEY", "TEST_API_KEY")
    monkeypatch.setenv("API_TITLE", "Capital Allocator API")
    monkeypatch.setenv("API_VERSION", "1.0.0")


def load_test_data(filename):
    """Load test data from JSON file"""
    test_data_dir = os.path.join(os.path.dirname(__file__), "test_data")
    filepath = os.path.join(test_data_dir, filename)

    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            return json.load(f)
    return None


@pytest.fixture
def test_data_dir():
    """Return path to test data directory"""
    return os.path.join(os.path.dirname(__file__), "test_data")
