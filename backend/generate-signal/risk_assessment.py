"""
Risk Assessment Module
Functions for calculating risk scores and confidence levels
"""
import numpy as np
from .constants import PERCENTAGE_MULTIPLIER


def calculate_risk_score(features_by_asset: dict, config) -> float:
    """Calculate overall market risk level"""
    volatilities = [f['volatility'] for f in features_by_asset.values()]
    avg_vol = sum(volatilities) / len(volatilities)

    vol_score = min(PERCENTAGE_MULTIPLIER, 
                   (avg_vol / config.volatility_normalization_factor) * PERCENTAGE_MULTIPLIER)

    recent_returns = [f.get('returns_5d', 0) for f in features_by_asset.values()]
    recent_stability = 1.0 - min(1.0, np.std(recent_returns) / config.stability_threshold)

    vol_score = vol_score * (1.0 - recent_stability * config.stability_discount_factor)

    momentums = [f['returns_60d'] for f in features_by_asset.values()]
    momentum_std = np.std(momentums)
    correlation_risk = max(0, config.correlation_risk_base - momentum_std * config.correlation_risk_multiplier)

    risk_score = (vol_score * config.risk_volatility_weight +
                 correlation_risk * config.risk_correlation_weight)

    return min(PERCENTAGE_MULTIPLIER, max(0, risk_score))


def calculate_confidence_score(regime_score: float, risk_score: float,
                               trend_consistency: float, mean_reversion_signal: bool,
                               config) -> float:
    """Calculate overall confidence in the signal"""
    regime_confidence = min(1.0, abs(regime_score) / config.regime_confidence_divisor)

    risk_penalty = max(0, (risk_score - config.risk_penalty_min) /
                      (config.risk_penalty_max - config.risk_penalty_min))

    consistency_bonus = config.consistency_bonus if trend_consistency > config.trend_consistency_threshold else 0

    if mean_reversion_signal:
        base_confidence = config.mean_reversion_base_confidence
    else:
        base_confidence = regime_confidence

    confidence = base_confidence + consistency_bonus - (risk_penalty * config.risk_penalty_multiplier)
    confidence = max(0, min(1.0, confidence))

    return confidence
