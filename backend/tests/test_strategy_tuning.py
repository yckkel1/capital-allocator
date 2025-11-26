"""
Unit tests for strategy_tuning.py (REFACTORED)
Tests monthly strategy parameter tuning with new modular structure
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import date, timedelta
import numpy as np
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'strategy-tuning'))

from data_models import TradeEvaluation
from performance_analysis import analyze_performance_by_condition, analyze_confidence_buckets, analyze_signal_types


class TestTradeEvaluation:
    """Test TradeEvaluation dataclass"""

    def test_trade_evaluation_creation(self):
        """Test creating a trade evaluation"""
        eval = TradeEvaluation(
            trade_date=date(2025, 11, 15),
            symbol='SPY',
            action='BUY',
            amount=400.0,
            regime='bullish',
            market_condition='momentum',
            contribution_to_drawdown=5.0,
            sharpe_impact=0.1,
            was_profitable=True,
            pnl=10.5,
            score=0.5,
            should_have_avoided=False
        )

        assert eval.symbol == 'SPY'
        assert eval.was_profitable is True
        assert eval.score == 0.5


class TestPerformanceAnalysis:
    """Test performance analysis functions"""

    def test_analyze_by_condition(self):
        """Test performance analysis by market condition"""
        mock_config = Mock()
        mock_config.good_trade_score_threshold = 0.3
        mock_config.tune_aggressive_win_rate = 65.0
        mock_config.tune_aggressive_participation = 0.6
        mock_config.tune_aggressive_score = 0.2
        mock_config.tune_conservative_win_rate = 45.0
        mock_config.tune_conservative_dd = 20.0
        mock_config.tune_conservative_score = -0.2

        evaluations = [
            TradeEvaluation(
                trade_date=date(2025, 11, 1),
                symbol='SPY',
                action='BUY',
                amount=400.0,
                regime='bullish',
                market_condition='momentum',
                contribution_to_drawdown=5.0,
                sharpe_impact=0.1,
                was_profitable=True,
                pnl=10.5,
                score=0.5,
                should_have_avoided=False
            ),
            TradeEvaluation(
                trade_date=date(2025, 11, 2),
                symbol='QQQ',
                action='BUY',
                amount=300.0,
                regime='neutral',
                market_condition='choppy',
                contribution_to_drawdown=25.0,
                sharpe_impact=-0.1,
                was_profitable=False,
                pnl=-15.0,
                score=-0.3,
                should_have_avoided=True
            )
        ]

        analysis = analyze_performance_by_condition(evaluations, mock_config)

        assert 'momentum' in analysis
        assert 'choppy' in analysis
        assert 'overall' in analysis
        assert analysis['momentum']['count'] == 1
        assert analysis['choppy']['count'] == 1


class TestConfidenceBuckets:
    """Test confidence bucket analysis"""

    def test_analyze_confidence_buckets(self):
        """Test performance analysis by confidence bucket"""
        evaluations = [
            TradeEvaluation(
                trade_date=date(2025, 11, 1), symbol='SPY', action='BUY',
                amount=400.0, regime='bullish', market_condition='momentum',
                contribution_to_drawdown=5.0, sharpe_impact=0.1,
                was_profitable=True, pnl=15.0,
                pnl_10d=10.0, pnl_20d=15.0, pnl_30d=12.0,
                best_horizon='20d', confidence_bucket='high',
                signal_type='bullish_momentum', score=0.5, should_have_avoided=False
            ),
            TradeEvaluation(
                trade_date=date(2025, 11, 2), symbol='QQQ', action='BUY',
                amount=300.0, regime='neutral', market_condition='choppy',
                contribution_to_drawdown=25.0, sharpe_impact=-0.1,
                was_profitable=False, pnl=-15.0,
                pnl_10d=-10.0, pnl_20d=-15.0, pnl_30d=-12.0,
                best_horizon='30d', confidence_bucket='low',
                signal_type='neutral_cautious', score=-0.3, should_have_avoided=True
            )
        ]

        analysis = analyze_confidence_buckets(evaluations)

        assert 'high' in analysis
        assert 'low' in analysis
        assert analysis['high']['count'] == 1
        assert analysis['low']['count'] == 1
        assert analysis['high']['win_rate'] == 100.0
        assert analysis['low']['win_rate'] == 0.0


class TestStrategyTuner:
    """Test StrategyTuner class"""

    @patch('strategy_tuning.ConfigLoader')
    @patch('strategy_tuning.psycopg2.connect')
    @patch('strategy_tuning.get_settings')
    def test_tuner_init(self, mock_get_settings, mock_connect, mock_config_loader):
        """Test StrategyTuner initialization"""
        mock_settings = Mock()
        mock_settings.database_url = "postgresql://test:test@localhost:5432/testdb"
        mock_get_settings.return_value = mock_settings

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        mock_loader = Mock()
        mock_loader.get_active_config.return_value = Mock()
        mock_config_loader.return_value = mock_loader

        from strategy_tuning import StrategyTuner

        tuner = StrategyTuner(lookback_months=3)

        assert tuner.lookback_months == 3
        mock_connect.assert_called_once()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
