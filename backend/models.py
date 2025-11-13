from sqlalchemy import Column, Integer, String, Float, Date, DateTime, JSON, Enum as SQLEnum
from sqlalchemy.sql import func
from database import Base
import enum


class ActionType(str, enum.Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class PriceHistory(Base):
    """Daily price data for assets"""
    __tablename__ = "price_history"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, index=True)
    symbol = Column(String(10), nullable=False, index=True)
    open_price = Column(Float, nullable=False)
    high_price = Column(Float, nullable=False)
    low_price = Column(Float, nullable=False)
    close_price = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class DailySignal(Base):
    """Model-generated allocation signals"""
    __tablename__ = "daily_signals"
    
    id = Column(Integer, primary_key=True, index=True)
    trade_date = Column(Date, nullable=False, index=True, unique=True)
    generated_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Allocation decisions
    allocations = Column(JSON, nullable=False)  # {"SPY": 500, "QQQ": 500, "DJI": 0}
    
    # Model metadata
    model_type = Column(String(50), nullable=False)
    confidence_score = Column(Float)
    features_used = Column(JSON)  # Store feature values for debugging


class Trade(Base):
    """Executed trades history"""
    __tablename__ = "trades"
    
    id = Column(Integer, primary_key=True, index=True)
    trade_date = Column(Date, nullable=False, index=True)
    executed_at = Column(DateTime(timezone=True), server_default=func.now())
    
    symbol = Column(String(10), nullable=False)
    action = Column(SQLEnum(ActionType), nullable=False)
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    amount = Column(Float, nullable=False)  # quantity * price
    
    # Link to signal
    signal_id = Column(Integer)


class Portfolio(Base):
    """Current portfolio holdings"""
    __tablename__ = "portfolio"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(10), nullable=False, unique=True)
    quantity = Column(Float, nullable=False, default=0)
    avg_cost = Column(Float, nullable=False, default=0)
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class PerformanceMetrics(Base):
    """Daily P&L and performance tracking"""
    __tablename__ = "performance_metrics"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, index=True, unique=True)

    # Portfolio values
    portfolio_value = Column(Float, nullable=False)
    cash_balance = Column(Float, nullable=False)
    total_value = Column(Float, nullable=False)

    # Performance metrics
    daily_return = Column(Float)
    cumulative_return = Column(Float)
    sharpe_ratio = Column(Float)
    max_drawdown = Column(Float)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class TradingConfig(Base):
    """Versioned trading configuration parameters"""
    __tablename__ = "trading_config"

    id = Column(Integer, primary_key=True, index=True)
    start_date = Column(Date, nullable=False, index=True)
    end_date = Column(Date, nullable=True, index=True)  # NULL means currently active

    # Basic Trading Parameters
    daily_capital = Column(Float, nullable=False, default=1000.0)
    assets = Column(JSON, nullable=False)  # ["SPY", "QQQ", "DIA"]
    lookback_days = Column(Integer, nullable=False, default=252)

    # Regime Detection Thresholds
    regime_bullish_threshold = Column(Float, nullable=False, default=0.3)
    regime_bearish_threshold = Column(Float, nullable=False, default=-0.3)

    # Risk Level Thresholds
    risk_high_threshold = Column(Float, nullable=False, default=70.0)
    risk_medium_threshold = Column(Float, nullable=False, default=40.0)

    # Allocation Percentages (Bullish Regime)
    allocation_low_risk = Column(Float, nullable=False, default=0.8)
    allocation_medium_risk = Column(Float, nullable=False, default=0.5)
    allocation_high_risk = Column(Float, nullable=False, default=0.3)

    # Neutral Regime Allocation
    allocation_neutral = Column(Float, nullable=False, default=0.2)

    # Sell Percentage (Bearish Regime)
    sell_percentage = Column(Float, nullable=False, default=0.7)

    # Asset Ranking Weights
    momentum_weight = Column(Float, nullable=False, default=0.6)
    price_momentum_weight = Column(Float, nullable=False, default=0.4)

    # Risk Management Targets
    max_drawdown_tolerance = Column(Float, nullable=False, default=15.0)
    min_sharpe_target = Column(Float, nullable=False, default=1.0)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(String(100), nullable=True)  # Who created this version (user/script)
    notes = Column(String(500), nullable=True)  # Optional notes about why parameters changed