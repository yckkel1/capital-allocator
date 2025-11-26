"""
Circuit Breaker Module
Functions for checking circuit breaker conditions
"""
from datetime import date


def check_circuit_breaker(db, trade_date: date, intramonth_drawdown_limit: float) -> tuple:
    """
    Check if circuit breaker should be triggered

    Returns:
        tuple: (triggered: bool, current_drawdown: float)
    """
    from models import PerformanceMetrics
    
    month_start = date(trade_date.year, trade_date.month, 1)

    perf_data = db.query(PerformanceMetrics).filter(
        PerformanceMetrics.date >= month_start,
        PerformanceMetrics.date < trade_date
    ).order_by(PerformanceMetrics.date.asc()).all()

    if len(perf_data) < 2:
        return (False, 0.0)

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
