"""
Enhanced Daily Signal Generation Script
Run this early AM (6:00 AM ET) to generate today's allocation

Improvements over v1:
- Mean reversion signals (RSI, Bollinger Bands) for neutral regimes
- Regime transition detection (early entry/exit)
- Adaptive thresholds based on volatility regime
- Position sizing by signal strength (Kelly-lite)
- Confidence bucket tracking
- Circuit breaker checks
"""

import pandas as pd
import numpy as np
from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models import PriceHistory, DailySignal, Portfolio, PerformanceMetrics
from config import get_settings, get_trading_config
from constraints_loader import get_active_strategy_constraints

settings = get_settings()
trading_config = get_trading_config()
constraints = get_active_strategy_constraints()

# Mathematical Constants
PERCENTAGE_MULTIPLIER = 100.0
RSI_NEUTRAL = 50.0
RSI_MAX = 100.0
ANNUAL_TRADING_DAYS = 252
HALF_KELLY_FACTOR = 0.5
HALF_KELLY_DEFAULT = 0.5
KELLY_MIN_ALLOCATION = 0.10
KELLY_MAX_ALLOCATION = 0.80

# Time horizons and periods
HORIZON_5D = 5
HORIZON_10D = 10
HORIZON_20D = 20
HORIZON_30D = 30
HORIZON_50D = 50
HORIZON_60D = 60
RSI_DEFAULT_PERIOD = 14
BB_DEFAULT_PERIOD = 20

# Default fallback values for calculations
DEFAULT_AVG_WIN = 0.05
DEFAULT_AVG_LOSS = 0.03
DEFAULT_VOLATILITY_DIVISOR = 0.001


def calculate_rsi(prices: pd.Series, period: int = None) -> float:
    """
    Calculate Relative Strength Index

    Args:
        prices: Price series
        period: RSI period (uses trading_config.rsi_period if not specified)

    Returns:
        float: RSI value between 0-100
    """
    if period is None:
        period = trading_config.rsi_period

    if len(prices) < period + 1:
        return RSI_NEUTRAL  # Neutral if insufficient data

    deltas = prices.diff()
    gains = deltas.where(deltas > 0, 0.0)
    losses = -deltas.where(deltas < 0, 0.0)

    avg_gain = gains.tail(period).mean()
    avg_loss = losses.tail(period).mean()

    if avg_loss == 0:
        return RSI_MAX

    rs = avg_gain / avg_loss
    rsi = PERCENTAGE_MULTIPLIER - (PERCENTAGE_MULTIPLIER / (1 + rs))

    return float(rsi)


def calculate_bollinger_bands(prices: pd.Series, period: int = None, num_std: float = None) -> dict:
    """
    Calculate Bollinger Bands position

    Args:
        prices: Price series
        period: Bollinger period (uses trading_config.bollinger_period if not specified)
        num_std: Standard deviation multiplier (uses trading_config.bollinger_std_multiplier if not specified)

    Returns:
        dict with 'upper', 'lower', 'middle', 'position' (-1 to +1 scale)
    """
    if period is None:
        period = trading_config.bollinger_period
    if num_std is None:
        num_std = trading_config.bollinger_std_multiplier

    if len(prices) < period:
        return {'upper': 0, 'lower': 0, 'middle': 0, 'position': 0}

    sma = prices.tail(period).mean()
    std = prices.tail(period).std()

    upper_band = sma + (std * num_std)
    lower_band = sma - (std * num_std)
    current_price = prices.iloc[-1]

    # Position: -1 = at lower band, 0 = at middle, +1 = at upper band
    band_width = upper_band - lower_band
    if band_width > 0:
        position = (current_price - sma) / (band_width / 2)
        position = max(-1, min(1, position))
    else:
        position = 0

    return {
        'upper': float(upper_band),
        'lower': float(lower_band),
        'middle': float(sma),
        'position': float(position)
    }


def detect_regime_transition(current_regime_score: float, previous_regime_score: float) -> str:
    """
    Detect regime transitions for early entry/exit signals using tunable thresholds

    Args:
        current_regime_score: Current regime score
        previous_regime_score: Previous regime score

    Returns:
        str: 'turning_bullish', 'turning_bearish', 'losing_momentum', 'gaining_momentum', 'stable'
    """
    if previous_regime_score is None:
        return 'stable'

    delta = current_regime_score - previous_regime_score

    # Turning points using tunable threshold
    threshold = trading_config.regime_transition_threshold
    if current_regime_score > threshold and previous_regime_score < -threshold:
        return 'turning_bullish'
    elif current_regime_score < -threshold and previous_regime_score > threshold:
        return 'turning_bearish'

    # Momentum changes within bullish territory using tunable thresholds
    if current_regime_score > trading_config.regime_bullish_threshold and delta < trading_config.momentum_loss_threshold:
        return 'losing_momentum'
    elif current_regime_score > 0 and delta > trading_config.momentum_gain_threshold:
        return 'gaining_momentum'

    return 'stable'


def calculate_adaptive_threshold(base_threshold: float, current_volatility: float,
                                  base_volatility: float, adjustment_factor: float) -> float:
    """
    Adjust regime threshold based on current volatility

    High vol -> higher threshold (harder to trigger)
    Low vol -> lower threshold (easier to trigger)
    """
    vol_ratio = current_volatility / base_volatility if base_volatility > 0 else 1.0
    adjustment = 1.0 + (adjustment_factor * (vol_ratio - 1.0))
    # Clamp adjustment using tunable thresholds
    adjustment = max(trading_config.adaptive_threshold_clamp_min,
                     min(trading_config.adaptive_threshold_clamp_max, adjustment))

    return base_threshold * adjustment


def calculate_confidence_score(regime_score: float, risk_score: float,
                                trend_consistency: float, mean_reversion_signal: bool) -> float:
    """
    Calculate overall confidence in the signal (0 to 1) using tunable parameters

    This is a CRITICAL function that drives position sizing decisions.
    All thresholds and weights are now tunable to allow quantitative optimization.

    Higher confidence = stronger position sizing

    Args:
        regime_score: Regime strength score
        risk_score: Current risk score (0-100)
        trend_consistency: Trend consistency multiplier
        mean_reversion_signal: Whether this is a mean reversion signal

    Returns:
        float: Confidence score (0 to 1)
    """
    # Base confidence from regime strength using tunable divisor
    regime_confidence = min(1.0, abs(regime_score) / trading_config.regime_confidence_divisor)

    # Risk penalty (high risk = lower confidence) using tunable min/max thresholds
    risk_penalty = max(0, (risk_score - trading_config.risk_penalty_min) /
                          (trading_config.risk_penalty_max - trading_config.risk_penalty_min))

    # Trend consistency bonus using tunable threshold and bonus amount
    consistency_bonus = trading_config.consistency_bonus if trend_consistency > trading_config.trend_consistency_threshold else 0

    # Mean reversion signals have moderate confidence (tunable)
    if mean_reversion_signal:
        base_confidence = trading_config.mean_reversion_base_confidence
    else:
        base_confidence = regime_confidence

    # Combine factors using tunable risk penalty multiplier
    confidence = base_confidence + consistency_bonus - (risk_penalty * trading_config.risk_penalty_multiplier)
    confidence = max(0, min(1.0, confidence))

    return confidence


def calculate_position_size(base_allocation: float, confidence: float,
                            confidence_scaling_factor: float) -> float:
    """
    Scale position size by confidence (Kelly-lite)

    base_allocation * (1 - scaling_factor + scaling_factor * confidence)
    """
    # At confidence=1.0, use full base allocation
    # At confidence=0.5, use (1 - 0.5*scaling_factor) of base allocation
    scaling = 1.0 - confidence_scaling_factor + (confidence_scaling_factor * confidence)
    return base_allocation * scaling


def check_circuit_breaker(db: Session, trade_date: date,
                          intramonth_drawdown_limit: float) -> tuple:
    """
    Check if circuit breaker should be triggered

    Returns:
        tuple: (triggered: bool, current_drawdown: float)
    """
    # Get start of current month
    month_start = date(trade_date.year, trade_date.month, 1)

    # Get performance data for current month
    perf_data = db.query(PerformanceMetrics).filter(
        PerformanceMetrics.date >= month_start,
        PerformanceMetrics.date < trade_date
    ).order_by(PerformanceMetrics.date.asc()).all()

    if len(perf_data) < 2:
        return (False, 0.0)

    # Calculate max drawdown this month
    peak_value = 0
    max_dd = 0

    for data in perf_data:
        value = float(data.total_value)
        if value > peak_value:
            peak_value = value

        if peak_value > 0:
            dd = (peak_value - value) / peak_value
            max_dd = max(max_dd, dd)

    triggered = max_dd >= intramonth_drawdown_limit
    return (triggered, max_dd)


def calculate_multi_timeframe_features(df: pd.DataFrame) -> dict:
    """
    Calculate features with multiple timeframes including mean reversion indicators

    Returns:
        dict with feature values including RSI, Bollinger Bands
    """
    # Calculate returns over different periods
    returns_5d = (df['close'].iloc[-1] / df['close'].iloc[-HORIZON_5D] - 1) if len(df) >= HORIZON_5D else 0
    returns_20d = (df['close'].iloc[-1] / df['close'].iloc[-HORIZON_20D] - 1) if len(df) >= HORIZON_20D else 0
    returns_60d = (df['close'].iloc[-1] / df['close'].iloc[-HORIZON_60D] - 1) if len(df) >= HORIZON_60D else 0

    # Volatility (20-day rolling std of daily returns)
    daily_returns = df['close'].pct_change()
    volatility = daily_returns.tail(HORIZON_20D).std() if len(df) >= HORIZON_20D else 0

    # Simple moving averages
    sma_20 = df['close'].tail(HORIZON_20D).mean() if len(df) >= HORIZON_20D else df['close'].iloc[-1]
    sma_50 = df['close'].tail(HORIZON_50D).mean() if len(df) >= HORIZON_50D else df['close'].iloc[-1]

    # Current price vs SMAs
    price_vs_sma20 = (df['close'].iloc[-1] / sma_20 - 1) if sma_20 > 0 else 0
    price_vs_sma50 = (df['close'].iloc[-1] / sma_50 - 1) if sma_50 > 0 else 0

    # NEW: RSI calculation
    rsi = calculate_rsi(df['close'], period=RSI_DEFAULT_PERIOD)

    # NEW: Bollinger Bands
    bb = calculate_bollinger_bands(df['close'], period=BB_DEFAULT_PERIOD,
                                   num_std=trading_config.bollinger_std_multiplier)

    return {
        "returns_5d": returns_5d,
        "returns_20d": returns_20d,
        "returns_60d": returns_60d,
        "volatility": volatility,
        "price_vs_sma20": price_vs_sma20,
        "price_vs_sma50": price_vs_sma50,
        "current_price": df['close'].iloc[-1],
        "rsi": rsi,
        "bollinger_position": bb['position'],
        "bollinger_upper": bb['upper'],
        "bollinger_lower": bb['lower']
    }


def calculate_regime(features_by_asset: dict) -> float:
    """
    Detect market regime: bullish, neutral, or bearish

    Returns:
        float: Regime score (-1 to +1, positive = bullish)
    """
    regime_scores = []

    for symbol, features in features_by_asset.items():
        # Multi-timeframe momentum
        short_momentum = features.get('returns_5d', 0)
        medium_momentum = features.get('returns_20d', 0)
        long_momentum = features['returns_60d']

        # Trend consistency (all pointing same direction = stronger signal)
        momentum_avg = (short_momentum + medium_momentum + long_momentum) / 3

        # Price vs moving averages
        price_vs_sma20 = features['price_vs_sma20']
        price_vs_sma50 = features['price_vs_sma50']

        # Combine signals using tunable weights
        asset_regime = (
            momentum_avg * trading_config.regime_momentum_weight +
            price_vs_sma20 * trading_config.regime_sma20_weight +
            price_vs_sma50 * trading_config.regime_sma50_weight
        )

        regime_scores.append(asset_regime)

    # Average across all assets
    overall_regime = sum(regime_scores) / len(regime_scores)

    return overall_regime


def calculate_risk_score(features_by_asset: dict) -> float:
    """
    Calculate overall market risk level using tunable weights

    This is a CRITICAL function that drives risk-based allocation decisions.
    All weights are now tunable to allow quantitative optimization.

    Returns:
        float: Risk score (0-100, higher = riskier)
    """
    volatilities = [f['volatility'] for f in features_by_asset.values()]
    avg_vol = sum(volatilities) / len(volatilities)

    # Normalize volatility to 0-100 scale using tunable normalization factor
    vol_score = min(PERCENTAGE_MULTIPLIER, (avg_vol / trading_config.volatility_normalization_factor) * PERCENTAGE_MULTIPLIER)

    # Check for recent stability: if last 5 days have low volatility, reduce risk score
    # This helps system recover faster after market selloffs
    recent_returns = [f.get('returns_5d', 0) for f in features_by_asset.values()]
    recent_stability = 1.0 - min(1.0, np.std(recent_returns) / trading_config.stability_threshold)  # 0 = volatile, 1 = stable

    # Apply stability discount using tunable factor
    vol_score = vol_score * (1.0 - recent_stability * trading_config.stability_discount_factor)

    # Correlation risk: When all assets move together = systemic risk
    momentums = [f['returns_60d'] for f in features_by_asset.values()]
    momentum_std = np.std(momentums)
    correlation_risk = max(0, trading_config.correlation_risk_base - momentum_std * trading_config.correlation_risk_multiplier)

    # Combined risk score using TUNABLE WEIGHTS
    # This is the critical formula that was previously hard-coded as 0.7/0.3
    risk_score = (vol_score * trading_config.risk_volatility_weight +
                  correlation_risk * trading_config.risk_correlation_weight)

    return min(PERCENTAGE_MULTIPLIER, max(0, risk_score))


def rank_assets(features_by_asset: dict) -> dict:
    """
    Rank assets using multiple factors including mean reversion signals

    Returns:
        dict: {symbol: composite_score}
    """
    scores = {}

    for symbol, features in features_by_asset.items():
        # Risk-adjusted momentum (primary factor)
        momentum_score = features['returns_60d'] / max(features['volatility'], DEFAULT_VOLATILITY_DIVISOR)

        # Trend consistency: Are all timeframes aligned?
        short_momentum = features.get('returns_5d', 0)
        medium_momentum = features.get('returns_20d', 0)
        long_momentum = features['returns_60d']

        # Check if all positive or all negative using tunable multipliers
        all_positive = all(m > 0 for m in [short_momentum, medium_momentum, long_momentum])
        all_negative = all(m < 0 for m in [short_momentum, medium_momentum, long_momentum])
        trend_consistency = trading_config.trend_aligned_multiplier if (all_positive or all_negative) else trading_config.trend_mixed_multiplier

        # Price momentum relative to moving averages
        price_momentum = (features['price_vs_sma20'] + features['price_vs_sma50']) / 2

        # Mean reversion bonus using tunable thresholds and bonuses
        rsi = features.get('rsi', RSI_NEUTRAL)
        bb_position = features.get('bollinger_position', 0)

        # Oversold assets get a bonus, overbought get a penalty (all tunable)
        mean_reversion_bonus = 0
        if rsi < trading_config.rsi_oversold_threshold and bb_position < trading_config.bb_oversold_threshold:
            mean_reversion_bonus = trading_config.oversold_strong_bonus  # Strong oversold signal
        elif rsi < trading_config.rsi_mild_oversold and bb_position < trading_config.bb_mild_oversold:
            mean_reversion_bonus = trading_config.oversold_mild_bonus  # Mild oversold
        elif rsi > trading_config.rsi_overbought_threshold and bb_position > trading_config.bb_overbought_threshold:
            mean_reversion_bonus = trading_config.overbought_penalty  # Overbought penalty

        # Composite score
        composite = (
            momentum_score * trading_config.momentum_weight * trend_consistency +
            price_momentum * trading_config.price_momentum_weight +
            mean_reversion_bonus
        )

        scores[symbol] = composite

    return scores


def detect_mean_reversion_opportunity(features_by_asset: dict, regime_score: float) -> tuple:
    """
    Check if there's a mean reversion opportunity in neutral/mild regimes using tunable thresholds

    Returns:
        tuple: (has_opportunity: bool, opportunity_type: str, assets: list)
    """
    # Strong trend - stick with momentum (tunable threshold)
    if abs(regime_score) > trading_config.strong_trend_threshold:
        return (False, None, [])

    oversold_assets = []
    overbought_assets = []

    for symbol, features in features_by_asset.items():
        rsi = features.get('rsi', RSI_NEUTRAL)
        bb_position = features.get('bollinger_position', 0)

        # Check for oversold bounce opportunity using tunable thresholds
        if rsi < trading_config.rsi_oversold_threshold and bb_position < trading_config.bb_oversold_threshold:
            oversold_assets.append(symbol)
        # Check for overbought reversal using tunable thresholds
        elif rsi > trading_config.rsi_overbought_threshold and bb_position > trading_config.bb_overbought_threshold:
            overbought_assets.append(symbol)

    if oversold_assets:
        return (True, 'oversold_bounce', oversold_assets)
    elif overbought_assets:
        return (True, 'overbought_reversal', overbought_assets)

    return (False, None, [])


def detect_downward_pressure(features_by_asset: dict, risk_score: float) -> tuple:
    """
    Detect sustained downward pressure using tunable thresholds

    This helps catch market crashes early before they fully register in regime score.
    All thresholds are now configurable for quantitative optimization.

    Returns:
        tuple: (has_pressure: bool, severity: str, reason: str)
    """
    # Check multiple assets for consistent negative signals
    negative_momentum_count = 0
    below_sma_count = 0
    high_vol_negative_count = 0
    total_assets = len(features_by_asset)

    for symbol, features in features_by_asset.items():
        # Check if all timeframes are negative (sustained downtrend)
        returns_5d = features.get('returns_5d', 0)
        returns_20d = features.get('returns_20d', 0)
        returns_60d = features.get('returns_60d', 0)

        if returns_5d < 0 and returns_20d < 0 and returns_60d < 0:
            negative_momentum_count += 1

        # Check if price is below both key moving averages (tunable threshold)
        price_vs_sma20 = features.get('price_vs_sma20', 0)
        price_vs_sma50 = features.get('price_vs_sma50', 0)

        if price_vs_sma20 < trading_config.price_vs_sma_threshold and price_vs_sma50 < trading_config.price_vs_sma_threshold:
            below_sma_count += 1

        # Check for high volatility + negative short-term momentum (tunable thresholds)
        volatility = features.get('volatility', 0)
        if volatility > trading_config.high_volatility_threshold and returns_5d < trading_config.negative_return_threshold:
            high_vol_negative_count += 1

    # Determine if there's significant downward pressure
    # Require majority of assets showing negative signals (tunable thresholds)
    negative_momentum_pct = negative_momentum_count / total_assets
    below_sma_pct = below_sma_count / total_assets
    high_vol_negative_pct = high_vol_negative_count / total_assets

    # Severe downward pressure using tunable thresholds
    if (negative_momentum_pct >= trading_config.severe_pressure_threshold and below_sma_pct >= trading_config.severe_pressure_threshold) or \
       (high_vol_negative_pct >= trading_config.severe_pressure_threshold and risk_score > trading_config.severe_pressure_risk):
        return (True, "severe", f"Sustained downtrend across {negative_momentum_count}/{total_assets} assets with elevated risk")

    # Moderate downward pressure using tunable thresholds
    elif (negative_momentum_pct >= trading_config.moderate_pressure_threshold and risk_score > trading_config.moderate_pressure_risk) or \
         (below_sma_pct >= trading_config.severe_pressure_threshold and returns_5d < trading_config.price_vs_sma_threshold):
        return (True, "moderate", f"Emerging downward pressure in {negative_momentum_count}/{total_assets} assets")

    return (False, "none", "")


def decide_action(regime_score: float, risk_score: float, has_holdings: bool,
                  mean_reversion_opportunity: tuple, adaptive_bullish_threshold: float,
                  adaptive_bearish_threshold: float, current_drawdown: float,
                  features_by_asset: dict, cash_pct: float = 0.0) -> tuple:
    """
    Decide whether to BUY, SELL, or HOLD with enhanced logic

    Note: Removed circuit breaker - strategy should learn from mistakes, not cease operations

    Args:
        cash_pct: Current percentage of portfolio in cash (0-100)

    Returns:
        tuple: (action: str, allocation_pct: float, signal_type: str)
    """
    has_mr_opportunity, mr_type, mr_assets = mean_reversion_opportunity

    # REMOVED: Circuit breaker logic - strategy must continue operating to learn

    # NEW: Detect downward pressure early to avoid being caught in market crashes
    has_pressure, pressure_severity, pressure_reason = detect_downward_pressure(features_by_asset, risk_score)

    if has_pressure and has_holdings:
        if pressure_severity == "severe":
            # Severe downward pressure - sell aggressively using tunable thresholds
            # Scale down if already heavily defensive to avoid over-selling
            if cash_pct > trading_config.defensive_cash_threshold:
                sell_pct = min(trading_config.sell_percentage * trading_config.sell_defensive_multiplier, trading_config.sell_percentage)
            else:
                sell_pct = min(trading_config.sell_percentage_max, trading_config.sell_percentage * trading_config.sell_aggressive_multiplier)
            return ("SELL", sell_pct, f"downward_pressure_severe")
        elif pressure_severity == "moderate" and regime_score < trading_config.regime_transition_threshold:
            # Moderate pressure in non-bullish regime - reduce exposure unless already very defensive
            if cash_pct > trading_config.defensive_cash_threshold:
                # Already defensive, let normal logic handle it
                pass
            else:
                sell_pct = trading_config.sell_percentage * trading_config.sell_moderate_pressure_multiplier
                return ("SELL", sell_pct, "downward_pressure_moderate")

    # Sell aggressively when risk is VERY HIGH, regardless of regime (tunable threshold)
    if risk_score > trading_config.extreme_risk_threshold and has_holdings:
        # Risk is very high - sell most holdings
        sell_pct = trading_config.sell_percentage
        return ("SELL", sell_pct, "extreme_risk_protection")

    # Bearish regime
    if regime_score < adaptive_bearish_threshold:
        if has_holdings:
            # Scale sell percentage by bearish intensity
            bearish_intensity = abs(regime_score - adaptive_bearish_threshold) / (1.0 - adaptive_bearish_threshold)
            sell_pct = min(trading_config.sell_percentage, trading_config.bearish_sell_base + (bearish_intensity * trading_config.bearish_sell_intensity_multiplier))
            return ("SELL", sell_pct, "bearish_regime")
        else:
            return ("HOLD", 0.0, "bearish_no_holdings")

    # Neutral regime with mean reversion opportunity
    elif adaptive_bearish_threshold <= regime_score <= adaptive_bullish_threshold:
        if has_mr_opportunity and mr_type == 'oversold_bounce' and risk_score < trading_config.mean_reversion_max_risk:
            # Mean reversion buy opportunity (tunable risk threshold)
            allocation_pct = trading_config.mean_reversion_allocation
            return ("BUY", allocation_pct, "mean_reversion_oversold")
        elif risk_score > trading_config.neutral_deleverage_risk and has_holdings:
            # High risk in neutral = SELL some holdings (tunable threshold)
            sell_pct = trading_config.sell_percentage * trading_config.sell_moderate_pressure_multiplier
            return ("SELL", sell_pct, "neutral_high_risk_deleverage")
        elif risk_score > trading_config.neutral_hold_risk:
            # Sit out risky neutral periods (tunable threshold)
            return ("HOLD", 0.0, "neutral_high_risk")
        else:
            # Small cautious buy
            return ("BUY", trading_config.allocation_neutral, "neutral_cautious")

    # Bullish regime
    else:
        # Even in bullish, if risk is very high, SELL instead of buying (tunable threshold)
        if risk_score > trading_config.bullish_excessive_risk and has_holdings:
            # Risk too high even though bullish - reduce exposure
            sell_pct = trading_config.sell_percentage * trading_config.sell_bullish_risk_multiplier
            return ("SELL", sell_pct, "bullish_excessive_risk")
        elif risk_score > trading_config.risk_high_threshold:
            # High risk in bullish - buy less or hold (tunable threshold)
            if has_holdings and risk_score > trading_config.bullish_excessive_risk:
                return ("HOLD", 0.0, "bullish_high_risk_hold")
            else:
                allocation_pct = trading_config.allocation_high_risk
                return ("BUY", allocation_pct, "bullish_high_risk")
        elif risk_score > trading_config.risk_medium_threshold:
            allocation_pct = trading_config.allocation_medium_risk
            return ("BUY", allocation_pct, "bullish_medium_risk")
        else:
            allocation_pct = trading_config.allocation_low_risk
            return ("BUY", allocation_pct, "bullish_momentum")


def allocate_diversified(asset_scores: dict, total_amount: float) -> dict:
    """
    Allocate capital across assets proportionally (not winner-take-all)

    Args:
        asset_scores: {symbol: score}
        total_amount: Total $ to allocate

    Returns:
        dict: {symbol: allocation_amount}
    """
    # Only allocate to assets with positive scores
    positive_scores = {s: max(0, score) for s, score in asset_scores.items()}

    if sum(positive_scores.values()) == 0:
        return {s: 0.0 for s in asset_scores.keys()}

    # Sort by score
    sorted_assets = sorted(positive_scores.items(), key=lambda x: x[1], reverse=True)

    # Proportional allocation with concentration limits
    allocations = {}

    if len(sorted_assets) >= 3 and all(score > 0 for _, score in sorted_assets[:3]):
        # All three are positive - diversify using tunable limits
        total_score = sum(score for _, score in sorted_assets)

        # Normalize scores
        weights = [score / total_score for _, score in sorted_assets]

        # Apply concentration limits using tunable parameters
        allocations[sorted_assets[0][0]] = total_amount * min(trading_config.diversify_top_asset_max, max(trading_config.diversify_top_asset_min, weights[0]))
        allocations[sorted_assets[1][0]] = total_amount * min(trading_config.diversify_second_asset_max, max(trading_config.diversify_second_asset_min, weights[1]))
        allocations[sorted_assets[2][0]] = total_amount * min(trading_config.diversify_third_asset_max, max(trading_config.diversify_third_asset_min, weights[2]))

        # Normalize to exactly total_amount
        total_allocated = sum(allocations.values())
        for symbol in allocations:
            allocations[symbol] = allocations[symbol] * (total_amount / total_allocated)

    elif len(sorted_assets) >= 2 and sorted_assets[1][1] > 0:
        # Only top 2 are positive - use tunable split
        allocations[sorted_assets[0][0]] = total_amount * trading_config.two_asset_top
        allocations[sorted_assets[1][0]] = total_amount * trading_config.two_asset_second
        allocations[sorted_assets[2][0]] = 0.0

    else:
        # Only top 1 is positive
        allocations[sorted_assets[0][0]] = total_amount
        for symbol, _ in sorted_assets[1:]:
            allocations[symbol] = 0.0

    return allocations


def get_previous_regime_score(db: Session, trade_date: date) -> float:
    """Get regime score from the previous trading day's signal"""
    prev_signal = db.query(DailySignal).filter(
        DailySignal.trade_date < trade_date
    ).order_by(DailySignal.trade_date.desc()).first()

    if prev_signal and prev_signal.features_used:
        return prev_signal.features_used.get('regime', None)

    return None


def capital_scaling_adjustment(capital: float) -> float:
    """
    Calculate capital scaling factor using tunable constraints

    This implements the principle that larger capital requires more conservative
    position sizing. All breakpoints and factors are now database-configurable.

    Args:
        capital: Current available capital

    Returns:
        Scaling factor between constraints.capital_scale_max_reduction and 1.0
    """
    tier1_threshold = constraints.capital_scale_tier1_threshold
    tier1_factor = constraints.capital_scale_tier1_factor
    tier2_threshold = constraints.capital_scale_tier2_threshold
    tier2_factor = constraints.capital_scale_tier2_factor
    tier3_threshold = constraints.capital_scale_tier3_threshold
    tier3_factor = constraints.capital_scale_tier3_factor
    max_reduction = constraints.capital_scale_max_reduction

    if capital < tier1_threshold:
        # Small capital: No scaling needed
        return tier1_factor
    elif capital < tier2_threshold:
        # Tier 1 to Tier 2: Gradual reduction
        range_size = tier2_threshold - tier1_threshold
        reduction = tier1_factor - tier2_factor
        return tier1_factor - ((capital - tier1_threshold) / range_size) * reduction
    elif capital < tier3_threshold:
        # Tier 2 to Tier 3: More aggressive reduction
        range_size = tier3_threshold - tier2_threshold
        reduction = tier2_factor - tier3_factor
        return tier2_factor - ((capital - tier2_threshold) / range_size) * reduction
    else:
        # Beyond Tier 3: Conservative asymptotic minimum
        excess_capital = capital - tier3_threshold
        additional_reduction = min(tier3_factor - max_reduction, excess_capital / 2_000_000)
        return max(max_reduction, tier3_factor - additional_reduction)


def calculate_half_kelly(db: Session, trade_date: date, lookback_days: int = HORIZON_60D) -> float:
    """
    Calculate half Kelly allocation based on recent trade performance

    Kelly Criterion: f* = (bp - q) / b
    where:
    - b = payoff ratio (avg_win / avg_loss)
    - p = win probability
    - q = loss probability (1 - p)

    Half Kelly = HALF_KELLY_FACTOR × Kelly for safety margin

    Args:
        db: Database session
        trade_date: Current date
        lookback_days: Days to look back for performance stats

    Returns:
        Half Kelly allocation percentage (0-1), defaults to HALF_KELLY_DEFAULT if insufficient data
    """
    lookback_start = trade_date - timedelta(days=lookback_days)

    # Get recent BUY trades with their outcomes
    trades = db.query(DailySignal).filter(
        DailySignal.trade_date >= lookback_start,
        DailySignal.trade_date < trade_date
    ).all()

    if not trades or len(trades) < constraints.min_trades_for_kelly:
        # Insufficient data - use conservative default
        return HALF_KELLY_DEFAULT

    # Calculate win rate and payoff ratio from signals
    wins = 0
    total_trades = 0
    total_win_return = 0.0
    total_loss_return = 0.0

    for signal in trades:
        features = signal.features_used
        if not features or features.get('action') != 'BUY':
            continue

        total_trades += 1

        # Use signal confidence as a proxy for trade quality
        # In a full implementation, we'd track actual P&L
        confidence = features.get('confidence_score', HALF_KELLY_DEFAULT)

        # Use tunable kelly_confidence_threshold to determine wins
        if confidence > constraints.kelly_confidence_threshold:
            wins += 1
            total_win_return += confidence
        else:
            total_loss_return += (1.0 - confidence)

    if total_trades < constraints.min_trades_for_kelly:
        return HALF_KELLY_DEFAULT

    # Calculate statistics using default constants
    win_rate = wins / total_trades
    avg_win = total_win_return / wins if wins > 0 else DEFAULT_AVG_WIN
    avg_loss = total_loss_return / (total_trades - wins) if (total_trades - wins) > 0 else DEFAULT_AVG_LOSS

    # Avoid division by zero
    if avg_loss == 0:
        avg_loss = DEFAULT_AVG_LOSS

    payoff_ratio = avg_win / avg_loss

    # Kelly formula
    kelly = (win_rate * payoff_ratio - (1 - win_rate)) / payoff_ratio

    # Half Kelly for safety
    half_kelly = kelly * HALF_KELLY_FACTOR

    # Clamp to reasonable range (KELLY_MIN_ALLOCATION to KELLY_MAX_ALLOCATION)
    return max(KELLY_MIN_ALLOCATION, min(KELLY_MAX_ALLOCATION, half_kelly))


def generate_signal(trade_date: date = None):
    """
    Generate allocation signal for the given trade date using enhanced multi-factor model

    Args:
        trade_date: Date to generate signal for (defaults to today)
    """
    if trade_date is None:
        trade_date = date.today()

    db = SessionLocal()

    try:
        print(f"Generating enhanced signal for {trade_date}...\n")

        # Check if signal already exists
        existing = db.query(DailySignal).filter(
            DailySignal.trade_date == trade_date
        ).first()

        if existing:
            print(f"Signal already exists for {trade_date}")
            return

        # Fetch historical data for each asset
        lookback_start = trade_date - timedelta(days=trading_config.lookback_days + 30)

        features_by_asset = {}

        for symbol in trading_config.assets:
            prices = db.query(PriceHistory).filter(
                PriceHistory.symbol == symbol,
                PriceHistory.date < trade_date,
                PriceHistory.date >= lookback_start
            ).order_by(PriceHistory.date.asc()).all()

            # Use tunable min_data_days constraint
            if len(prices) < constraints.min_data_days:
                print(f"WARNING: Insufficient data for {symbol} ({len(prices)} days, need {constraints.min_data_days})")
                continue

            # Convert to DataFrame
            df = pd.DataFrame([
                {
                    'date': p.date,
                    'close': p.close_price,
                    'open': p.open_price,
                    'high': p.high_price,
                    'low': p.low_price,
                    'volume': p.volume
                }
                for p in prices
            ])

            # Calculate features with multiple timeframes
            features = calculate_multi_timeframe_features(df)
            features_by_asset[symbol] = features

            print(f"{symbol}:")
            print(f"  Price: ${features['current_price']:.2f}")
            print(f"  5d: {features['returns_5d']*100:+.2f}% | 20d: {features['returns_20d']*100:+.2f}% | 60d: {features['returns_60d']*100:+.2f}%")
            print(f"  Volatility: {features['volatility']*100:.2f}%")
            print(f"  RSI: {features['rsi']:.1f} | BB Position: {features['bollinger_position']:.2f}")

        if not features_by_asset:
            error_msg = f"ERROR: No data available for any assets on {trade_date}. Need at least 60 days of price history."
            print(error_msg)
            raise ValueError(error_msg)

        # Step 1: Detect market regime
        regime_score = calculate_regime(features_by_asset)

        # Step 2: Calculate adaptive thresholds based on current volatility
        avg_volatility = sum(f['volatility'] for f in features_by_asset.values()) / len(features_by_asset)
        adaptive_bullish_threshold = calculate_adaptive_threshold(
            trading_config.regime_bullish_threshold,
            avg_volatility,
            trading_config.base_volatility,
            trading_config.volatility_adjustment_factor
        )
        adaptive_bearish_threshold = calculate_adaptive_threshold(
            trading_config.regime_bearish_threshold,
            avg_volatility,
            trading_config.base_volatility,
            trading_config.volatility_adjustment_factor
        )

        regime_label = "BULLISH" if regime_score > adaptive_bullish_threshold else "BEARISH" if regime_score < adaptive_bearish_threshold else "NEUTRAL"
        print(f"\nMarket Regime: {regime_label} (score: {regime_score:.3f})")
        print(f"  Adaptive Thresholds: Bullish>{adaptive_bullish_threshold:.3f}, Bearish<{adaptive_bearish_threshold:.3f}")

        # Step 3: Detect regime transition
        prev_regime_score = get_previous_regime_score(db, trade_date)
        regime_transition = detect_regime_transition(regime_score, prev_regime_score)
        print(f"  Regime Transition: {regime_transition}")

        # Step 4: Calculate risk level
        risk_score = calculate_risk_score(features_by_asset)
        # Use tunable risk label thresholds
        risk_label = "HIGH" if risk_score > trading_config.risk_label_high_threshold else \
                     "MEDIUM" if risk_score > trading_config.risk_label_medium_threshold else "LOW"
        print(f"Risk Level: {risk_label} ({risk_score:.1f}/100)")

        # Step 5: Monitor drawdown (warning only - DO NOT stop operations)
        _, current_dd = check_circuit_breaker(
            db, trade_date, trading_config.intramonth_drawdown_limit
        )
        if current_dd > trading_config.intramonth_drawdown_limit:
            print(f"  ⚠️  WARNING: Intra-month drawdown {current_dd*100:.1f}% exceeds {trading_config.intramonth_drawdown_limit*100:.0f}% - continuing operations")

        # Step 6: Rank assets
        asset_scores = rank_assets(features_by_asset)
        print(f"\nAsset Rankings:")
        for symbol, score in sorted(asset_scores.items(), key=lambda x: x[1], reverse=True):
            rsi = features_by_asset[symbol]['rsi']
            bb_pos = features_by_asset[symbol]['bollinger_position']
            print(f"  {symbol}: {score:.4f} (RSI:{rsi:.1f}, BB:{bb_pos:+.2f})")

        # Step 7: Check for mean reversion opportunity
        mean_reversion_opportunity = detect_mean_reversion_opportunity(features_by_asset, regime_score)
        if mean_reversion_opportunity[0]:
            print(f"\nMean Reversion: {mean_reversion_opportunity[1]} in {mean_reversion_opportunity[2]}")

        # NEW: Step 7b: Check for downward pressure
        has_pressure, pressure_severity, pressure_reason = detect_downward_pressure(features_by_asset, risk_score)
        if has_pressure:
            print(f"\n⚠️  Downward Pressure Detected: {pressure_severity.upper()}")
            print(f"   Reason: {pressure_reason}")

        # Step 8: Check current holdings and portfolio allocation
        holdings = db.query(Portfolio).filter(Portfolio.quantity > 0).all()
        has_holdings = len(holdings) > 0

        # Calculate current allocation: what % is in positions vs cash
        cash_row = db.query(Portfolio).filter(Portfolio.symbol == 'CASH').first()
        cash_balance = float(cash_row.quantity) if cash_row else 0.0

        # Get latest prices to value holdings
        holdings_value = 0.0
        for holding in holdings:
            latest_price = db.query(PriceHistory).filter(
                PriceHistory.symbol == holding.symbol,
                PriceHistory.date < trade_date
            ).order_by(PriceHistory.date.desc()).first()
            if latest_price:
                holdings_value += float(holding.quantity) * float(latest_price.close_price)

        total_portfolio = cash_balance + holdings_value
        cash_pct = (cash_balance / total_portfolio * 100) if total_portfolio > 0 else 0
        holdings_pct = (holdings_value / total_portfolio * 100) if total_portfolio > 0 else 0

        print(f"\nCurrent Holdings: {len(holdings)} positions")
        print(f"Portfolio Allocation: {holdings_pct:.1f}% positions, {cash_pct:.1f}% cash (${cash_balance:,.0f})")

        # Step 9: Decide action with enhanced logic (now aware of current allocation)
        action, allocation_pct, signal_type = decide_action(
            regime_score, risk_score, has_holdings,
            mean_reversion_opportunity,
            adaptive_bullish_threshold, adaptive_bearish_threshold,
            current_dd, features_by_asset, cash_pct
        )
        print(f"\nDecision: {action} (allocation: {allocation_pct*100:.0f}%, type: {signal_type})")

        # Step 10: Calculate confidence score
        trend_consistency = max(
            1.5 if all(
                m > 0 for m in [f.get('returns_5d', 0), f.get('returns_20d', 0), f['returns_60d']]
            ) else 1.0
            for f in features_by_asset.values()
        )
        is_mean_reversion = signal_type.startswith('mean_reversion')
        confidence = calculate_confidence_score(regime_score, risk_score, trend_consistency, is_mean_reversion)

        # Use tunable min_holding_threshold from constraints
        # If holdings are below threshold, force buying to reach minimum

        # Apply confidence-based position sizing
        if action == "BUY":
            if confidence >= trading_config.min_confidence_threshold:
                adjusted_allocation = calculate_position_size(
                    allocation_pct,
                    confidence,
                    trading_config.confidence_scaling_factor
                )
                print(f"Confidence: {confidence:.2f} | Adjusted Allocation: {adjusted_allocation*100:.0f}%")
            else:
                if holdings_pct >= constraints.min_holding_threshold:
                    adjusted_allocation = 0.0
                    action = "HOLD"
                    signal_type = "low_confidence_skip"
                    print(f"Confidence: {confidence:.2f} < {trading_config.min_confidence_threshold:.2f} - SKIPPING")
                # Force Action if holding_pct is smaller than threshold (tunable)
                else:
                    adjusted_allocation = constraints.min_holding_threshold - holdings_pct
        elif action == "SELL":
            adjusted_allocation = allocation_pct
        else:
            if holdings_pct < constraints.min_holding_threshold:
                action = "BUY"
                adjusted_allocation = constraints.min_holding_threshold - holdings_pct
            else:
                adjusted_allocation = allocation_pct

        # Determine confidence bucket for tracking using tunable thresholds
        if confidence >= trading_config.confidence_bucket_high_threshold:
            confidence_bucket = "high"
        elif confidence >= trading_config.confidence_bucket_medium_threshold:
            confidence_bucket = "medium"
        else:
            confidence_bucket = "low"

        # Step 11: Generate allocations based on action
        allocations = {}
        action_type = action

        # Initialize capital scaling variables for tracking
        capital_scale_factor = 1.0
        half_kelly_pct = 0.0
        final_allocation_pct = adjusted_allocation

        if action == "BUY":
            # CRITICAL FIX: Use accumulated cash + today's capital for buying
            # This ensures we deploy cash reserves built up during defensive selling
            available_cash = cash_balance + trading_config.daily_capital

            # NEW: Apply capital scaling to reduce allocation % for large capital
            # This implements half Kelly × capital scaling factor
            capital_scale_factor = capital_scaling_adjustment(available_cash)

            # Calculate half Kelly (if sufficient data available)
            half_kelly_pct = calculate_half_kelly(db, trade_date)

            # Base allocation from strategy (regime-based decision)
            base_allocation = adjusted_allocation

            # Apply scaling: min(base_allocation, half_kelly) × capital_factor
            # This ensures we never exceed either the strategy allocation or half Kelly
            kelly_limited_allocation = min(base_allocation, half_kelly_pct)
            final_allocation = kelly_limited_allocation * capital_scale_factor
            final_allocation_pct = final_allocation  # Store for metadata

            # Only proceed with BUY if not converted to HOLD
            if action == "BUY" and final_allocation > 0:
                # Deploy capital with scaled allocation
                buy_amount = available_cash * final_allocation
                allocations = allocate_diversified(asset_scores, buy_amount)

                print(f"\nBuy Allocations:")
                print(f"  Available Cash: ${available_cash:,.2f} (accumulated: ${cash_balance:,.2f} + daily: ${trading_config.daily_capital:,.2f})")
                print(f"  Base Strategy Allocation: {base_allocation*100:.1f}%")
                print(f"  Half Kelly Limit: {half_kelly_pct*100:.1f}%")
                print(f"  Kelly-Limited Allocation: {kelly_limited_allocation*100:.1f}%")
                print(f"  Capital Scale Factor: {capital_scale_factor:.3f} (capital: ${available_cash:,.0f})")
                print(f"  → Final Allocation: {final_allocation*100:.1f}% = ${buy_amount:,.2f}")

                for symbol, amount in sorted(allocations.items(), key=lambda x: x[1], reverse=True):
                    if amount > 0:
                        print(f"    {symbol}: ${amount:,.2f} ({amount/buy_amount*100:.1f}%)")

                cash_kept = available_cash - buy_amount
                if cash_kept > 0:
                    print(f"  Cash Reserve: ${cash_kept:,.2f}")

        elif action == "SELL":
            if has_holdings and holdings_pct >= constraints.min_holding_threshold:
                holding_scores = {h.symbol: asset_scores.get(h.symbol, -999) for h in holdings}
                sorted_holdings = sorted(holding_scores.items(), key=lambda x: x[1])

                print(f"\nSell Signals (sell {adjusted_allocation*100:.0f}% of weakest):")
                for symbol, score in sorted_holdings:
                    allocations[symbol] = -adjusted_allocation
                    print(f"  SELL {adjusted_allocation*100:.0f}% of {symbol} (score: {score:.4f})")
            else:
                allocations = {s: 0.0 for s in trading_config.assets}

        else:  # HOLD
            allocations = {s: 0.0 for s in trading_config.assets}
            available_cash = cash_balance + trading_config.daily_capital
            print(f"\nHolding cash: ${available_cash:,.2f} (accumulated: ${cash_balance:,.2f} + daily: ${trading_config.daily_capital:,.2f})")

        # Store signal with enhanced metadata
        signal = DailySignal(
            trade_date=trade_date,
            allocations=allocations,
            model_type="enhanced_regime_based",
            confidence_score=float(confidence),
            features_used={
                "regime": float(regime_score),
                "risk": float(risk_score),
                "action": action_type,
                "signal_type": signal_type,
                "allocation_pct": float(adjusted_allocation),
                "final_allocation_pct": float(final_allocation_pct),  # NEW: Capital-scaled allocation
                "capital_scale_factor": float(capital_scale_factor),  # NEW: Scaling factor applied
                "half_kelly_pct": float(half_kelly_pct),  # NEW: Half Kelly percentage
                "available_cash": float(cash_balance + trading_config.daily_capital),  # NEW: Available capital
                "confidence_bucket": confidence_bucket,
                "adaptive_bullish_threshold": float(adaptive_bullish_threshold),
                "adaptive_bearish_threshold": float(adaptive_bearish_threshold),
                "regime_transition": regime_transition,
                "intramonth_drawdown": float(current_dd),
                "mean_reversion_opportunity": mean_reversion_opportunity[0],
                "avg_volatility": float(avg_volatility),
                "assets": {
                    symbol: {
                        "returns_5d": float(f["returns_5d"]),
                        "returns_20d": float(f["returns_20d"]),
                        "returns_60d": float(f["returns_60d"]),
                        "volatility": float(f["volatility"]),
                        "score": float(asset_scores.get(symbol, 0)),
                        "rsi": float(f["rsi"]),
                        "bollinger_position": float(f["bollinger_position"])
                    }
                    for symbol, f in features_by_asset.items()
                }
            }
        )

        db.add(signal)
        db.commit()

        print(f"\n✓ Enhanced signal generated and stored for {trade_date}")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate enhanced allocation signal")
    parser.add_argument("--date", type=str, help="Date to generate signal for (YYYY-MM-DD)")

    args = parser.parse_args()

    if args.date:
        target = datetime.strptime(args.date, "%Y-%m-%d").date()
        generate_signal(target)
    else:
        generate_signal()
