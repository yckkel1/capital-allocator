"""
Market Analysis Module
Functions for detecting market conditions and analyzing market behavior
"""
from datetime import date, timedelta
from typing import TYPE_CHECKING
import numpy as np

from constants import MARKET_CONDITION_WINDOW_DAYS, MARKET_CONDITION_LOOKBACK_BUFFER

if TYPE_CHECKING:
    from psycopg2.extensions import cursor


def detect_market_condition(cursor, config, trade_date: date,
                            window: int = MARKET_CONDITION_WINDOW_DAYS) -> str:
    """
    Detect if market was in momentum or choppy condition

    Args:
        cursor: Database cursor
        config: Trading configuration with thresholds
        trade_date: Date to analyze
        window: Lookback window for analysis

    Returns:
        'momentum' or 'choppy'
    """
    lookback_start = trade_date - timedelta(days=window + MARKET_CONDITION_LOOKBACK_BUFFER)

    # Get SPY prices for the period
    cursor.execute("""
        SELECT date, close_price
        FROM price_history
        WHERE symbol = 'SPY'
        AND date >= %s AND date <= %s
        ORDER BY date
    """, (lookback_start, trade_date))

    prices = [float(row['close_price']) for row in cursor.fetchall()]

    if len(prices) < window:
        return 'unknown'

    prices = prices[-window:]

    # Calculate trend strength
    # 1. Linear regression slope (trend direction)
    x = np.arange(len(prices))
    y = np.array(prices)
    slope, _ = np.polyfit(x, y, 1)

    # 2. R-squared (trend consistency)
    y_pred = slope * x + np.mean(y) - slope * np.mean(x)
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

    # 3. Price volatility
    returns = np.diff(prices) / prices[:-1]
    volatility = np.std(returns)

    # Decision logic using tunable thresholds:
    # Strong momentum: High R-squared and clear trend
    # Choppy: Low R-squared or high volatility with no clear trend

    if r_squared > config.market_condition_r_squared_threshold and \
       abs(slope) > config.market_condition_slope_threshold:
        return 'momentum'
    elif r_squared < config.market_condition_choppy_r_squared or \
         volatility > config.market_condition_choppy_volatility:
        return 'choppy'
    else:
        return 'mixed'
