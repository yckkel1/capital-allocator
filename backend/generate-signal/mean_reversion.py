"""
Mean Reversion Module
Functions for detecting mean reversion opportunities
"""


def detect_mean_reversion_opportunity(features_by_asset: dict, regime_score: float, 
                                     config) -> tuple:
    """Check if there's a mean reversion opportunity in neutral/mild regimes"""
    if abs(regime_score) > config.strong_trend_threshold:
        return (False, None, [])

    oversold_assets = []
    overbought_assets = []

    for symbol, features in features_by_asset.items():
        rsi = features.get('rsi', 50.0)
        bb_position = features.get('bollinger_position', 0)

        # Check for oversold bounce opportunity
        if rsi < config.rsi_oversold_threshold and bb_position < config.bb_oversold_threshold:
            oversold_assets.append(symbol)
        # Check for overbought reversal
        elif rsi > config.rsi_overbought_threshold and bb_position > config.bb_overbought_threshold:
            overbought_assets.append(symbol)

    if oversold_assets:
        return (True, 'oversold_bounce', oversold_assets)
    elif overbought_assets:
        return (True, 'overbought_reversal', overbought_assets)

    return (False, None, [])


def detect_downward_pressure(features_by_asset: dict, risk_score: float, config) -> tuple:
    """Detect sustained downward pressure"""
    negative_momentum_count = 0
    below_sma_count = 0
    high_vol_negative_count = 0
    total_assets = len(features_by_asset)

    for symbol, features in features_by_asset.items():
        returns_5d = features.get('returns_5d', 0)
        returns_20d = features.get('returns_20d', 0)
        returns_60d = features.get('returns_60d', 0)

        if returns_5d < 0 and returns_20d < 0 and returns_60d < 0:
            negative_momentum_count += 1

        price_vs_sma20 = features.get('price_vs_sma20', 0)
        price_vs_sma50 = features.get('price_vs_sma50', 0)

        if price_vs_sma20 < config.price_vs_sma_threshold and price_vs_sma50 < config.price_vs_sma_threshold:
            below_sma_count += 1

        volatility = features.get('volatility', 0)
        if volatility > config.high_volatility_threshold and returns_5d < config.negative_return_threshold:
            high_vol_negative_count += 1

    negative_momentum_pct = negative_momentum_count / total_assets
    below_sma_pct = below_sma_count / total_assets
    high_vol_negative_pct = high_vol_negative_count / total_assets

    if (negative_momentum_pct >= config.severe_pressure_threshold and below_sma_pct >= config.severe_pressure_threshold) or \
       (high_vol_negative_pct >= config.severe_pressure_threshold and risk_score > config.severe_pressure_risk):
        return (True, "severe", f"Sustained downtrend across {negative_momentum_count}/{total_assets} assets with elevated risk")

    elif (negative_momentum_pct >= config.moderate_pressure_threshold and risk_score > config.moderate_pressure_risk) or \
         (below_sma_pct >= config.severe_pressure_threshold):
        return (True, "moderate", f"Emerging downward pressure in {negative_momentum_count}/{total_assets} assets")

    return (False, "none", "")
