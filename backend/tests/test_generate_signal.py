"""
Unit tests for scripts/generate_signal.py (REFACTORED)
Tests enhanced signal generation logic with modular structure
"""
import pytest
from unittest.mock import Mock
import pandas as pd
import numpy as np
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'generate-signal'))

from technical_indicators import calculate_rsi, calculate_bollinger_bands
from regime_detection import detect_regime_transition
from risk_assessment import calculate_confidence_score
from asset_ranking import rank_assets


class TestCalculateRSI:
    """Test RSI calculation"""

    def test_rsi_oversold(self):
        """Test RSI calculation for oversold condition"""
        prices = pd.Series([100 - i * 0.5 for i in range(20)])
        rsi = calculate_rsi(prices, period=14)
        assert rsi < 50

    def test_rsi_overbought(self):
        """Test RSI calculation for overbought condition"""
        prices = pd.Series([100 + i * 0.5 for i in range(20)])
        rsi = calculate_rsi(prices, period=14)
        assert rsi > 50

    def test_rsi_insufficient_data(self):
        """Test RSI with insufficient data returns neutral"""
        prices = pd.Series([100, 101, 102])
        rsi = calculate_rsi(prices, period=14)
        assert rsi == 50.0


class TestCalculateBollingerBands:
    """Test Bollinger Bands calculation"""

    def test_bollinger_position_above_upper(self):
        """Test position when price is near upper band"""
        prices = pd.Series([100] * 19 + [105])
        bb = calculate_bollinger_bands(prices, period=20, num_std=2.0)
        assert bb['position'] > 0.5

    def test_bollinger_position_below_lower(self):
        """Test position when price is near lower band"""
        prices = pd.Series([100] * 19 + [95])
        bb = calculate_bollinger_bands(prices, period=20, num_std=2.0)
        assert bb['position'] < -0.5


class TestDetectRegimeTransition:
    """Test regime transition detection"""

    def test_turning_bullish(self):
        """Test detection of bullish transition"""
        mock_config = Mock()
        mock_config.regime_transition_threshold = 0.15
        mock_config.regime_bullish_threshold = 0.3
        mock_config.momentum_loss_threshold = -0.15
        mock_config.momentum_gain_threshold = 0.15

        transition = detect_regime_transition(0.2, -0.2, mock_config)
        assert transition == 'turning_bullish'

    def test_stable(self):
        """Test stable regime"""
        mock_config = Mock()
        mock_config.regime_transition_threshold = 0.15
        mock_config.regime_bullish_threshold = 0.3
        mock_config.momentum_loss_threshold = -0.15
        mock_config.momentum_gain_threshold = 0.15

        transition = detect_regime_transition(0.35, 0.33, mock_config)
        assert transition == 'stable'


class TestCalculateConfidenceScore:
    """Test confidence score calculation"""

    def test_high_regime_high_confidence(self):
        """Test that strong regime gives high confidence"""
        mock_config = Mock()
        mock_config.regime_confidence_divisor = 1.0
        mock_config.risk_penalty_min = 40.0
        mock_config.risk_penalty_max = 80.0
        mock_config.consistency_bonus = 0.1
        mock_config.trend_consistency_threshold = 1.2
        mock_config.mean_reversion_base_confidence = 0.6
        mock_config.risk_penalty_multiplier = 0.3

        confidence = calculate_confidence_score(
            regime_score=0.8,
            risk_score=30,
            trend_consistency=1.5,
            mean_reversion_signal=False,
            config=mock_config
        )
        assert confidence > 0.7

    def test_high_risk_reduces_confidence(self):
        """Test that high risk reduces confidence"""
        mock_config = Mock()
        mock_config.regime_confidence_divisor = 1.0
        mock_config.risk_penalty_min = 40.0
        mock_config.risk_penalty_max = 80.0
        mock_config.consistency_bonus = 0.1
        mock_config.trend_consistency_threshold = 1.2
        mock_config.mean_reversion_base_confidence = 0.6
        mock_config.risk_penalty_multiplier = 0.3

        low_risk_conf = calculate_confidence_score(0.5, 30, 1.0, False, mock_config)
        high_risk_conf = calculate_confidence_score(0.5, 80, 1.0, False, mock_config)
        assert low_risk_conf > high_risk_conf


class TestRankAssets:
    """Test rank_assets function with mean reversion"""

    def test_oversold_asset_gets_bonus(self):
        """Test that oversold assets get ranking bonus"""
        mock_config = Mock()
        mock_config.rsi_oversold_threshold = 30.0
        mock_config.bb_oversold_threshold = -0.6
        mock_config.rsi_mild_oversold = 40.0
        mock_config.bb_mild_oversold = -0.4
        mock_config.rsi_overbought_threshold = 70.0
        mock_config.bb_overbought_threshold = 0.6
        mock_config.momentum_weight = 0.6
        mock_config.price_momentum_weight = 0.4
        mock_config.oversold_strong_bonus = 0.5
        mock_config.oversold_mild_bonus = 0.2
        mock_config.overbought_penalty = -0.3
        mock_config.trend_aligned_multiplier = 1.2
        mock_config.trend_mixed_multiplier = 1.0

        features = {
            'SPY': {
                'returns_5d': 0.01,
                'returns_20d': 0.02,
                'returns_60d': 0.04,
                'volatility': 0.01,
                'price_vs_sma20': 0.01,
                'price_vs_sma50': 0.01,
                'rsi': 25.0,
                'bollinger_position': -0.7
            },
            'QQQ': {
                'returns_5d': 0.01,
                'returns_20d': 0.02,
                'returns_60d': 0.04,
                'volatility': 0.01,
                'price_vs_sma20': 0.01,
                'price_vs_sma50': 0.01,
                'rsi': 50.0,
                'bollinger_position': 0.0
            }
        }

        scores = rank_assets(features, mock_config)
        assert scores['SPY'] > scores['QQQ']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
