"""
Position Sizing Module
Functions for calculating position sizes using Kelly criterion and confidence scaling
"""
from datetime import date, timedelta
from constants import HALF_KELLY_FACTOR, HALF_KELLY_DEFAULT, DEFAULT_AVG_WIN, DEFAULT_AVG_LOSS


def calculate_position_size(base_allocation: float, confidence: float,
                            confidence_scaling_factor: float) -> float:
    """Scale position size by confidence (Kelly-lite)"""
    scaling = 1.0 - confidence_scaling_factor + (confidence_scaling_factor * confidence)
    return base_allocation * scaling


def capital_scaling_adjustment(capital: float, constraints) -> float:
    """Calculate capital scaling factor for larger capitals"""
    tier1_threshold = constraints.capital_scale_tier1_threshold
    tier1_factor = constraints.capital_scale_tier1_factor
    tier2_threshold = constraints.capital_scale_tier2_threshold
    tier2_factor = constraints.capital_scale_tier2_factor
    tier3_threshold = constraints.capital_scale_tier3_threshold
    tier3_factor = constraints.capital_scale_tier3_factor
    max_reduction = constraints.capital_scale_max_reduction

    if capital < tier1_threshold:
        return tier1_factor
    elif capital < tier2_threshold:
        range_size = tier2_threshold - tier1_threshold
        reduction = tier1_factor - tier2_factor
        return tier1_factor - ((capital - tier1_threshold) / range_size) * reduction
    elif capital < tier3_threshold:
        range_size = tier3_threshold - tier2_threshold
        reduction = tier2_factor - tier3_factor
        return tier2_factor - ((capital - tier2_threshold) / range_size) * reduction
    else:
        excess_capital = capital - tier3_threshold
        additional_reduction = min(tier3_factor - max_reduction, excess_capital / 2_000_000)
        return max(max_reduction, tier3_factor - additional_reduction)


def calculate_half_kelly(db, trade_date: date, constraints, lookback_days: int = 60) -> float:
    """Calculate half Kelly allocation based on recent trade performance"""
    from models import DailySignal
    
    lookback_start = trade_date - timedelta(days=lookback_days)

    trades = db.query(DailySignal).filter(
        DailySignal.trade_date >= lookback_start,
        DailySignal.trade_date < trade_date
    ).all()

    if not trades or len(trades) < constraints.min_trades_for_kelly:
        return HALF_KELLY_DEFAULT

    wins = 0
    total_trades = 0
    total_win_return = 0.0
    total_loss_return = 0.0

    for signal in trades:
        features = signal.features_used
        if not features or features.get('action') != 'BUY':
            continue

        total_trades += 1

        confidence = features.get('confidence_score', HALF_KELLY_DEFAULT)

        if confidence > constraints.kelly_confidence_threshold:
            wins += 1
            total_win_return += confidence
        else:
            total_loss_return += (1.0 - confidence)

    if total_trades < constraints.min_trades_for_kelly:
        return HALF_KELLY_DEFAULT

    win_rate = wins / total_trades
    avg_win = total_win_return / wins if wins > 0 else DEFAULT_AVG_WIN
    avg_loss = total_loss_return / (total_trades - wins) if (total_trades - wins) > 0 else DEFAULT_AVG_LOSS

    if avg_loss == 0:
        avg_loss = DEFAULT_AVG_LOSS

    payoff_ratio = avg_win / avg_loss

    kelly = (win_rate * payoff_ratio - (1 - win_rate)) / payoff_ratio

    half_kelly = kelly * HALF_KELLY_FACTOR

    return max(0.10, min(0.80, half_kelly))
