"""
Performance Analysis Module
Functions for analyzing performance by different conditions and criteria
"""
from typing import List, Dict
from data_models import TradeEvaluation


def analyze_performance_by_condition(evaluations: List[TradeEvaluation], config) -> Dict:
    """
    Analyze performance in different market conditions

    Returns:
        Dictionary with performance metrics by condition
    """
    momentum_trades = [e for e in evaluations if e.market_condition == 'momentum']
    choppy_trades = [e for e in evaluations if e.market_condition == 'choppy']

    def calc_metrics(trades):
        if not trades:
            return {
                'count': 0,
                'win_rate': 0,
                'avg_score': 0,
                'total_pnl': 0,
                'avg_drawdown_contribution': 0,
                'should_be_more_aggressive': False,
                'should_be_more_conservative': False
            }

        wins = sum(1 for t in trades if t.was_profitable)
        win_rate = wins / len(trades) * 100
        avg_score = sum(t.score for t in trades) / len(trades)
        total_pnl = sum(t.pnl for t in trades)
        avg_dd = sum(t.contribution_to_drawdown for t in trades) / len(trades)

        # Determine if strategy should be adjusted
        buy_trades = [t for t in trades if t.action == 'BUY']
        hold_trades = [t for t in trades if t.action == 'HOLD']

        # Should be more aggressive if: high win rate but low participation
        should_be_more_aggressive = (
            win_rate > config.tune_aggressive_win_rate and
            len(buy_trades) < len(trades) * config.tune_aggressive_participation and
            avg_score > config.tune_aggressive_score
        )

        # Should be more conservative if: low win rate or high DD contribution
        should_be_more_conservative = (
            win_rate < config.tune_conservative_win_rate or
            avg_dd > config.tune_conservative_dd or
            avg_score < config.tune_conservative_score
        )

        return {
            'count': len(trades),
            'win_rate': win_rate,
            'avg_score': avg_score,
            'total_pnl': total_pnl,
            'avg_drawdown_contribution': avg_dd,
            'buy_count': len(buy_trades),
            'hold_count': len(hold_trades),
            'should_be_more_aggressive': should_be_more_aggressive,
            'should_be_more_conservative': should_be_more_conservative
        }

    return {
        'momentum': calc_metrics(momentum_trades),
        'choppy': calc_metrics(choppy_trades),
        'overall': calc_metrics(evaluations)
    }


def analyze_confidence_buckets(evaluations: List[TradeEvaluation]) -> Dict:
    """
    Analyze performance by confidence bucket

    Returns:
        Dictionary with performance metrics by confidence level
    """
    high_conf = [e for e in evaluations if e.confidence_bucket == 'high']
    medium_conf = [e for e in evaluations if e.confidence_bucket == 'medium']
    low_conf = [e for e in evaluations if e.confidence_bucket == 'low']

    def calc_bucket_metrics(trades):
        if not trades:
            return {
                'count': 0,
                'win_rate': 0,
                'avg_pnl': 0,
                'total_pnl': 0,
                'avg_score': 0,
                'best_horizon_10d': 0,
                'best_horizon_20d': 0,
                'best_horizon_30d': 0
            }

        wins = sum(1 for t in trades if t.was_profitable)
        win_rate = wins / len(trades) * 100
        total_pnl = sum(t.pnl for t in trades)
        avg_pnl = total_pnl / len(trades)
        avg_score = sum(t.score for t in trades) / len(trades)

        # Analyze which horizon performs best
        best_10d = sum(1 for t in trades if t.best_horizon == '10d')
        best_20d = sum(1 for t in trades if t.best_horizon == '20d')
        best_30d = sum(1 for t in trades if t.best_horizon == '30d')

        return {
            'count': len(trades),
            'win_rate': win_rate,
            'avg_pnl': avg_pnl,
            'total_pnl': total_pnl,
            'avg_score': avg_score,
            'best_horizon_10d': best_10d,
            'best_horizon_20d': best_20d,
            'best_horizon_30d': best_30d
        }

    return {
        'high': calc_bucket_metrics(high_conf),
        'medium': calc_bucket_metrics(medium_conf),
        'low': calc_bucket_metrics(low_conf)
    }


def analyze_signal_types(evaluations: List[TradeEvaluation]) -> Dict:
    """
    Analyze performance by signal type (momentum vs mean reversion)

    Returns:
        Dictionary with performance metrics by signal type
    """
    signal_groups = {}
    for eval in evaluations:
        signal_type = eval.signal_type
        if signal_type not in signal_groups:
            signal_groups[signal_type] = []
        signal_groups[signal_type].append(eval)

    results = {}
    for signal_type, trades in signal_groups.items():
        wins = sum(1 for t in trades if t.was_profitable)
        win_rate = wins / len(trades) * 100 if trades else 0
        total_pnl = sum(t.pnl for t in trades)
        avg_pnl = total_pnl / len(trades) if trades else 0

        results[signal_type] = {
            'count': len(trades),
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'avg_pnl': avg_pnl
        }

    return results
