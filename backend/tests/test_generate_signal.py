"""
Unit tests for scripts/generate_signal.py
Tests signal generation logic
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

        # All positive momentum should give positive regime
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

        # Should be close to zero
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

        # Low volatility = low risk
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

        # High volatility = high risk
        assert risk_score > 70

    def test_risk_score_bounds(self):
        """Test that risk score is bounded between 0 and 100"""
        from scripts.generate_signal import calculate_risk_score

        # Extreme volatility
        features = {
            'SPY': {'volatility': 0.1, 'returns_60d': 0.05},
        }

        risk_score = calculate_risk_score(features)

        assert 0 <= risk_score <= 100


class TestRankAssets:
    """Test rank_assets function"""

    def test_rank_assets_by_score(self):
        """Test that assets are ranked by composite score"""
        from scripts.generate_signal import rank_assets

        features = {
            'SPY': {
                'returns_5d': 0.02,
                'returns_20d': 0.05,
                'returns_60d': 0.10,
                'volatility': 0.01,
                'price_vs_sma20': 0.03,
                'price_vs_sma50': 0.05
            },
            'QQQ': {
                'returns_5d': 0.01,
                'returns_20d': 0.03,
                'returns_60d': 0.06,
                'volatility': 0.01,
                'price_vs_sma20': 0.02,
                'price_vs_sma50': 0.03
            }
        }

        scores = rank_assets(features)

        # SPY should have higher score
        assert scores['SPY'] > scores['QQQ']

    def test_rank_assets_trend_consistency(self):
        """Test that trend consistency is rewarded"""
        from scripts.generate_signal import rank_assets

        # All positive = consistent trend
        features_consistent = {
            'SPY': {
                'returns_5d': 0.01,
                'returns_20d': 0.02,
                'returns_60d': 0.04,
                'volatility': 0.01,
                'price_vs_sma20': 0.01,
                'price_vs_sma50': 0.01
            }
        }

        # Mixed signals = inconsistent
        features_inconsistent = {
            'QQQ': {
                'returns_5d': -0.01,
                'returns_20d': 0.02,
                'returns_60d': 0.04,
                'volatility': 0.01,
                'price_vs_sma20': 0.01,
                'price_vs_sma50': 0.01
            }
        }

        score_consistent = rank_assets(features_consistent)['SPY']
        score_inconsistent = rank_assets(features_inconsistent)['QQQ']

        # Consistent trend should have higher score
        assert score_consistent > score_inconsistent


class TestDecideAction:
    """Test decide_action function"""

    def test_buy_on_bullish_regime(self):
        """Test BUY decision on bullish regime"""
        from scripts.generate_signal import decide_action

        action, allocation = decide_action(regime_score=0.35, risk_score=30, has_holdings=False)

        assert action == "BUY"
        assert allocation > 0.5  # Should be aggressive in low risk bullish

    def test_hold_on_bearish_no_holdings(self):
        """Test HOLD on bearish regime with no holdings"""
        from scripts.generate_signal import decide_action

        action, allocation = decide_action(regime_score=-0.35, risk_score=50, has_holdings=False)

        assert action == "HOLD"
        assert allocation == 0.0

    def test_sell_on_bearish_with_holdings(self):
        """Test SELL on bearish regime with holdings"""
        from scripts.generate_signal import decide_action

        action, allocation = decide_action(regime_score=-0.35, risk_score=50, has_holdings=True)

        assert action == "SELL"
        assert allocation > 0  # Should sell some percentage

    def test_cautious_buy_on_neutral(self):
        """Test cautious buy on neutral regime"""
        from scripts.generate_signal import decide_action

        action, allocation = decide_action(regime_score=0.1, risk_score=30, has_holdings=False)

        assert action == "BUY"
        assert allocation == 0.2  # Small cautious buy

    def test_hold_on_neutral_high_risk(self):
        """Test HOLD on neutral regime with high risk"""
        from scripts.generate_signal import decide_action

        action, allocation = decide_action(regime_score=0.1, risk_score=65, has_holdings=False)

        assert action == "HOLD"
        assert allocation == 0.0

    def test_bullish_allocation_by_risk(self):
        """Test allocation varies by risk level in bullish regime"""
        from scripts.generate_signal import decide_action

        # High risk
        _, alloc_high_risk = decide_action(0.35, 75, False)
        # Medium risk
        _, alloc_medium_risk = decide_action(0.35, 50, False)
        # Low risk
        _, alloc_low_risk = decide_action(0.35, 30, False)

        assert alloc_high_risk < alloc_medium_risk < alloc_low_risk


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

        # All should have positive allocation
        assert allocations['SPY'] > 0
        assert allocations['QQQ'] > 0
        assert allocations['DIA'] > 0

        # Total should equal 1000
        total = sum(allocations.values())
        assert abs(total - 1000.0) < 0.01

        # Should respect concentration limits
        assert allocations['SPY'] <= 500  # Max 50%
        assert allocations['QQQ'] <= 350  # Max 35%

    def test_allocate_to_two_positive_assets(self):
        """Test allocation when only two assets are positive"""
        from scripts.generate_signal import allocate_diversified

        asset_scores = {
            'SPY': 3.5,
            'QQQ': 3.0,
            'DIA': -0.5  # Negative
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

        # All should be zero
        assert all(v == 0.0 for v in allocations.values())


class TestCalculateMultiTimeframeFeatures:
    """Test calculate_multi_timeframe_features function"""

    def test_calculate_features_sufficient_data(self):
        """Test feature calculation with sufficient data"""
        from scripts.generate_signal import calculate_multi_timeframe_features

        # Create test DataFrame with 100 days of data
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

        assert 'returns_5d' in features
        assert 'returns_20d' in features
        assert 'returns_60d' in features
        assert 'volatility' in features
        assert 'price_vs_sma20' in features
        assert 'price_vs_sma50' in features
        assert 'current_price' in features

    def test_calculate_features_insufficient_data(self):
        """Test feature calculation with insufficient data"""
        from scripts.generate_signal import calculate_multi_timeframe_features

        # Only 10 days of data
        dates = pd.date_range(end='2025-11-15', periods=10)
        prices = [580.0 + i for i in range(10)]

        df = pd.DataFrame({
            'date': dates,
            'close': prices,
            'open': [p - 0.5 for p in prices],
            'high': [p + 1.0 for p in prices],
            'low': [p - 1.5 for p in prices],
            'volume': [50000000] * 10
        })

        features = calculate_multi_timeframe_features(df)

        # Should handle insufficient data gracefully
        assert features['returns_5d'] != 0
        assert features['returns_20d'] == 0  # Not enough data
        assert features['returns_60d'] == 0  # Not enough data


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

        # Should not add new signal
        mock_db.add.assert_not_called()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
