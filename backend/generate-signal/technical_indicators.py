"""
Technical Indicators Module
Functions for calculating technical indicators like RSI and Bollinger Bands
"""
import pandas as pd
from .constants import RSI_NEUTRAL, RSI_MAX, PERCENTAGE_MULTIPLIER


def calculate_rsi(prices: pd.Series, period: int = 14) -> float:
    """Calculate Relative Strength Index"""
    if len(prices) < period + 1:
        return RSI_NEUTRAL

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


def calculate_bollinger_bands(prices: pd.Series, period: int = 20,
                              num_std: float = 2.0) -> dict:
    """Calculate Bollinger Bands position"""
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
