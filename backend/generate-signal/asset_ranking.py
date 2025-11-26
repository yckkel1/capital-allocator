"""
Asset Ranking Module
Functions for scoring and ranking assets
"""
from constants import DEFAULT_VOLATILITY_DIVISOR


def rank_assets(features_by_asset: dict, config) -> dict:
    """Rank assets using multiple factors including mean reversion signals"""
    scores = {}

    for symbol, features in features_by_asset.items():
        momentum_score = features['returns_60d'] / max(features['volatility'], DEFAULT_VOLATILITY_DIVISOR)

        short_momentum = features.get('returns_5d', 0)
        medium_momentum = features.get('returns_20d', 0)
        long_momentum = features['returns_60d']

        all_positive = all(m > 0 for m in [short_momentum, medium_momentum, long_momentum])
        all_negative = all(m < 0 for m in [short_momentum, medium_momentum, long_momentum])
        trend_consistency = config.trend_aligned_multiplier if (all_positive or all_negative) else config.trend_mixed_multiplier

        price_momentum = (features['price_vs_sma20'] + features['price_vs_sma50']) / 2

        # Mean reversion bonus
        rsi = features.get('rsi', 50.0)
        bb_position = features.get('bollinger_position', 0)

        mean_reversion_bonus = 0
        if rsi < config.rsi_oversold_threshold and bb_position < config.bb_oversold_threshold:
            mean_reversion_bonus = config.oversold_strong_bonus
        elif rsi < config.rsi_mild_oversold and bb_position < config.bb_mild_oversold:
            mean_reversion_bonus = config.oversold_mild_bonus
        elif rsi > config.rsi_overbought_threshold and bb_position > config.bb_overbought_threshold:
            mean_reversion_bonus = config.overbought_penalty

        composite = (
            momentum_score * config.momentum_weight * trend_consistency +
            price_momentum * config.price_momentum_weight +
            mean_reversion_bonus
        )

        scores[symbol] = composite

    return scores
