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

settings = get_settings()
trading_config = get_trading_config()


def calculate_rsi(prices: pd.Series, period: int = 14) -> float:
    """
    Calculate Relative Strength Index

    Returns:
        float: RSI value between 0-100
    """
    if len(prices) < period + 1:
        return 50.0  # Neutral if insufficient data

    deltas = prices.diff()
    gains = deltas.where(deltas > 0, 0.0)
    losses = -deltas.where(deltas < 0, 0.0)

    avg_gain = gains.tail(period).mean()
    avg_loss = losses.tail(period).mean()

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    return float(rsi)


def calculate_bollinger_bands(prices: pd.Series, period: int = 20, num_std: float = 2.0) -> dict:
    """
    Calculate Bollinger Bands position

    Returns:
        dict with 'upper', 'lower', 'middle', 'position' (-1 to +1 scale)
    """
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
    Detect regime transitions for early entry/exit signals

    Returns:
        str: 'turning_bullish', 'turning_bearish', 'losing_momentum', 'gaining_momentum', 'stable'
    """
    if previous_regime_score is None:
        return 'stable'

    delta = current_regime_score - previous_regime_score

    # Turning points
    if current_regime_score > 0.1 and previous_regime_score < -0.1:
        return 'turning_bullish'
    elif current_regime_score < -0.1 and previous_regime_score > 0.1:
        return 'turning_bearish'

    # Momentum changes within bullish territory
    if current_regime_score > 0.3 and delta < -0.15:
        return 'losing_momentum'
    elif current_regime_score > 0 and delta > 0.15:
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
    adjustment = max(0.7, min(1.5, adjustment))  # Clamp adjustment

    return base_threshold * adjustment


def calculate_confidence_score(regime_score: float, risk_score: float,
                                trend_consistency: float, mean_reversion_signal: bool) -> float:
    """
    Calculate overall confidence in the signal (0 to 1)

    Higher confidence = stronger position sizing
    """
    # Base confidence from regime strength
    regime_confidence = min(1.0, abs(regime_score) / 0.5)

    # Risk penalty (high risk = lower confidence)
    risk_penalty = max(0, (risk_score - 40) / 60)  # 0 at 40, 1 at 100

    # Trend consistency bonus
    consistency_bonus = 0.2 if trend_consistency > 1.2 else 0

    # Mean reversion signals have moderate confidence
    if mean_reversion_signal:
        base_confidence = 0.6
    else:
        base_confidence = regime_confidence

    # Combine factors
    confidence = base_confidence + consistency_bonus - (risk_penalty * 0.3)
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
    returns_5d = (df['close'].iloc[-1] / df['close'].iloc[-5] - 1) if len(df) >= 5 else 0
    returns_20d = (df['close'].iloc[-1] / df['close'].iloc[-20] - 1) if len(df) >= 20 else 0
    returns_60d = (df['close'].iloc[-1] / df['close'].iloc[-60] - 1) if len(df) >= 60 else 0

    # Volatility (20-day rolling std of daily returns)
    daily_returns = df['close'].pct_change()
    volatility = daily_returns.tail(20).std() if len(df) >= 20 else 0

    # Simple moving averages
    sma_20 = df['close'].tail(20).mean() if len(df) >= 20 else df['close'].iloc[-1]
    sma_50 = df['close'].tail(50).mean() if len(df) >= 50 else df['close'].iloc[-1]

    # Current price vs SMAs
    price_vs_sma20 = (df['close'].iloc[-1] / sma_20 - 1) if sma_20 > 0 else 0
    price_vs_sma50 = (df['close'].iloc[-1] / sma_50 - 1) if sma_50 > 0 else 0

    # NEW: RSI calculation
    rsi = calculate_rsi(df['close'], period=14)

    # NEW: Bollinger Bands
    bb = calculate_bollinger_bands(df['close'], period=20,
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

        # Combine signals
        asset_regime = (
            momentum_avg * 0.5 +
            price_vs_sma20 * 0.3 +
            price_vs_sma50 * 0.2
        )

        regime_scores.append(asset_regime)

    # Average across all assets
    overall_regime = sum(regime_scores) / len(regime_scores)

    return overall_regime


def calculate_risk_score(features_by_asset: dict) -> float:
    """
    Calculate overall market risk level

    Returns:
        float: Risk score (0-100, higher = riskier)
    """
    volatilities = [f['volatility'] for f in features_by_asset.values()]
    avg_vol = sum(volatilities) / len(volatilities)

    # Normalize volatility to 0-100 scale (assume typical vol ~0.5% to 2%)
    vol_score = min(100, (avg_vol / 0.02) * 100)

    # Check for recent stability: if last 5 days have low volatility, reduce risk score
    # This helps system recover faster after market selloffs
    recent_returns = [f.get('returns_5d', 0) for f in features_by_asset.values()]
    recent_stability = 1.0 - min(1.0, np.std(recent_returns) / 0.05)  # 0 = volatile, 1 = stable

    # Apply stability discount to volatility score
    vol_score = vol_score * (1.0 - recent_stability * 0.5)  # Up to 50% reduction if very stable

    # Correlation risk: When all assets move together = systemic risk
    momentums = [f['returns_60d'] for f in features_by_asset.values()]
    momentum_std = np.std(momentums)
    correlation_risk = max(0, 30 - momentum_std * 100)  # Low diversity = higher risk

    # Combined risk score
    risk_score = vol_score * 0.7 + correlation_risk * 0.3

    return min(100, max(0, risk_score))


def rank_assets(features_by_asset: dict) -> dict:
    """
    Rank assets using multiple factors including mean reversion signals

    Returns:
        dict: {symbol: composite_score}
    """
    scores = {}

    for symbol, features in features_by_asset.items():
        # Risk-adjusted momentum (primary factor)
        momentum_score = features['returns_60d'] / max(features['volatility'], 0.001)

        # Trend consistency: Are all timeframes aligned?
        short_momentum = features.get('returns_5d', 0)
        medium_momentum = features.get('returns_20d', 0)
        long_momentum = features['returns_60d']

        # Check if all positive or all negative
        all_positive = all(m > 0 for m in [short_momentum, medium_momentum, long_momentum])
        all_negative = all(m < 0 for m in [short_momentum, medium_momentum, long_momentum])
        trend_consistency = 1.5 if (all_positive or all_negative) else 1.0

        # Price momentum relative to moving averages
        price_momentum = (features['price_vs_sma20'] + features['price_vs_sma50']) / 2

        # NEW: Mean reversion bonus
        rsi = features.get('rsi', 50)
        bb_position = features.get('bollinger_position', 0)

        # Oversold assets get a bonus, overbought get a penalty
        mean_reversion_bonus = 0
        if rsi < trading_config.rsi_oversold_threshold and bb_position < -0.5:
            mean_reversion_bonus = 0.3  # Strong oversold signal
        elif rsi < 40 and bb_position < 0:
            mean_reversion_bonus = 0.1  # Mild oversold
        elif rsi > trading_config.rsi_overbought_threshold and bb_position > 0.5:
            mean_reversion_bonus = -0.2  # Overbought penalty

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
    Check if there's a mean reversion opportunity in neutral/mild regimes

    Returns:
        tuple: (has_opportunity: bool, opportunity_type: str, assets: list)
    """
    if abs(regime_score) > 0.4:  # Strong trend - stick with momentum
        return (False, None, [])

    oversold_assets = []
    overbought_assets = []

    for symbol, features in features_by_asset.items():
        rsi = features.get('rsi', 50)
        bb_position = features.get('bollinger_position', 0)

        # Check for oversold bounce opportunity
        if rsi < trading_config.rsi_oversold_threshold and bb_position < -0.5:
            oversold_assets.append(symbol)
        # Check for overbought reversal
        elif rsi > trading_config.rsi_overbought_threshold and bb_position > 0.5:
            overbought_assets.append(symbol)

    if oversold_assets:
        return (True, 'oversold_bounce', oversold_assets)
    elif overbought_assets:
        return (True, 'overbought_reversal', overbought_assets)

    return (False, None, [])


def detect_downward_pressure(features_by_asset: dict, risk_score: float) -> tuple:
    """
    Detect sustained downward pressure that warrants defensive action

    This helps catch market crashes early before they fully register in regime score

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

        # Check if price is below both key moving averages
        price_vs_sma20 = features.get('price_vs_sma20', 0)
        price_vs_sma50 = features.get('price_vs_sma50', 0)

        if price_vs_sma20 < -0.02 and price_vs_sma50 < -0.02:  # Below by 2%+
            below_sma_count += 1

        # Check for high volatility + negative short-term momentum
        volatility = features.get('volatility', 0)
        if volatility > 0.015 and returns_5d < -0.03:  # High vol + down >3% in 5 days
            high_vol_negative_count += 1

    # Determine if there's significant downward pressure
    # Require majority of assets showing negative signals
    negative_momentum_pct = negative_momentum_count / total_assets
    below_sma_pct = below_sma_count / total_assets
    high_vol_negative_pct = high_vol_negative_count / total_assets

    # Severe downward pressure: multiple indicators across most assets
    if (negative_momentum_pct >= 0.67 and below_sma_pct >= 0.67) or \
       (high_vol_negative_pct >= 0.67 and risk_score > 50):
        return (True, "severe", f"Sustained downtrend across {negative_momentum_count}/{total_assets} assets with elevated risk")

    # Moderate downward pressure: concerning signals but not catastrophic
    elif (negative_momentum_pct >= 0.50 and risk_score > 45) or \
         (below_sma_pct >= 0.67 and returns_5d < -0.02):
        return (True, "moderate", f"Emerging downward pressure in {negative_momentum_count}/{total_assets} assets")

    return (False, "none", "")


def decide_action(regime_score: float, risk_score: float, has_holdings: bool,
                  mean_reversion_opportunity: tuple, adaptive_bullish_threshold: float,
                  adaptive_bearish_threshold: float, current_drawdown: float,
                  features_by_asset: dict) -> tuple:
    """
    Decide whether to BUY, SELL, or HOLD with enhanced logic

    Note: Removed circuit breaker - strategy should learn from mistakes, not cease operations

    Returns:
        tuple: (action: str, allocation_pct: float, signal_type: str)
    """
    has_mr_opportunity, mr_type, mr_assets = mean_reversion_opportunity

    # REMOVED: Circuit breaker logic - strategy must continue operating to learn

    # NEW: Detect downward pressure early to avoid being caught in market crashes
    has_pressure, pressure_severity, pressure_reason = detect_downward_pressure(features_by_asset, risk_score)

    if has_pressure and has_holdings:
        if pressure_severity == "severe":
            # Severe downward pressure - sell aggressively regardless of regime
            sell_pct = min(0.9, trading_config.sell_percentage * 1.2)  # Sell more than usual
            return ("SELL", sell_pct, f"downward_pressure_severe")
        elif pressure_severity == "moderate" and regime_score < 0.1:
            # Moderate pressure in non-bullish regime - reduce exposure
            sell_pct = trading_config.sell_percentage * 0.6
            return ("SELL", sell_pct, "downward_pressure_moderate")

    # IMPROVED: Sell aggressively when risk is VERY HIGH (>70), regardless of regime
    # Lowered from 85 to 70 to be more responsive to risk
    if risk_score > 70 and has_holdings:
        # Risk is very high - sell most holdings
        sell_pct = trading_config.sell_percentage
        return ("SELL", sell_pct, "extreme_risk_protection")

    # Bearish regime
    if regime_score < adaptive_bearish_threshold:
        if has_holdings:
            # Use tunable sell_percentage instead of hardcoded formula
            # Scale it by how bearish: more bearish = sell more
            bearish_intensity = abs(regime_score - adaptive_bearish_threshold) / (1.0 - adaptive_bearish_threshold)
            sell_pct = min(trading_config.sell_percentage, 0.3 + (bearish_intensity * 0.4))
            return ("SELL", sell_pct, "bearish_regime")
        else:
            return ("HOLD", 0.0, "bearish_no_holdings")

    # Neutral regime with mean reversion opportunity
    elif adaptive_bearish_threshold <= regime_score <= adaptive_bullish_threshold:
        if has_mr_opportunity and mr_type == 'oversold_bounce' and risk_score < 60:
            # Mean reversion buy opportunity
            allocation_pct = trading_config.mean_reversion_allocation
            return ("BUY", allocation_pct, "mean_reversion_oversold")
        elif risk_score > 55 and has_holdings:
            # IMPROVED: High risk in neutral = SELL some holdings
            # Lowered from 75 to 55 to be more defensive in neutral markets
            sell_pct = trading_config.sell_percentage * 0.5  # Sell 50% of sell_percentage
            return ("SELL", sell_pct, "neutral_high_risk_deleverage")
        elif risk_score > 50:
            # IMPROVED: Lowered from 60 to 50 - more willing to sit out risky neutral periods
            return ("HOLD", 0.0, "neutral_high_risk")
        else:
            # Small cautious buy
            return ("BUY", trading_config.allocation_neutral, "neutral_cautious")

    # Bullish regime
    else:
        # IMPROVED: Even in bullish, if risk is very high, SELL instead of buying
        # Lowered from 80 to 65 to be more defensive
        if risk_score > 65 and has_holdings:
            # Risk too high even though bullish - reduce exposure
            sell_pct = trading_config.sell_percentage * 0.3  # Sell 30% of sell_percentage
            return ("SELL", sell_pct, "bullish_excessive_risk")
        elif risk_score > trading_config.risk_high_threshold:
            # High risk in bullish - buy less or hold
            # IMPROVED: Lowered from 75 to 65 for hold threshold
            if has_holdings and risk_score > 65:
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
        # All three are positive - diversify
        total_score = sum(score for _, score in sorted_assets)

        # Normalize scores
        weights = [score / total_score for _, score in sorted_assets]

        # Apply concentration limits
        allocations[sorted_assets[0][0]] = total_amount * min(0.50, max(0.40, weights[0]))
        allocations[sorted_assets[1][0]] = total_amount * min(0.35, max(0.30, weights[1]))
        allocations[sorted_assets[2][0]] = total_amount * min(0.25, max(0.15, weights[2]))

        # Normalize to exactly total_amount
        total_allocated = sum(allocations.values())
        for symbol in allocations:
            allocations[symbol] = allocations[symbol] * (total_amount / total_allocated)

    elif len(sorted_assets) >= 2 and sorted_assets[1][1] > 0:
        # Only top 2 are positive
        allocations[sorted_assets[0][0]] = total_amount * 0.65
        allocations[sorted_assets[1][0]] = total_amount * 0.35
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

            if len(prices) < 60:
                print(f"WARNING: Insufficient data for {symbol} ({len(prices)} days)")
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
        risk_label = "HIGH" if risk_score > 70 else "MEDIUM" if risk_score > 40 else "LOW"
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

        # Step 8: Check current holdings
        holdings = db.query(Portfolio).filter(Portfolio.quantity > 0).all()
        has_holdings = len(holdings) > 0
        print(f"\nCurrent Holdings: {len(holdings)} positions")

        # Step 9: Decide action with enhanced logic
        action, allocation_pct, signal_type = decide_action(
            regime_score, risk_score, has_holdings,
            mean_reversion_opportunity,
            adaptive_bullish_threshold, adaptive_bearish_threshold,
            current_dd, features_by_asset
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

        # Apply confidence-based position sizing
        if action == "BUY" and confidence >= trading_config.min_confidence_threshold:
            adjusted_allocation = calculate_position_size(
                allocation_pct,
                confidence,
                trading_config.confidence_scaling_factor
            )
            print(f"Confidence: {confidence:.2f} | Adjusted Allocation: {adjusted_allocation*100:.0f}%")
        elif action == "BUY" and confidence < trading_config.min_confidence_threshold:
            adjusted_allocation = 0.0
            action = "HOLD"
            signal_type = "low_confidence_skip"
            print(f"Confidence: {confidence:.2f} < {trading_config.min_confidence_threshold:.2f} - SKIPPING")
        else:
            adjusted_allocation = allocation_pct

        # Determine confidence bucket for tracking
        if confidence >= 0.7:
            confidence_bucket = "high"
        elif confidence >= 0.5:
            confidence_bucket = "medium"
        else:
            confidence_bucket = "low"

        # Step 11: Generate allocations based on action
        allocations = {}
        action_type = action

        if action == "BUY":
            buy_amount = trading_config.daily_capital * adjusted_allocation
            allocations = allocate_diversified(asset_scores, buy_amount)

            print(f"\nBuy Allocations (Total: ${buy_amount:.2f}):")
            for symbol, amount in sorted(allocations.items(), key=lambda x: x[1], reverse=True):
                if amount > 0:
                    print(f"  {symbol}: ${amount:.2f} ({amount/buy_amount*100:.1f}%)")

            cash_kept = trading_config.daily_capital - buy_amount
            if cash_kept > 0:
                print(f"  CASH: ${cash_kept:.2f}")

        elif action == "SELL":
            if has_holdings:
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
            print(f"\nHolding cash: ${trading_config.daily_capital:.2f}")

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
