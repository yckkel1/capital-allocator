"""
Performance Metrics Module
Functions for calculating overall performance metrics
"""
from datetime import date
from typing import Dict, TYPE_CHECKING
import numpy as np
import math

from .constants import RISK_FREE_RATE, ANNUAL_TRADING_DAYS

if TYPE_CHECKING:
    from psycopg2.extensions import cursor


def calculate_overall_metrics(cursor, start_date: date, end_date: date) -> Dict:
    """Calculate overall performance metrics for the period"""
    cursor.execute("""
        SELECT * FROM performance_metrics
        WHERE date >= %s AND date <= %s
        ORDER BY date
    """, (start_date, end_date))

    performance_data = cursor.fetchall()

    if not performance_data:
        return {}

    # Calculate Sharpe ratio
    daily_returns = []
    for i in range(1, len(performance_data)):
        if performance_data[i-1]['total_value'] and performance_data[i-1]['total_value'] > 0:
            ret = float((performance_data[i]['total_value'] - performance_data[i-1]['total_value']) /
                       performance_data[i-1]['total_value'] * 100)
            daily_returns.append(ret)

    if len(daily_returns) > 1:
        mean_return = np.mean(daily_returns)
        std_return = np.std(daily_returns, ddof=1)
        sharpe = (mean_return * ANNUAL_TRADING_DAYS - RISK_FREE_RATE) / (std_return * math.sqrt(ANNUAL_TRADING_DAYS)) if std_return > 0 else 0
    else:
        sharpe = 0

    # Calculate max drawdown
    peak_value = 0
    max_dd = 0
    for data in performance_data:
        value = float(data['total_value'])
        if value > peak_value:
            peak_value = value
        dd = (peak_value - value) / peak_value * 100 if peak_value > 0 else 0
        if dd > max_dd:
            max_dd = dd

    # Total return
    start_value = float(performance_data[0]['total_value'])
    end_value = float(performance_data[-1]['total_value'])
    total_return = (end_value - start_value) / start_value * 100 if start_value > 0 else 0

    return {
        'sharpe_ratio': sharpe,
        'max_drawdown': max_dd,
        'total_return': total_return,
        'total_days': len(performance_data),
        'daily_returns': daily_returns
    }
