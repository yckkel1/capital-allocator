"""
Trade Evaluation Module
Functions for evaluating individual trades and calculating their impact
"""
from datetime import date, timedelta
from typing import List, TYPE_CHECKING

from .data_models import TradeEvaluation
from .market_analysis import detect_market_condition
from .constants import (
    HORIZON_10D, HORIZON_20D, HORIZON_30D,
    DRAWDOWN_WINDOW_BEFORE, DRAWDOWN_WINDOW_AFTER,
    SCORE_MIN, SCORE_MAX
)

if TYPE_CHECKING:
    from psycopg2.extensions import cursor


def calculate_drawdown_contribution(cursor, trade_date: date, trade_pnl: float) -> float:
    """
    Calculate how much a trade contributed to maximum drawdown

    Returns:
        Float between 0-100 representing percentage contribution
    """
    # Get performance data around the trade
    window_start = trade_date - timedelta(days=DRAWDOWN_WINDOW_BEFORE)
    window_end = trade_date + timedelta(days=DRAWDOWN_WINDOW_AFTER)

    cursor.execute("""
        SELECT date, total_value
        FROM performance_metrics
        WHERE date >= %s AND date <= %s
        ORDER BY date
    """, (window_start, window_end))

    values = [(row['date'], float(row['total_value'])) for row in cursor.fetchall()]

    if len(values) < 2:
        return 0.0

    # Find peak before trade and trough after
    trade_idx = None
    for i, (d, _) in enumerate(values):
        if d >= trade_date:
            trade_idx = i
            break

    if trade_idx is None or trade_idx == 0:
        return 0.0

    peak_value = max(v for _, v in values[:trade_idx + 1])
    trough_value = min(v for _, v in values[trade_idx:]) if trade_idx < len(values) else values[-1][1]

    # Calculate drawdown
    drawdown_pct = ((peak_value - trough_value) / peak_value * 100) if peak_value > 0 else 0

    # If trade lost money and there was a drawdown, attribute proportionally
    if trade_pnl < 0 and drawdown_pct > 0:
        # Contribution is based on how much the trade lost relative to the drawdown
        contribution = min(100, abs(trade_pnl) / (peak_value * drawdown_pct / 100) * 100)
        return contribution

    return 0.0


def evaluate_trades(cursor, config, start_date: date, end_date: date) -> List[TradeEvaluation]:
    """
    Evaluate all trades in the period with multi-horizon analysis

    Returns:
        List of TradeEvaluation objects
    """
    evaluations = []

    # Get all trades in period
    cursor.execute("""
        SELECT
            t.*,
            ds.features_used
        FROM trades t
        JOIN daily_signals ds ON t.signal_id = ds.id
        WHERE t.trade_date >= %s AND t.trade_date <= %s
        ORDER BY t.trade_date, t.id
    """, (start_date, end_date))

    trades = cursor.fetchall()

    for trade in trades:
        trade_date = trade['trade_date']
        symbol = trade['symbol']
        action = trade['action']
        amount = float(trade['amount'])
        quantity = float(trade['quantity'])
        price = float(trade['price'])

        features = trade['features_used']
        regime_score = features.get('regime', 0)
        regime = 'bullish' if regime_score > config.regime_classification_bullish_threshold else \
                 'bearish' if regime_score < config.regime_classification_bearish_threshold else 'neutral'

        # Extract confidence bucket and signal type from features
        confidence_bucket = features.get('confidence_bucket', 'unknown')
        signal_type = features.get('signal_type', 'unknown')

        # Detect market condition
        market_condition = detect_market_condition(cursor, config, trade_date)

        # Multi-horizon P&L calculation
        pnl_horizons = {}
        for horizon, days in [('10d', HORIZON_10D), ('20d', HORIZON_20D), ('30d', HORIZON_30D)]:
            future_date = trade_date + timedelta(days=days)

            cursor.execute("""
                SELECT close_price
                FROM price_history
                WHERE symbol = %s
                AND date > %s AND date <= %s
                ORDER BY date DESC
                LIMIT 1
            """, (symbol, trade_date, future_date))

            future_price_row = cursor.fetchone()
            future_price = float(future_price_row['close_price']) if future_price_row else price

            # Calculate P&L for this horizon
            if action == 'BUY':
                horizon_pnl = (future_price - price) * abs(quantity)
            else:  # SELL
                horizon_pnl = (price - future_price) * abs(quantity)

            pnl_horizons[horizon] = horizon_pnl

        # Best performing horizon
        best_horizon = max(pnl_horizons.keys(), key=lambda k: pnl_horizons[k])
        best_pnl = pnl_horizons[best_horizon]

        # Use best horizon for profitability determination
        was_profitable = best_pnl > 0
        pnl = best_pnl  # Use best horizon as the primary P&L

        # Calculate contribution to drawdown
        drawdown_contribution = calculate_drawdown_contribution(cursor, trade_date, pnl_horizons['10d'])

        # Calculate Sharpe impact using tunable bonuses/penalties
        sharpe_impact = 0.0
        if market_condition == 'momentum' and action == 'BUY' and regime == 'bullish':
            sharpe_impact = config.score_momentum_bonus
        elif market_condition == 'choppy' and action == 'HOLD':
            sharpe_impact = config.score_momentum_bonus * config.score_hold_bonus_multiplier
        elif market_condition == 'choppy' and action == 'BUY':
            sharpe_impact = config.score_choppy_penalty

        # Bonus for mean reversion trades that work
        if signal_type and 'mean_reversion' in signal_type and was_profitable:
            sharpe_impact += config.score_mean_reversion_bonus

        # Calculate trade score (-1 to 1) using tunable scoring parameters
        score = 0.0

        # Positive factors
        if was_profitable:
            score += config.score_profitable_bonus
        if sharpe_impact > 0:
            score += config.score_sharpe_bonus
        if drawdown_contribution < config.score_dd_low_threshold:
            score += config.score_low_dd_bonus

        # Multi-horizon consistency bonus
        profitable_horizons = sum(1 for p in pnl_horizons.values() if p > 0)
        if profitable_horizons == 3:
            score += config.score_all_horizons_bonus
        elif profitable_horizons == 2:
            score += config.score_two_horizons_bonus

        # Negative factors
        if not was_profitable:
            score += config.score_unprofitable_penalty
        if drawdown_contribution > config.score_dd_high_threshold:
            score += config.score_high_dd_penalty
        if sharpe_impact < 0:
            score += config.score_sharpe_penalty

        # Market condition alignment
        if market_condition == 'momentum' and action == 'BUY' and was_profitable:
            score += config.score_momentum_bonus
        elif market_condition == 'choppy' and action == 'BUY' and not was_profitable:
            score += config.score_choppy_penalty

        # Confidence bucket scoring
        if confidence_bucket == 'high' and was_profitable:
            score += config.score_confidence_bonus
        elif confidence_bucket == 'low' and not was_profitable:
            score += config.score_confidence_bonus

        score = max(SCORE_MIN, min(SCORE_MAX, score))  # Clamp to [-1, 1]

        # Should have avoided?
        should_have_avoided = (
            drawdown_contribution > config.should_avoid_dd_threshold or
            (market_condition == 'choppy' and action == 'BUY' and not was_profitable) or
            (confidence_bucket == 'low' and not was_profitable and pnl_horizons['10d'] < config.should_avoid_loss_threshold)
        )

        evaluation = TradeEvaluation(
            trade_date=trade_date,
            symbol=symbol,
            action=action,
            amount=amount,
            regime=regime,
            market_condition=market_condition,
            contribution_to_drawdown=drawdown_contribution,
            sharpe_impact=sharpe_impact,
            was_profitable=was_profitable,
            pnl=pnl,
            pnl_10d=pnl_horizons['10d'],
            pnl_20d=pnl_horizons['20d'],
            pnl_30d=pnl_horizons['30d'],
            best_horizon=best_horizon,
            confidence_bucket=confidence_bucket,
            signal_type=signal_type,
            score=score,
            should_have_avoided=should_have_avoided
        )

        evaluations.append(evaluation)

    return evaluations
