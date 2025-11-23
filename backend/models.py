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


class StrategyConstraints(Base):
    """System constraints and non-tunable configuration"""
    __tablename__ = "strategy_constraints"

    id = Column(Integer, primary_key=True, index=True)
    start_date = Column(Date, nullable=False, index=True)
    end_date = Column(Date, nullable=True, index=True)  # NULL means currently active

    # Position Management
    min_holding_threshold = Column(Float, nullable=False, default=10.0)

    # Capital Scaling Breakpoints
    capital_scale_tier1_threshold = Column(Float, nullable=False, default=10000.0)
    capital_scale_tier1_factor = Column(Float, nullable=False, default=1.0)
    capital_scale_tier2_threshold = Column(Float, nullable=False, default=50000.0)
    capital_scale_tier2_factor = Column(Float, nullable=False, default=0.75)
    capital_scale_tier3_threshold = Column(Float, nullable=False, default=200000.0)
    capital_scale_tier3_factor = Column(Float, nullable=False, default=0.50)
    capital_scale_max_reduction = Column(Float, nullable=False, default=0.35)

    # Kelly Criterion
    min_trades_for_kelly = Column(Integer, nullable=False, default=10)
    kelly_confidence_threshold = Column(Float, nullable=False, default=0.6)

    # Data Requirements
    min_data_days = Column(Integer, nullable=False, default=60)

    # Time Horizons
    pnl_horizon_short = Column(Integer, nullable=False, default=10)
    pnl_horizon_medium = Column(Integer, nullable=False, default=20)
    pnl_horizon_long = Column(Integer, nullable=False, default=30)

    # Risk-Free Rate
    risk_free_rate = Column(Float, nullable=False, default=0.05)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(String(100), nullable=True)
    notes = Column(String(500), nullable=True)


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

    # Mean Reversion Parameters (NEW)
    rsi_oversold_threshold = Column(Float, nullable=False, default=30.0)
    rsi_overbought_threshold = Column(Float, nullable=False, default=70.0)
    bollinger_std_multiplier = Column(Float, nullable=False, default=2.0)
    mean_reversion_allocation = Column(Float, nullable=False, default=0.4)  # Allocation for mean reversion signals

    # Adaptive Threshold Parameters (NEW)
    volatility_adjustment_factor = Column(Float, nullable=False, default=0.4)  # How much to adjust thresholds based on vol
    base_volatility = Column(Float, nullable=False, default=0.01)  # Historical average volatility baseline

    # Confidence-Based Position Sizing (NEW)
    min_confidence_threshold = Column(Float, nullable=False, default=0.3)  # Minimum confidence to trade
    confidence_scaling_factor = Column(Float, nullable=False, default=0.5)  # How much confidence affects sizing

    # Circuit Breaker Parameters (NEW)
    intramonth_drawdown_limit = Column(Float, nullable=False, default=0.10)  # 10% intra-month max drawdown
    circuit_breaker_reduction = Column(Float, nullable=False, default=0.5)  # Reduce positions by 50% when triggered

    # Regime Transition Detection
    regime_transition_threshold = Column(Float, nullable=False, default=0.1)
    momentum_loss_threshold = Column(Float, nullable=False, default=-0.15)
    momentum_gain_threshold = Column(Float, nullable=False, default=0.15)
    strong_trend_threshold = Column(Float, nullable=False, default=0.4)

    # Confidence Scoring
    regime_confidence_divisor = Column(Float, nullable=False, default=0.5)
    risk_penalty_min = Column(Float, nullable=False, default=40.0)
    risk_penalty_max = Column(Float, nullable=False, default=60.0)
    trend_consistency_threshold = Column(Float, nullable=False, default=1.2)
    mean_reversion_base_confidence = Column(Float, nullable=False, default=0.6)
    consistency_bonus = Column(Float, nullable=False, default=0.2)
    risk_penalty_multiplier = Column(Float, nullable=False, default=0.3)
    confidence_bucket_high_threshold = Column(Float, nullable=False, default=0.7)
    confidence_bucket_medium_threshold = Column(Float, nullable=False, default=0.5)

    # Mean Reversion Signals
    bb_oversold_threshold = Column(Float, nullable=False, default=-0.5)
    bb_overbought_threshold = Column(Float, nullable=False, default=0.5)
    oversold_strong_bonus = Column(Float, nullable=False, default=0.3)
    oversold_mild_bonus = Column(Float, nullable=False, default=0.1)
    rsi_mild_oversold = Column(Float, nullable=False, default=40.0)
    bb_mild_oversold = Column(Float, nullable=False, default=0.0)
    overbought_penalty = Column(Float, nullable=False, default=-0.2)

    # Downward Pressure Detection
    price_vs_sma_threshold = Column(Float, nullable=False, default=-0.02)
    high_volatility_threshold = Column(Float, nullable=False, default=0.015)
    negative_return_threshold = Column(Float, nullable=False, default=-0.03)
    severe_pressure_threshold = Column(Float, nullable=False, default=0.67)
    moderate_pressure_threshold = Column(Float, nullable=False, default=0.50)
    severe_pressure_risk = Column(Float, nullable=False, default=50.0)
    moderate_pressure_risk = Column(Float, nullable=False, default=45.0)

    # Dynamic Selling Behavior
    defensive_cash_threshold = Column(Float, nullable=False, default=70.0)
    sell_defensive_multiplier = Column(Float, nullable=False, default=0.5)
    sell_aggressive_multiplier = Column(Float, nullable=False, default=1.2)
    sell_moderate_pressure_multiplier = Column(Float, nullable=False, default=0.6)
    sell_bullish_risk_multiplier = Column(Float, nullable=False, default=0.3)

    # Risk-Based Thresholds
    mean_reversion_max_risk = Column(Float, nullable=False, default=60.0)
    neutral_deleverage_risk = Column(Float, nullable=False, default=55.0)
    neutral_hold_risk = Column(Float, nullable=False, default=50.0)
    bullish_excessive_risk = Column(Float, nullable=False, default=65.0)
    extreme_risk_threshold = Column(Float, nullable=False, default=70.0)

    # Asset Diversification
    diversify_top_asset_max = Column(Float, nullable=False, default=0.50)
    diversify_top_asset_min = Column(Float, nullable=False, default=0.40)
    diversify_second_asset_max = Column(Float, nullable=False, default=0.35)
    diversify_second_asset_min = Column(Float, nullable=False, default=0.30)
    diversify_third_asset_max = Column(Float, nullable=False, default=0.25)
    diversify_third_asset_min = Column(Float, nullable=False, default=0.15)
    two_asset_top = Column(Float, nullable=False, default=0.65)
    two_asset_second = Column(Float, nullable=False, default=0.35)

    # Volatility & Normalization
    volatility_normalization_factor = Column(Float, nullable=False, default=0.02)
    stability_threshold = Column(Float, nullable=False, default=0.05)
    correlation_risk_base = Column(Float, nullable=False, default=30.0)
    correlation_risk_multiplier = Column(Float, nullable=False, default=100.0)

    # Indicator Periods
    rsi_period = Column(Integer, nullable=False, default=14)
    bollinger_period = Column(Integer, nullable=False, default=20)

    # Trend Consistency
    trend_aligned_multiplier = Column(Float, nullable=False, default=1.5)
    trend_mixed_multiplier = Column(Float, nullable=False, default=1.0)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(String(100), nullable=True)  # Who created this version (user/script)
    notes = Column(String(500), nullable=True)  # Optional notes about why parameters changed