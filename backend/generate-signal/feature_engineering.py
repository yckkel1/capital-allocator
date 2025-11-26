"""
Feature Engineering Module
Functions for calculating multi-timeframe features
"""
import pandas as pd
from .technical_indicators import calculate_rsi, calculate_bollinger_bands
from .constants import (
    HORIZON_5D, HORIZON_10D, HORIZON_20D, HORIZON_30D, 
    HORIZON_50D, HORIZON_60D, RSI_DEFAULT_PERIOD, BB_DEFAULT_PERIOD
)


def calculate_multi_timeframe_features(df: pd.DataFrame, config) -> dict:
    """Calculate features with multiple timeframes including mean reversion indicators"""
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

    # RSI calculation
    rsi = calculate_rsi(df['close'], period=RSI_DEFAULT_PERIOD)

    # Bollinger Bands
    bb = calculate_bollinger_bands(df['close'], period=BB_DEFAULT_PERIOD,
                                   num_std=config.bollinger_std_multiplier)

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
