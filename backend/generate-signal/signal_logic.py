"""
Signal Logic Module
Core decision logic for BUY/SELL/HOLD signals
"""


def decide_action(regime_score: float, risk_score: float, has_holdings: bool,
                 mean_reversion_opportunity: tuple, adaptive_bullish_threshold: float,
                 adaptive_bearish_threshold: float, current_drawdown: float,
                 features_by_asset: dict, config, cash_pct: float = 0.0) -> tuple:
    """
    Decide whether to BUY, SELL, or HOLD with enhanced logic

    Returns:
        tuple: (action: str, allocation_pct: float, signal_type: str)
    """
    from .mean_reversion import detect_downward_pressure
    
    has_mr_opportunity, mr_type, mr_assets = mean_reversion_opportunity

    # Detect downward pressure early
    has_pressure, pressure_severity, pressure_reason = detect_downward_pressure(features_by_asset, risk_score, config)

    if has_pressure and has_holdings:
        if pressure_severity == "severe":
            if cash_pct > config.defensive_cash_threshold:
                sell_pct = min(config.sell_percentage * config.sell_defensive_multiplier, config.sell_percentage)
            else:
                sell_pct = min(config.sell_percentage_max, config.sell_percentage * config.sell_aggressive_multiplier)
            return ("SELL", sell_pct, f"downward_pressure_severe")
        elif pressure_severity == "moderate" and regime_score < config.regime_transition_threshold:
            if cash_pct > config.defensive_cash_threshold:
                pass
            else:
                sell_pct = config.sell_percentage * config.sell_moderate_pressure_multiplier
                return ("SELL", sell_pct, "downward_pressure_moderate")

    # Sell aggressively when risk is VERY HIGH
    if risk_score > config.extreme_risk_threshold and has_holdings:
        sell_pct = config.sell_percentage
        return ("SELL", sell_pct, "extreme_risk_protection")

    # Bearish regime
    if regime_score < adaptive_bearish_threshold:
        if has_holdings:
            bearish_intensity = abs(regime_score - adaptive_bearish_threshold) / (1.0 - adaptive_bearish_threshold)
            sell_pct = min(config.sell_percentage, config.bearish_sell_base + (bearish_intensity * config.bearish_sell_intensity_multiplier))
            return ("SELL", sell_pct, "bearish_regime")
        else:
            return ("HOLD", 0.0, "bearish_no_holdings")

    # Neutral regime with mean reversion opportunity
    elif adaptive_bearish_threshold <= regime_score <= adaptive_bullish_threshold:
        if has_mr_opportunity and mr_type == 'oversold_bounce' and risk_score < config.mean_reversion_max_risk:
            allocation_pct = config.mean_reversion_allocation
            return ("BUY", allocation_pct, "mean_reversion_oversold")
        elif risk_score > config.neutral_deleverage_risk and has_holdings:
            sell_pct = config.sell_percentage * config.sell_moderate_pressure_multiplier
            return ("SELL", sell_pct, "neutral_high_risk_deleverage")
        elif risk_score > config.neutral_hold_risk:
            return ("HOLD", 0.0, "neutral_high_risk")
        else:
            return ("BUY", config.allocation_neutral, "neutral_cautious")

    # Bullish regime
    else:
        if risk_score > config.bullish_excessive_risk and has_holdings:
            sell_pct = config.sell_percentage * config.sell_bullish_risk_multiplier
            return ("SELL", sell_pct, "bullish_excessive_risk")
        elif risk_score > config.risk_high_threshold:
            if has_holdings and risk_score > config.bullish_excessive_risk:
                return ("HOLD", 0.0, "bullish_high_risk_hold")
            else:
                allocation_pct = config.allocation_high_risk
                return ("BUY", allocation_pct, "bullish_high_risk")
        elif risk_score > config.risk_medium_threshold:
            allocation_pct = config.allocation_medium_risk
            return ("BUY", allocation_pct, "bullish_medium_risk")
        else:
            allocation_pct = config.allocation_low_risk
            return ("BUY", allocation_pct, "bullish_momentum")
