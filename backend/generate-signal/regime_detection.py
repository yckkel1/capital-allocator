"""
Regime Detection Module
Functions for detecting market regimes and transitions
"""


def detect_regime_transition(current_regime_score: float, previous_regime_score: float,
                             config) -> str:
    """Detect regime transitions for early entry/exit signals"""
    if previous_regime_score is None:
        return 'stable'

    delta = current_regime_score - previous_regime_score

    # Turning points
    threshold = config.regime_transition_threshold
    if current_regime_score > threshold and previous_regime_score < -threshold:
        return 'turning_bullish'
    elif current_regime_score < -threshold and previous_regime_score > threshold:
        return 'turning_bearish'

    # Momentum changes within bullish territory
    if current_regime_score > config.regime_bullish_threshold and delta < config.momentum_loss_threshold:
        return 'losing_momentum'
    elif current_regime_score > 0 and delta > config.momentum_gain_threshold:
        return 'gaining_momentum'

    return 'stable'


def calculate_adaptive_threshold(base_threshold: float, current_volatility: float,
                                 base_volatility: float, adjustment_factor: float,
                                 config) -> float:
    """Adjust regime threshold based on current volatility"""
    vol_ratio = current_volatility / base_volatility if base_volatility > 0 else 1.0
    adjustment = 1.0 + (adjustment_factor * (vol_ratio - 1.0))
    adjustment = max(config.adaptive_threshold_clamp_min,
                    min(config.adaptive_threshold_clamp_max, adjustment))

    return base_threshold * adjustment


def calculate_regime(features_by_asset: dict, config) -> float:
    """Detect market regime: bullish, neutral, or bearish"""
    regime_scores = []

    for symbol, features in features_by_asset.items():
        short_momentum = features.get('returns_5d', 0)
        medium_momentum = features.get('returns_20d', 0)
        long_momentum = features['returns_60d']

        momentum_avg = (short_momentum + medium_momentum + long_momentum) / 3

        price_vs_sma20 = features['price_vs_sma20']
        price_vs_sma50 = features['price_vs_sma50']

        asset_regime = (
            momentum_avg * config.regime_momentum_weight +
            price_vs_sma20 * config.regime_sma20_weight +
            price_vs_sma50 * config.regime_sma50_weight
        )

        regime_scores.append(asset_regime)

    overall_regime = sum(regime_scores) / len(regime_scores)

    return overall_regime
