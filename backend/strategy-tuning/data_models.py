"""
Data Models for Strategy Tuning
Contains dataclasses and data structures used in strategy tuning
"""
from dataclasses import dataclass
from datetime import date


@dataclass
class TradeEvaluation:
    """Evaluation of a specific trade"""
    trade_date: date
    symbol: str
    action: str
    amount: float
    regime: str
    market_condition: str  # 'momentum' or 'choppy'

    # Impact metrics
    contribution_to_drawdown: float  # How much this trade contributed to max DD
    sharpe_impact: float  # Impact on Sharpe ratio
    was_profitable: bool
    pnl: float

    # Rating (required fields must come before optional)
    score: float  # -1.0 to 1.0, negative = bad trade, positive = good trade
    should_have_avoided: bool

    # Enhanced metrics (NEW) - optional fields with defaults
    pnl_10d: float = 0.0  # P&L at 10 days
    pnl_20d: float = 0.0  # P&L at 20 days
    pnl_30d: float = 0.0  # P&L at 30 days
    best_horizon: str = "10d"  # Which horizon was most profitable
    confidence_bucket: str = "unknown"  # Signal confidence bucket
    signal_type: str = "unknown"  # Type of signal (momentum, mean_reversion, etc.)
