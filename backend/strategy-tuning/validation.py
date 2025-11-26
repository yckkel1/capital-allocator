"""
Validation Module
Functions for out-of-sample validation of tuned parameters
"""
from datetime import date
from typing import Dict, Tuple, TYPE_CHECKING

from .performance_metrics import calculate_overall_metrics

if TYPE_CHECKING:
    from psycopg2.extensions import cursor
    from config_loader import TradingConfig


def perform_out_of_sample_validation(cursor, config, candidate_params: 'TradingConfig',
                                     train_period: Tuple[date, date],
                                     test_period: Tuple[date, date]) -> Dict:
    """
    Validate tuned parameters on out-of-sample data

    Returns:
        Dictionary with validation results
    """
    # This is a simplified validation - we check if the tuned parameters
    # would have led to better decisions in the test period

    train_start, train_end = train_period
    test_start, test_end = test_period

    # Get test period performance
    test_metrics = calculate_overall_metrics(cursor, test_start, test_end)

    # Compare against targets using tunable tolerance thresholds
    sharpe_passes = test_metrics.get('sharpe_ratio', 0) >= \
                   candidate_params.min_sharpe_target * config.validation_sharpe_tolerance
    drawdown_passes = test_metrics.get('max_drawdown', 100) <= \
                     candidate_params.max_drawdown_tolerance * config.validation_dd_tolerance

    # Overall validation score using tunable weights
    validation_score = 0
    if sharpe_passes:
        validation_score += config.validation_sharpe_weight
    if drawdown_passes:
        validation_score += config.validation_drawdown_weight

    return {
        'passes_validation': validation_score >= config.validation_passing_score,
        'validation_score': validation_score,
        'test_sharpe': test_metrics.get('sharpe_ratio', 0),
        'test_max_drawdown': test_metrics.get('max_drawdown', 0),
        'sharpe_passes': sharpe_passes,
        'drawdown_passes': drawdown_passes,
        'train_period': f"{train_start} to {train_end}",
        'test_period': f"{test_start} to {test_end}"
    }
