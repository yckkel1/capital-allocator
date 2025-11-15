"""
Unit tests for scripts/generate_signal.py
Tests enhanced signal generation logic with mean reversion, adaptive thresholds, and confidence scoring
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import date, datetime, timedelta
import pandas as pd
import numpy as np
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'scripts'))


class TestCalculateRSI:
    """Test RSI calculation"""

    def test_rsi_oversold(self):
        """Test RSI calculation for oversold condition"""
        from scripts.generate_signal import calculate_rsi

        # Create declining prices (oversold)
        prices = pd.Series([100 - i * 0.5 for i in range(20)])
        rsi = calculate_rsi(prices, period=14)

        assert rsi < 50  # Should be below neutral

    def test_rsi_overbought(self):
        """Test RSI calculation for overbought condition"""
        from scripts.generate_signal import calculate_rsi

        # Create rising prices (overbought)
        prices = pd.Series([100 + i * 0.5 for i in range(20)])
        rsi = calculate_rsi(prices, period=14)

        assert rsi > 50  # Should be above neutral

    def test_rsi_neutral(self):
        """Test RSI calculation for neutral condition"""
        from scripts.generate_signal import calculate_rsi

        # Create sideways prices
        prices = pd.Series([100 + (i % 3 - 1) * 0.1 for i in range(20)])
        rsi = calculate_rsi(prices, period=14)

        assert 30 < rsi < 70  # Should be in neutral range

    def test_rsi_insufficient_data(self):
        """Test RSI with insufficient data returns neutral"""
        from scripts.generate_signal import calculate_rsi

        prices = pd.Series([100, 101, 102])
        rsi = calculate_rsi(prices, period=14)

        assert rsi == 50.0  # Default neutral

    def test_rsi_all_gains(self):
        """Test RSI when all gains (no losses)"""
        from scripts.generate_signal import calculate_rsi

        prices = pd.Series([100 + i for i in range(20)])
        rsi = calculate_rsi(prices, period=14)

        assert rsi == 100.0  # Max RSI when no losses


class TestCalculateBollingerBands:
    """Test Bollinger Bands calculation"""

    def test_bollinger_position_above_upper(self):
        """Test position when price is near upper band"""
        from scripts.generate_signal import calculate_bollinger_bands

        # Price at upper band
        prices = pd.Series([100] * 19 + [105])
        bb = calculate_bollinger_bands(prices, period=20, num_std=2.0)

        assert bb['position'] > 0.5  # Above middle

    def test_bollinger_position_below_lower(self):
        """Test position when price is near lower band"""
        from scripts.generate_signal import calculate_bollinger_bands

        # Price at lower band
        prices = pd.Series([100] * 19 + [95])
        bb = calculate_bollinger_bands(prices, period=20, num_std=2.0)

        assert bb['position'] < -0.5  # Below middle

    def test_bollinger_position_at_middle(self):
        """Test position when price is at middle"""
        from scripts.generate_signal import calculate_bollinger_bands

        prices = pd.Series([100] * 20)
        bb = calculate_bollinger_bands(prices, period=20, num_std=2.0)

        assert abs(bb['position']) < 0.1  # At middle

    def test_bollinger_insufficient_data(self):
        """Test with insufficient data"""
        from scripts.generate_signal import calculate_bollinger_bands

        prices = pd.Series([100, 101])
        bb = calculate_bollinger_bands(prices, period=20)

        assert bb['position'] == 0  # Default when insufficient data

    def test_bollinger_bands_structure(self):
        """Test that all bands are returned"""
        from scripts.generate_signal import calculate_bollinger_bands

        prices = pd.Series([100 + i * 0.1 for i in range(25)])
        bb = calculate_bollinger_bands(prices, period=20)

        assert 'upper' in bb
        assert 'lower' in bb
        assert 'middle' in bb
        assert 'position' in bb
        assert bb['upper'] > bb['middle'] > bb['lower']


class TestDetectRegimeTransition:
    """Test regime transition detection"""

    def test_turning_bullish(self):
        """Test detection of bullish transition"""
        from scripts.generate_signal import detect_regime_transition

        transition = detect_regime_transition(current_regime_score=0.2, previous_regime_score=-0.2)
        assert transition == 'turning_bullish'

    def test_turning_bearish(self):
        """Test detection of bearish transition"""
        from scripts.generate_signal import detect_regime_transition

        transition = detect_regime_transition(current_regime_score=-0.2, previous_regime_score=0.2)
        assert transition == 'turning_bearish'

    def test_losing_momentum(self):
        """Test detection of losing momentum"""
        from scripts.generate_signal import detect_regime_transition

        transition = detect_regime_transition(current_regime_score=0.35, previous_regime_score=0.55)
        assert transition == 'losing_momentum'

    def test_gaining_momentum(self):
        """Test detection of gaining momentum"""
        from scripts.generate_signal import detect_regime_transition

        transition = detect_regime_transition(current_regime_score=0.3, previous_regime_score=0.1)
        assert transition == 'gaining_momentum'

    def test_stable(self):
        """Test stable regime"""
        from scripts.generate_signal import detect_regime_transition

        transition = detect_regime_transition(current_regime_score=0.35, previous_regime_score=0.33)
        assert transition == 'stable'

    def test_no_previous_score(self):
        """Test with no previous score"""
        from scripts.generate_signal import detect_regime_transition

        transition = detect_regime_transition(current_regime_score=0.35, previous_regime_score=None)
        assert transition == 'stable'


class TestCalculateAdaptiveThreshold:
    """Test adaptive threshold calculation"""

    def test_high_volatility_increases_threshold(self):
        """Test that high volatility increases threshold"""
        from scripts.generate_signal import calculate_adaptive_threshold

        base = 0.3
        threshold = calculate_adaptive_threshold(base, current_volatility=0.02,
                                                  base_volatility=0.01, adjustment_factor=0.4)
        assert threshold > base  # Higher vol = higher threshold

    def test_low_volatility_decreases_threshold(self):
        """Test that low volatility decreases threshold"""
        from scripts.generate_signal import calculate_adaptive_threshold

        base = 0.3
        threshold = calculate_adaptive_threshold(base, current_volatility=0.005,
                                                  base_volatility=0.01, adjustment_factor=0.4)
        assert threshold < base  # Lower vol = lower threshold

    def test_normal_volatility_maintains_threshold(self):
        """Test that normal volatility keeps threshold similar"""
        from scripts.generate_signal import calculate_adaptive_threshold

        base = 0.3
        threshold = calculate_adaptive_threshold(base, current_volatility=0.01,
                                                  base_volatility=0.01, adjustment_factor=0.4)
        assert abs(threshold - base) < 0.01  # Similar to base

    def test_threshold_clamped_to_range(self):
        """Test that threshold is clamped to valid range"""
        from scripts.generate_signal import calculate_adaptive_threshold

        base = 0.3
        # Extreme high volatility
        threshold = calculate_adaptive_threshold(base, current_volatility=0.1,
                                                  base_volatility=0.01, adjustment_factor=0.4)
        assert threshold <= base * 1.5  # Clamped to max 1.5x

        # Extreme low volatility
        threshold = calculate_adaptive_threshold(base, current_volatility=0.001,
                                                  base_volatility=0.01, adjustment_factor=0.4)
        assert threshold >= base * 0.7  # Clamped to min 0.7x


class TestCalculateConfidenceScore:
    """Test confidence score calculation"""

    def test_high_regime_high_confidence(self):
        """Test that strong regime gives high confidence"""
        from scripts.generate_signal import calculate_confidence_score

        confidence = calculate_confidence_score(regime_score=0.8, risk_score=30,
                                                 trend_consistency=1.5, mean_reversion_signal=False)
        assert confidence > 0.7

    def test_high_risk_reduces_confidence(self):
        """Test that high risk reduces confidence"""
        from scripts.generate_signal import calculate_confidence_score

        low_risk_conf = calculate_confidence_score(regime_score=0.5, risk_score=30,
                                                    trend_consistency=1.0, mean_reversion_signal=False)
        high_risk_conf = calculate_confidence_score(regime_score=0.5, risk_score=80,
                                                     trend_consistency=1.0, mean_reversion_signal=False)
        assert low_risk_conf > high_risk_conf

    def test_trend_consistency_bonus(self):
        """Test that trend consistency adds bonus"""
        from scripts.generate_signal import calculate_confidence_score

        no_bonus = calculate_confidence_score(regime_score=0.4, risk_score=40,
                                               trend_consistency=1.0, mean_reversion_signal=False)
        with_bonus = calculate_confidence_score(regime_score=0.4, risk_score=40,
                                                 trend_consistency=1.5, mean_reversion_signal=False)
        assert with_bonus > no_bonus

    def test_mean_reversion_moderate_confidence(self):
        """Test that mean reversion signals have moderate confidence"""
        from scripts.generate_signal import calculate_confidence_score

        confidence = calculate_confidence_score(regime_score=0.1, risk_score=40,
                                                 trend_consistency=1.0, mean_reversion_signal=True)
        assert 0.4 < confidence < 0.8

    def test_confidence_bounded(self):
        """Test that confidence is bounded 0-1"""
        from scripts.generate_signal import calculate_confidence_score

        confidence = calculate_confidence_score(regime_score=2.0, risk_score=0,
                                                 trend_consistency=2.0, mean_reversion_signal=False)
        assert 0 <= confidence <= 1.0


class TestCalculatePositionSize:
    """Test position sizing by confidence"""

    def test_full_confidence_full_size(self):
        """Test that full confidence gives full allocation"""
        from scripts.generate_signal import calculate_position_size

        size = calculate_position_size(base_allocation=0.8, confidence=1.0,
                                        confidence_scaling_factor=0.5)
        assert abs(size - 0.8) < 0.01  # Full allocation

    def test_low_confidence_reduced_size(self):
        """Test that low confidence reduces allocation"""
        from scripts.generate_signal import calculate_position_size

        size = calculate_position_size(base_allocation=0.8, confidence=0.5,
                                        confidence_scaling_factor=0.5)
        assert size < 0.8  # Reduced allocation

    def test_zero_confidence_minimum_size(self):
        """Test minimum size with zero confidence"""
        from scripts.generate_signal import calculate_position_size

        size = calculate_position_size(base_allocation=0.8, confidence=0.0,
                                        confidence_scaling_factor=0.5)
        assert size == 0.8 * 0.5  # 50% of base


class TestCheckCircuitBreaker:
    """Test circuit breaker functionality"""

    @patch('scripts.generate_signal.SessionLocal')
    def test_circuit_breaker_not_triggered(self, mock_session):
        """Test circuit breaker not triggered with low drawdown"""
        from scripts.generate_signal import check_circuit_breaker

        mock_db = MagicMock()
        mock_perf = [
            Mock(total_value=10000),
            Mock(total_value=10100),
            Mock(total_value=10050)
        ]
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = mock_perf

        triggered, dd = check_circuit_breaker(mock_db, date(2025, 11, 15), 0.10)

        assert not triggered
        assert dd < 0.10

    @patch('scripts.generate_signal.SessionLocal')
    def test_circuit_breaker_triggered(self, mock_session):
        """Test circuit breaker triggered with high drawdown"""
        from scripts.generate_signal import check_circuit_breaker

        mock_db = MagicMock()
        mock_perf = [
            Mock(total_value=10000),
            Mock(total_value=10500),  # Peak
            Mock(total_value=9000)    # 14.3% drawdown
        ]
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = mock_perf

        triggered, dd = check_circuit_breaker(mock_db, date(2025, 11, 15), 0.10)

        assert triggered
        assert dd >= 0.10

    @patch('scripts.generate_signal.SessionLocal')
    def test_circuit_breaker_insufficient_data(self, mock_session):
        """Test circuit breaker with insufficient data"""
        from scripts.generate_signal import check_circuit_breaker

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []

        triggered, dd = check_circuit_breaker(mock_db, date(2025, 11, 15), 0.10)

        assert not triggered
        assert dd == 0.0


class TestDetectMeanReversionOpportunity:
    """Test mean reversion opportunity detection"""

    def test_oversold_bounce_detected(self):
        """Test detection of oversold bounce opportunity"""
        from scripts.generate_signal import detect_mean_reversion_opportunity

        features = {
            'SPY': {'rsi': 25.0, 'bollinger_position': -0.8},  # Oversold
            'QQQ': {'rsi': 55.0, 'bollinger_position': 0.1},
            'DIA': {'rsi': 50.0, 'bollinger_position': 0.0}
        }

        has_opp, opp_type, assets = detect_mean_reversion_opportunity(features, regime_score=0.1)

        assert has_opp
        assert opp_type == 'oversold_bounce'
        assert 'SPY' in assets

    def test_overbought_reversal_detected(self):
        """Test detection of overbought reversal"""
        from scripts.generate_signal import detect_mean_reversion_opportunity

        features = {
            'SPY': {'rsi': 75.0, 'bollinger_position': 0.9},  # Overbought
            'QQQ': {'rsi': 50.0, 'bollinger_position': 0.0},
            'DIA': {'rsi': 50.0, 'bollinger_position': 0.0}
        }

        has_opp, opp_type, assets = detect_mean_reversion_opportunity(features, regime_score=0.1)

        assert has_opp
        assert opp_type == 'overbought_reversal'
        assert 'SPY' in assets

    def test_no_opportunity_in_strong_trend(self):
        """Test no mean reversion in strong trend"""
        from scripts.generate_signal import detect_mean_reversion_opportunity

        features = {
            'SPY': {'rsi': 25.0, 'bollinger_position': -0.8},  # Oversold
            'QQQ': {'rsi': 50.0, 'bollinger_position': 0.0},
            'DIA': {'rsi': 50.0, 'bollinger_position': 0.0}
        }

        # Strong trend (regime_score > 0.4) - should not trigger mean reversion
        has_opp, opp_type, assets = detect_mean_reversion_opportunity(features, regime_score=0.5)

        assert not has_opp

    def test_no_opportunity_when_neutral(self):
        """Test no opportunity when all assets are neutral"""
        from scripts.generate_signal import detect_mean_reversion_opportunity

        features = {
            'SPY': {'rsi': 50.0, 'bollinger_position': 0.0},
            'QQQ': {'rsi': 55.0, 'bollinger_position': 0.1},
            'DIA': {'rsi': 48.0, 'bollinger_position': -0.1}
        }

        has_opp, opp_type, assets = detect_mean_reversion_opportunity(features, regime_score=0.1)

        assert not has_opp


class TestDecideActionEnhanced:
    """Test enhanced decide_action function"""

    @patch('scripts.generate_signal.trading_config')
    def test_circuit_breaker_triggers_sell(self, mock_config):
        """Test that circuit breaker triggers sell"""
        from scripts.generate_signal import decide_action

        mock_config.circuit_breaker_reduction = 0.5
        mock_config.mean_reversion_allocation = 0.4
        mock_config.allocation_neutral = 0.2
        mock_config.risk_high_threshold = 70.0
        mock_config.risk_medium_threshold = 40.0
        mock_config.allocation_high_risk = 0.3
        mock_config.allocation_medium_risk = 0.5
        mock_config.allocation_low_risk = 0.8

        action, pct, signal_type = decide_action(
            regime_score=0.4, risk_score=30, has_holdings=True,
            mean_reversion_opportunity=(False, None, []),
            adaptive_bullish_threshold=0.3, adaptive_bearish_threshold=-0.3,
            circuit_breaker_triggered=True
        )

        assert action == "SELL"
        assert signal_type == "circuit_breaker"

    @patch('scripts.generate_signal.trading_config')
    def test_mean_reversion_buy(self, mock_config):
        """Test mean reversion buy in neutral regime"""
        from scripts.generate_signal import decide_action

        mock_config.mean_reversion_allocation = 0.4
        mock_config.allocation_neutral = 0.2

        action, pct, signal_type = decide_action(
            regime_score=0.1, risk_score=40, has_holdings=False,
            mean_reversion_opportunity=(True, 'oversold_bounce', ['SPY']),
            adaptive_bullish_threshold=0.3, adaptive_bearish_threshold=-0.3,
            circuit_breaker_triggered=False
        )

        assert action == "BUY"
        assert pct == 0.4
        assert signal_type == "mean_reversion_oversold"

    @patch('scripts.generate_signal.trading_config')
    def test_bullish_momentum_buy(self, mock_config):
        """Test bullish momentum buy"""
        from scripts.generate_signal import decide_action

        mock_config.risk_high_threshold = 70.0
        mock_config.risk_medium_threshold = 40.0
        mock_config.allocation_low_risk = 0.8

        action, pct, signal_type = decide_action(
            regime_score=0.4, risk_score=30, has_holdings=False,
            mean_reversion_opportunity=(False, None, []),
            adaptive_bullish_threshold=0.3, adaptive_bearish_threshold=-0.3,
            circuit_breaker_triggered=False
        )

        assert action == "BUY"
        assert pct == 0.8
        assert signal_type == "bullish_momentum"


class TestCalculateRegime:
    """Test calculate_regime function"""

    def test_bullish_regime(self):
        """Test detection of bullish regime"""
        from scripts.generate_signal import calculate_regime

        features = {
            'SPY': {
                'returns_5d': 0.02,
                'returns_20d': 0.05,
                'returns_60d': 0.10,
                'price_vs_sma20': 0.03,
                'price_vs_sma50': 0.05
            }
        }

        regime_score = calculate_regime(features)

        assert regime_score > 0

    def test_bearish_regime(self):
        """Test detection of bearish regime"""
        from scripts.generate_signal import calculate_regime

        features = {
            'SPY': {
                'returns_5d': -0.02,
                'returns_20d': -0.05,
                'returns_60d': -0.10,
                'price_vs_sma20': -0.03,
                'price_vs_sma50': -0.05
            }
        }

        regime_score = calculate_regime(features)

        assert regime_score < 0

    def test_neutral_regime(self):
        """Test detection of neutral regime"""
        from scripts.generate_signal import calculate_regime

        features = {
            'SPY': {
                'returns_5d': 0.001,
                'returns_20d': -0.001,
                'returns_60d': 0.001,
                'price_vs_sma20': 0.001,
                'price_vs_sma50': -0.001
            }
        }

        regime_score = calculate_regime(features)

        assert abs(regime_score) < 0.1


class TestCalculateRiskScore:
    """Test calculate_risk_score function"""

    def test_low_risk_score(self):
        """Test low risk score calculation"""
        from scripts.generate_signal import calculate_risk_score

        features = {
            'SPY': {'volatility': 0.005, 'returns_60d': 0.10},
            'QQQ': {'volatility': 0.006, 'returns_60d': 0.08},
            'DIA': {'volatility': 0.004, 'returns_60d': 0.05}
        }

        risk_score = calculate_risk_score(features)

        assert risk_score < 50

    def test_high_risk_score(self):
        """Test high risk score calculation"""
        from scripts.generate_signal import calculate_risk_score

        features = {
            'SPY': {'volatility': 0.025, 'returns_60d': 0.05},
            'QQQ': {'volatility': 0.030, 'returns_60d': 0.05},
            'DIA': {'volatility': 0.028, 'returns_60d': 0.05}
        }

        risk_score = calculate_risk_score(features)

        assert risk_score > 70

    def test_risk_score_bounds(self):
        """Test that risk score is bounded between 0 and 100"""
        from scripts.generate_signal import calculate_risk_score

        features = {
            'SPY': {'volatility': 0.1, 'returns_60d': 0.05},
        }

        risk_score = calculate_risk_score(features)

        assert 0 <= risk_score <= 100


class TestRankAssets:
    """Test rank_assets function with mean reversion"""

    @patch('scripts.generate_signal.trading_config')
    def test_oversold_asset_gets_bonus(self, mock_config):
        """Test that oversold assets get ranking bonus"""
        from scripts.generate_signal import rank_assets

        mock_config.rsi_oversold_threshold = 30.0
        mock_config.rsi_overbought_threshold = 70.0
        mock_config.momentum_weight = 0.6
        mock_config.price_momentum_weight = 0.4

        features = {
            'SPY': {
                'returns_5d': 0.01,
                'returns_20d': 0.02,
                'returns_60d': 0.04,
                'volatility': 0.01,
                'price_vs_sma20': 0.01,
                'price_vs_sma50': 0.01,
                'rsi': 25.0,  # Oversold
                'bollinger_position': -0.7
            },
            'QQQ': {
                'returns_5d': 0.01,
                'returns_20d': 0.02,
                'returns_60d': 0.04,
                'volatility': 0.01,
                'price_vs_sma20': 0.01,
                'price_vs_sma50': 0.01,
                'rsi': 50.0,  # Neutral
                'bollinger_position': 0.0
            }
        }

        scores = rank_assets(features)

        # Oversold asset should have higher score due to mean reversion bonus
        assert scores['SPY'] > scores['QQQ']

    @patch('scripts.generate_signal.trading_config')
    def test_overbought_asset_gets_penalty(self, mock_config):
        """Test that overbought assets get ranking penalty"""
        from scripts.generate_signal import rank_assets

        mock_config.rsi_oversold_threshold = 30.0
        mock_config.rsi_overbought_threshold = 70.0
        mock_config.momentum_weight = 0.6
        mock_config.price_momentum_weight = 0.4

        features = {
            'SPY': {
                'returns_5d': 0.01,
                'returns_20d': 0.02,
                'returns_60d': 0.04,
                'volatility': 0.01,
                'price_vs_sma20': 0.01,
                'price_vs_sma50': 0.01,
                'rsi': 75.0,  # Overbought
                'bollinger_position': 0.7
            },
            'QQQ': {
                'returns_5d': 0.01,
                'returns_20d': 0.02,
                'returns_60d': 0.04,
                'volatility': 0.01,
                'price_vs_sma20': 0.01,
                'price_vs_sma50': 0.01,
                'rsi': 50.0,  # Neutral
                'bollinger_position': 0.0
            }
        }

        scores = rank_assets(features)

        # Overbought asset should have lower score due to penalty
        assert scores['SPY'] < scores['QQQ']


class TestAllocateDiversified:
    """Test allocate_diversified function"""

    def test_allocate_to_three_positive_assets(self):
        """Test diversified allocation across three positive assets"""
        from scripts.generate_signal import allocate_diversified

        asset_scores = {
            'SPY': 3.5,
            'QQQ': 3.0,
            'DIA': 2.5
        }

        allocations = allocate_diversified(asset_scores, 1000.0)

        assert allocations['SPY'] > 0
        assert allocations['QQQ'] > 0
        assert allocations['DIA'] > 0

        total = sum(allocations.values())
        assert abs(total - 1000.0) < 0.01

        assert allocations['SPY'] <= 500

    def test_allocate_to_two_positive_assets(self):
        """Test allocation when only two assets are positive"""
        from scripts.generate_signal import allocate_diversified

        asset_scores = {
            'SPY': 3.5,
            'QQQ': 3.0,
            'DIA': -0.5
        }

        allocations = allocate_diversified(asset_scores, 1000.0)

        assert allocations['SPY'] == 650.0
        assert allocations['QQQ'] == 350.0
        assert allocations['DIA'] == 0.0

    def test_allocate_to_single_positive_asset(self):
        """Test allocation when only one asset is positive"""
        from scripts.generate_signal import allocate_diversified

        asset_scores = {
            'SPY': 3.5,
            'QQQ': -0.5,
            'DIA': -0.8
        }

        allocations = allocate_diversified(asset_scores, 1000.0)

        assert allocations['SPY'] == 1000.0
        assert allocations['QQQ'] == 0.0
        assert allocations['DIA'] == 0.0

    def test_allocate_no_positive_assets(self):
        """Test allocation when no assets are positive"""
        from scripts.generate_signal import allocate_diversified

        asset_scores = {
            'SPY': -0.5,
            'QQQ': -0.8,
            'DIA': -1.0
        }

        allocations = allocate_diversified(asset_scores, 1000.0)

        assert all(v == 0.0 for v in allocations.values())


class TestCalculateMultiTimeframeFeatures:
    """Test calculate_multi_timeframe_features function"""

    @patch('scripts.generate_signal.trading_config')
    def test_calculate_features_with_rsi_bb(self, mock_config):
        """Test feature calculation includes RSI and Bollinger Bands"""
        from scripts.generate_signal import calculate_multi_timeframe_features

        mock_config.bollinger_std_multiplier = 2.0

        dates = pd.date_range(end='2025-11-15', periods=100)
        prices = 580.0 + np.cumsum(np.random.randn(100) * 0.5)

        df = pd.DataFrame({
            'date': dates,
            'close': prices,
            'open': prices - 0.5,
            'high': prices + 1.0,
            'low': prices - 1.5,
            'volume': [50000000] * 100
        })

        features = calculate_multi_timeframe_features(df)

        assert 'rsi' in features
        assert 'bollinger_position' in features
        assert 'bollinger_upper' in features
        assert 'bollinger_lower' in features
        assert 0 <= features['rsi'] <= 100
        assert -1 <= features['bollinger_position'] <= 1


class TestGenerateSignalFunction:
    """Test main generate_signal function"""

    @patch('scripts.generate_signal.SessionLocal')
    @patch('scripts.generate_signal.get_trading_config')
    def test_generate_signal_existing_signal(self, mock_config, mock_session):
        """Test that existing signals are not overwritten"""
        from scripts.generate_signal import generate_signal

        mock_trading_config = Mock()
        mock_trading_config.assets = ['SPY', 'QQQ', 'DIA']
        mock_trading_config.lookback_days = 252
        mock_trading_config.daily_capital = 1000.0
        mock_config.return_value = mock_trading_config

        mock_db = MagicMock()
        mock_session.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = Mock()  # Existing signal

        generate_signal(date(2025, 11, 15))

        mock_db.add.assert_not_called()

    @patch('scripts.generate_signal.SessionLocal')
    @patch('scripts.generate_signal.get_trading_config')
    def test_generate_signal_no_data_available(self, mock_config, mock_session):
        """Test that signal generation handles no data gracefully"""
        from scripts.generate_signal import generate_signal

        mock_trading_config = Mock()
        mock_trading_config.assets = ['SPY', 'QQQ', 'DIA']
        mock_trading_config.lookback_days = 252
        mock_trading_config.daily_capital = 1000.0
        mock_config.return_value = mock_trading_config

        mock_db = MagicMock()
        mock_session.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = None  # No signal
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []  # No data

        generate_signal(date(2025, 11, 15))

        mock_db.add.assert_not_called()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
