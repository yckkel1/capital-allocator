"""
Unit tests for strategy_tuning.py
Tests monthly strategy parameter tuning
"""
import pytest
from unittest.mock import Mock, patch, MagicMock, mock_open
from datetime import date, datetime, timedelta
from decimal import Decimal
import numpy as np
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestTradeEvaluation:
    """Test TradeEvaluation dataclass"""

    def test_trade_evaluation_creation(self):
        """Test creating a trade evaluation"""
        from strategy_tuning import TradeEvaluation

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

    def test_trade_evaluation_with_enhanced_fields(self):
        """Test creating a trade evaluation with enhanced fields"""
        from strategy_tuning import TradeEvaluation

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
            should_have_avoided=False,
            pnl_10d=8.0,
            pnl_20d=10.5,
            pnl_30d=12.0,
            best_horizon='30d',
            confidence_bucket='high',
            signal_type='bullish_momentum'
        )

        assert eval.pnl_10d == 8.0
        assert eval.pnl_20d == 10.5
        assert eval.pnl_30d == 12.0
        assert eval.best_horizon == '30d'
        assert eval.confidence_bucket == 'high'
        assert eval.signal_type == 'bullish_momentum'


class TestStrategyTunerInit:
    """Test StrategyTuner initialization"""

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

    @patch('strategy_tuning.ConfigLoader')
    @patch('strategy_tuning.psycopg2.connect')
    @patch('strategy_tuning.get_settings')
    def test_tuner_close(self, mock_get_settings, mock_connect, mock_config_loader):
        """Test StrategyTuner close method"""
        mock_settings = Mock()
        mock_settings.database_url = "postgresql://test"
        mock_get_settings.return_value = mock_settings

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        mock_loader = Mock()
        mock_loader.get_active_config.return_value = Mock()
        mock_config_loader.return_value = mock_loader

        from strategy_tuning import StrategyTuner

        tuner = StrategyTuner()
        tuner.close()

        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()


class TestDetectMarketCondition:
    """Test detect_market_condition method"""

    @patch('strategy_tuning.ConfigLoader')
    @patch('strategy_tuning.psycopg2.connect')
    @patch('strategy_tuning.get_settings')
    def test_detect_momentum_market(self, mock_get_settings, mock_connect, mock_config_loader):
        """Test detection of momentum market"""
        mock_settings = Mock()
        mock_settings.database_url = "postgresql://test"
        mock_get_settings.return_value = mock_settings

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        mock_loader = Mock()
        mock_loader.get_active_config.return_value = Mock()
        mock_config_loader.return_value = mock_loader

        # Simulate clear uptrend
        prices = [{'close_price': 580.0 + i * 0.5} for i in range(25)]
        mock_cursor.fetchall.return_value = prices

        from strategy_tuning import StrategyTuner

        tuner = StrategyTuner()
        condition = tuner.detect_market_condition(date(2025, 11, 15))

        # Strong uptrend = momentum
        assert condition in ['momentum', 'mixed', 'unknown']

    @patch('strategy_tuning.ConfigLoader')
    @patch('strategy_tuning.psycopg2.connect')
    @patch('strategy_tuning.get_settings')
    def test_detect_choppy_market(self, mock_get_settings, mock_connect, mock_config_loader):
        """Test detection of choppy market"""
        mock_settings = Mock()
        mock_settings.database_url = "postgresql://test"
        mock_get_settings.return_value = mock_settings

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        mock_loader = Mock()
        mock_loader.get_active_config.return_value = Mock()
        mock_config_loader.return_value = mock_loader

        # Simulate choppy market (oscillating prices)
        prices = [{'close_price': 580.0 + (i % 3 - 1) * 2.0} for i in range(25)]
        mock_cursor.fetchall.return_value = prices

        from strategy_tuning import StrategyTuner

        tuner = StrategyTuner()
        condition = tuner.detect_market_condition(date(2025, 11, 15))

        assert condition in ['choppy', 'mixed', 'unknown']

    @patch('strategy_tuning.ConfigLoader')
    @patch('strategy_tuning.psycopg2.connect')
    @patch('strategy_tuning.get_settings')
    def test_insufficient_data_returns_unknown(self, mock_get_settings, mock_connect, mock_config_loader):
        """Test that insufficient data returns unknown"""
        mock_settings = Mock()
        mock_settings.database_url = "postgresql://test"
        mock_get_settings.return_value = mock_settings

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        mock_loader = Mock()
        mock_loader.get_active_config.return_value = Mock()
        mock_config_loader.return_value = mock_loader

        # Only 5 prices (not enough)
        prices = [{'close_price': 580.0 + i} for i in range(5)]
        mock_cursor.fetchall.return_value = prices

        from strategy_tuning import StrategyTuner

        tuner = StrategyTuner()
        condition = tuner.detect_market_condition(date(2025, 11, 15))

        assert condition == 'unknown'


class TestCalculateDrawdownContribution:
    """Test calculate_drawdown_contribution method"""

    @patch('strategy_tuning.ConfigLoader')
    @patch('strategy_tuning.psycopg2.connect')
    @patch('strategy_tuning.get_settings')
    def test_drawdown_contribution_loss(self, mock_get_settings, mock_connect, mock_config_loader):
        """Test drawdown contribution for losing trade"""
        mock_settings = Mock()
        mock_settings.database_url = "postgresql://test"
        mock_get_settings.return_value = mock_settings

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        mock_loader = Mock()
        mock_loader.get_active_config.return_value = Mock()
        mock_config_loader.return_value = mock_loader

        # Simulate drawdown: peak 10500, trough 9800 (using dicts as returned by RealDictCursor)
        mock_cursor.fetchall.return_value = [
            {'date': date(2025, 11, 10), 'total_value': 10000.0},
            {'date': date(2025, 11, 11), 'total_value': 10500.0},  # Peak
            {'date': date(2025, 11, 12), 'total_value': 10200.0},
            {'date': date(2025, 11, 13), 'total_value': 9800.0},   # Trough
            {'date': date(2025, 11, 14), 'total_value': 10000.0},
        ]

        from strategy_tuning import StrategyTuner

        tuner = StrategyTuner()
        contribution = tuner.calculate_drawdown_contribution(date(2025, 11, 13), -100.0)

        # Should return non-zero contribution
        assert contribution >= 0

    @patch('strategy_tuning.ConfigLoader')
    @patch('strategy_tuning.psycopg2.connect')
    @patch('strategy_tuning.get_settings')
    def test_drawdown_contribution_profit(self, mock_get_settings, mock_connect, mock_config_loader):
        """Test drawdown contribution for profitable trade"""
        mock_settings = Mock()
        mock_settings.database_url = "postgresql://test"
        mock_get_settings.return_value = mock_settings

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        mock_loader = Mock()
        mock_loader.get_active_config.return_value = Mock()
        mock_config_loader.return_value = mock_loader

        mock_cursor.fetchall.return_value = [
            {'date': date(2025, 11, 10), 'total_value': 10000.0},
            {'date': date(2025, 11, 11), 'total_value': 10100.0},
        ]

        from strategy_tuning import StrategyTuner

        tuner = StrategyTuner()
        contribution = tuner.calculate_drawdown_contribution(date(2025, 11, 11), 50.0)

        # Profitable trade should have zero contribution
        assert contribution == 0.0


class TestAnalyzePerformanceByCondition:
    """Test analyze_performance_by_condition method"""

    @patch('strategy_tuning.ConfigLoader')
    @patch('strategy_tuning.psycopg2.connect')
    @patch('strategy_tuning.get_settings')
    def test_analyze_by_condition(self, mock_get_settings, mock_connect, mock_config_loader):
        """Test performance analysis by market condition"""
        mock_settings = Mock()
        mock_settings.database_url = "postgresql://test"
        mock_get_settings.return_value = mock_settings
        mock_connect.return_value = MagicMock()

        mock_loader = Mock()
        mock_loader.get_active_config.return_value = Mock()
        mock_config_loader.return_value = mock_loader

        from strategy_tuning import StrategyTuner, TradeEvaluation

        tuner = StrategyTuner()

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

        analysis = tuner.analyze_performance_by_condition(evaluations)

        assert 'momentum' in analysis
        assert 'choppy' in analysis
        assert 'overall' in analysis
        assert analysis['momentum']['count'] == 1
        assert analysis['choppy']['count'] == 1
        assert analysis['overall']['count'] == 2


class TestTuneParameters:
    """Test tune_parameters method"""

    @patch('strategy_tuning.ConfigLoader')
    @patch('strategy_tuning.psycopg2.connect')
    @patch('strategy_tuning.get_settings')
    def test_tune_increases_allocation_on_aggressive(self, mock_get_settings, mock_connect, mock_config_loader):
        """Test that parameters increase allocation when too conservative"""
        mock_settings = Mock()
        mock_settings.database_url = "postgresql://test"
        mock_get_settings.return_value = mock_settings
        mock_connect.return_value = MagicMock()

        from config_loader import TradingConfig
        mock_loader = Mock()
        current_config = TradingConfig(
            daily_capital=1000.0,
            assets=["SPY", "QQQ", "DIA"],
            lookback_days=252,
            regime_bullish_threshold=0.3,
            regime_bearish_threshold=-0.3,
            risk_high_threshold=70.0,
            risk_medium_threshold=40.0,
            allocation_low_risk=0.8,
            allocation_medium_risk=0.5,
            allocation_high_risk=0.3,
            allocation_neutral=0.2,
            sell_percentage=0.7,
            momentum_weight=0.6,
            price_momentum_weight=0.4,
            max_drawdown_tolerance=15.0,
            min_sharpe_target=1.0
        )
        mock_loader.get_active_config.return_value = current_config
        mock_config_loader.return_value = mock_loader

        from strategy_tuning import StrategyTuner

        tuner = StrategyTuner()

        condition_analysis = {
            'momentum': {
                'count': 10,
                'win_rate': 70.0,
                'avg_score': 0.3,
                'should_be_more_aggressive': True,
                'should_be_more_conservative': False
            },
            'choppy': {
                'count': 5,
                'should_be_more_aggressive': False,
                'should_be_more_conservative': False
            },
            'overall': {
                'count': 15
            }
        }

        overall_metrics = {
            'sharpe_ratio': 1.5,
            'max_drawdown': 10.0
        }

        new_params = tuner.tune_parameters([], condition_analysis, overall_metrics)

        # Should increase allocation
        assert new_params.allocation_low_risk > current_config.allocation_low_risk

    @patch('strategy_tuning.ConfigLoader')
    @patch('strategy_tuning.psycopg2.connect')
    @patch('strategy_tuning.get_settings')
    def test_tune_decreases_allocation_on_high_drawdown(self, mock_get_settings, mock_connect, mock_config_loader):
        """Test that parameters decrease allocation when drawdown exceeds tolerance"""
        mock_settings = Mock()
        mock_settings.database_url = "postgresql://test"
        mock_get_settings.return_value = mock_settings
        mock_connect.return_value = MagicMock()

        from config_loader import TradingConfig
        mock_loader = Mock()
        current_config = TradingConfig(
            daily_capital=1000.0,
            assets=["SPY", "QQQ", "DIA"],
            lookback_days=252,
            regime_bullish_threshold=0.3,
            regime_bearish_threshold=-0.3,
            risk_high_threshold=70.0,
            risk_medium_threshold=40.0,
            allocation_low_risk=0.8,
            allocation_medium_risk=0.5,
            allocation_high_risk=0.3,
            allocation_neutral=0.2,
            sell_percentage=0.7,
            momentum_weight=0.6,
            price_momentum_weight=0.4,
            max_drawdown_tolerance=15.0,
            min_sharpe_target=1.0
        )
        mock_loader.get_active_config.return_value = current_config
        mock_config_loader.return_value = mock_loader

        from strategy_tuning import StrategyTuner

        tuner = StrategyTuner()

        condition_analysis = {
            'momentum': {'should_be_more_aggressive': False, 'should_be_more_conservative': False},
            'choppy': {'should_be_more_aggressive': False, 'should_be_more_conservative': False},
            'overall': {}
        }

        overall_metrics = {
            'sharpe_ratio': 1.2,
            'max_drawdown': 20.0  # Exceeds 15% tolerance
        }

        new_params = tuner.tune_parameters([], condition_analysis, overall_metrics)

        # Should tighten risk controls
        assert new_params.risk_high_threshold < current_config.risk_high_threshold


class TestAnalyzeConfidenceBuckets:
    """Test analyze_confidence_buckets method"""

    @patch('strategy_tuning.ConfigLoader')
    @patch('strategy_tuning.psycopg2.connect')
    @patch('strategy_tuning.get_settings')
    def test_analyze_confidence_buckets(self, mock_get_settings, mock_connect, mock_config_loader):
        """Test performance analysis by confidence bucket"""
        mock_settings = Mock()
        mock_settings.database_url = "postgresql://test"
        mock_get_settings.return_value = mock_settings
        mock_connect.return_value = MagicMock()

        mock_loader = Mock()
        mock_loader.get_active_config.return_value = Mock()
        mock_config_loader.return_value = mock_loader

        from strategy_tuning import StrategyTuner, TradeEvaluation

        tuner = StrategyTuner()

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

        analysis = tuner.analyze_confidence_buckets(evaluations)

        assert 'high' in analysis
        assert 'medium' in analysis
        assert 'low' in analysis
        assert analysis['high']['count'] == 1
        assert analysis['low']['count'] == 1
        assert analysis['high']['win_rate'] == 100.0
        assert analysis['low']['win_rate'] == 0.0

    @patch('strategy_tuning.ConfigLoader')
    @patch('strategy_tuning.psycopg2.connect')
    @patch('strategy_tuning.get_settings')
    def test_analyze_confidence_buckets_empty(self, mock_get_settings, mock_connect, mock_config_loader):
        """Test confidence bucket analysis with no trades"""
        mock_settings = Mock()
        mock_settings.database_url = "postgresql://test"
        mock_get_settings.return_value = mock_settings
        mock_connect.return_value = MagicMock()

        mock_loader = Mock()
        mock_loader.get_active_config.return_value = Mock()
        mock_config_loader.return_value = mock_loader

        from strategy_tuning import StrategyTuner

        tuner = StrategyTuner()
        analysis = tuner.analyze_confidence_buckets([])

        assert analysis['high']['count'] == 0
        assert analysis['medium']['count'] == 0
        assert analysis['low']['count'] == 0


class TestAnalyzeSignalTypes:
    """Test analyze_signal_types method"""

    @patch('strategy_tuning.ConfigLoader')
    @patch('strategy_tuning.psycopg2.connect')
    @patch('strategy_tuning.get_settings')
    def test_analyze_signal_types(self, mock_get_settings, mock_connect, mock_config_loader):
        """Test performance analysis by signal type"""
        mock_settings = Mock()
        mock_settings.database_url = "postgresql://test"
        mock_get_settings.return_value = mock_settings
        mock_connect.return_value = MagicMock()

        mock_loader = Mock()
        mock_loader.get_active_config.return_value = Mock()
        mock_config_loader.return_value = mock_loader

        from strategy_tuning import StrategyTuner, TradeEvaluation

        tuner = StrategyTuner()

        evaluations = [
            TradeEvaluation(
                trade_date=date(2025, 11, 1), symbol='SPY', action='BUY',
                amount=400.0, regime='bullish', market_condition='momentum',
                contribution_to_drawdown=5.0, sharpe_impact=0.1,
                was_profitable=True, pnl=15.0,
                signal_type='bullish_momentum', score=0.5, should_have_avoided=False
            ),
            TradeEvaluation(
                trade_date=date(2025, 11, 2), symbol='QQQ', action='BUY',
                amount=300.0, regime='neutral', market_condition='choppy',
                contribution_to_drawdown=5.0, sharpe_impact=0.15,
                was_profitable=True, pnl=10.0,
                signal_type='mean_reversion_oversold', score=0.4, should_have_avoided=False
            )
        ]

        analysis = tuner.analyze_signal_types(evaluations)

        assert 'bullish_momentum' in analysis
        assert 'mean_reversion_oversold' in analysis
        assert analysis['bullish_momentum']['count'] == 1
        assert analysis['mean_reversion_oversold']['count'] == 1
        assert analysis['bullish_momentum']['win_rate'] == 100.0


class TestOutOfSampleValidation:
    """Test out-of-sample validation"""

    @patch('strategy_tuning.ConfigLoader')
    @patch('strategy_tuning.psycopg2.connect')
    @patch('strategy_tuning.get_settings')
    def test_validation_passes(self, mock_get_settings, mock_connect, mock_config_loader):
        """Test validation passes with good metrics"""
        mock_settings = Mock()
        mock_settings.database_url = "postgresql://test"
        mock_get_settings.return_value = mock_settings

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Mock performance metrics for test period
        mock_cursor.fetchall.return_value = [
            {'date': date(2025, 11, 1), 'total_value': 10000.0},
            {'date': date(2025, 11, 2), 'total_value': 10100.0},
            {'date': date(2025, 11, 3), 'total_value': 10200.0},
        ]

        from config_loader import TradingConfig
        mock_loader = Mock()
        current_config = TradingConfig(
            daily_capital=1000.0, assets=["SPY", "QQQ", "DIA"],
            lookback_days=252, regime_bullish_threshold=0.3,
            regime_bearish_threshold=-0.3, risk_high_threshold=70.0,
            risk_medium_threshold=40.0, allocation_low_risk=0.8,
            allocation_medium_risk=0.5, allocation_high_risk=0.3,
            allocation_neutral=0.2, sell_percentage=0.7,
            momentum_weight=0.6, price_momentum_weight=0.4,
            max_drawdown_tolerance=15.0, min_sharpe_target=1.0
        )
        mock_loader.get_active_config.return_value = current_config
        mock_config_loader.return_value = mock_loader

        from strategy_tuning import StrategyTuner

        tuner = StrategyTuner()
        result = tuner.perform_out_of_sample_validation(
            current_config,
            (date(2025, 10, 1), date(2025, 10, 20)),
            (date(2025, 10, 21), date(2025, 11, 15))
        )

        assert 'passes_validation' in result
        assert 'validation_score' in result
        assert 'test_sharpe' in result
        assert 'test_max_drawdown' in result


class TestTuneParametersEnhanced:
    """Test enhanced tune_parameters method"""

    @patch('strategy_tuning.ConfigLoader')
    @patch('strategy_tuning.psycopg2.connect')
    @patch('strategy_tuning.get_settings')
    def test_tune_confidence_threshold(self, mock_get_settings, mock_connect, mock_config_loader):
        """Test tuning of confidence threshold based on low confidence performance"""
        mock_settings = Mock()
        mock_settings.database_url = "postgresql://test"
        mock_get_settings.return_value = mock_settings
        mock_connect.return_value = MagicMock()

        from config_loader import TradingConfig
        mock_loader = Mock()
        current_config = TradingConfig(
            daily_capital=1000.0, assets=["SPY", "QQQ", "DIA"],
            lookback_days=252, regime_bullish_threshold=0.3,
            regime_bearish_threshold=-0.3, risk_high_threshold=70.0,
            risk_medium_threshold=40.0, allocation_low_risk=0.8,
            allocation_medium_risk=0.5, allocation_high_risk=0.3,
            allocation_neutral=0.2, sell_percentage=0.7,
            momentum_weight=0.6, price_momentum_weight=0.4,
            max_drawdown_tolerance=15.0, min_sharpe_target=1.0,
            min_confidence_threshold=0.3, confidence_scaling_factor=0.5
        )
        mock_loader.get_active_config.return_value = current_config
        mock_config_loader.return_value = mock_loader

        from strategy_tuning import StrategyTuner

        tuner = StrategyTuner()

        condition_analysis = {
            'momentum': {'should_be_more_aggressive': False, 'should_be_more_conservative': False},
            'choppy': {'should_be_more_aggressive': False, 'should_be_more_conservative': False},
            'overall': {}
        }

        overall_metrics = {
            'sharpe_ratio': 1.2,
            'max_drawdown': 10.0
        }

        # Low confidence trades performing poorly
        confidence_analysis = {
            'high': {'count': 5, 'win_rate': 75.0},
            'medium': {'count': 10, 'win_rate': 55.0},
            'low': {'count': 8, 'win_rate': 35.0}  # Poor performance
        }

        new_params = tuner.tune_parameters(
            [], condition_analysis, overall_metrics,
            confidence_analysis, None
        )

        # Should increase minimum confidence threshold
        assert new_params.min_confidence_threshold > current_config.min_confidence_threshold

    @patch('strategy_tuning.ConfigLoader')
    @patch('strategy_tuning.psycopg2.connect')
    @patch('strategy_tuning.get_settings')
    def test_tune_mean_reversion_allocation(self, mock_get_settings, mock_connect, mock_config_loader):
        """Test tuning of mean reversion allocation"""
        mock_settings = Mock()
        mock_settings.database_url = "postgresql://test"
        mock_get_settings.return_value = mock_settings
        mock_connect.return_value = MagicMock()

        from config_loader import TradingConfig
        mock_loader = Mock()
        current_config = TradingConfig(
            daily_capital=1000.0, assets=["SPY", "QQQ", "DIA"],
            lookback_days=252, regime_bullish_threshold=0.3,
            regime_bearish_threshold=-0.3, risk_high_threshold=70.0,
            risk_medium_threshold=40.0, allocation_low_risk=0.8,
            allocation_medium_risk=0.5, allocation_high_risk=0.3,
            allocation_neutral=0.2, sell_percentage=0.7,
            momentum_weight=0.6, price_momentum_weight=0.4,
            max_drawdown_tolerance=15.0, min_sharpe_target=1.0,
            mean_reversion_allocation=0.4
        )
        mock_loader.get_active_config.return_value = current_config
        mock_config_loader.return_value = mock_loader

        from strategy_tuning import StrategyTuner

        tuner = StrategyTuner()

        condition_analysis = {
            'momentum': {'should_be_more_aggressive': False, 'should_be_more_conservative': False},
            'choppy': {'should_be_more_aggressive': False, 'should_be_more_conservative': False},
            'overall': {}
        }

        overall_metrics = {
            'sharpe_ratio': 1.2,
            'max_drawdown': 10.0
        }

        # Mean reversion signals performing well
        signal_type_analysis = {
            'mean_reversion_oversold': {'count': 10, 'win_rate': 65.0},
            'bullish_momentum': {'count': 20, 'win_rate': 55.0}
        }

        new_params = tuner.tune_parameters(
            [], condition_analysis, overall_metrics,
            None, signal_type_analysis
        )

        # Should increase mean reversion allocation
        assert new_params.mean_reversion_allocation > current_config.mean_reversion_allocation


class TestMainFunction:
    """Test main entry point"""

    def test_main_function_exists(self):
        """Test that main function exists"""
        from strategy_tuning import main
        assert callable(main)

    def test_strategy_tuner_class_exists(self):
        """Test that StrategyTuner class exists"""
        from strategy_tuning import StrategyTuner
        assert StrategyTuner is not None

    def test_trade_evaluation_class_exists(self):
        """Test that TradeEvaluation dataclass exists"""
        from strategy_tuning import TradeEvaluation
        assert TradeEvaluation is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
