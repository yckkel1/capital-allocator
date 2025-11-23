"""
Tests for capital scaling and half Kelly position sizing

Validates that position sizes scale appropriately with capital to manage risk
"""
import pytest
from decimal import Decimal
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'scripts'))


class TestCapitalScalingAdjustment:
    """Test capital_scaling_adjustment function"""

    def test_small_capital_no_scaling(self):
        """Small capital (<$10k) should have no scaling (factor = 1.0)"""
        from scripts.generate_signal import capital_scaling_adjustment

        assert capital_scaling_adjustment(1_000) == 1.0
        assert capital_scaling_adjustment(5_000) == 1.0
        assert capital_scaling_adjustment(9_999) == 1.0

    def test_10k_to_50k_gradual_scaling(self):
        """Capital $10k-$50k should scale from 1.0 to 0.75"""
        from scripts.generate_signal import capital_scaling_adjustment

        # At exactly $10k
        assert abs(capital_scaling_adjustment(10_000) - 1.0) < 0.01

        # At exactly $50k
        assert abs(capital_scaling_adjustment(50_000) - 0.75) < 0.01

        # Midpoint $30k should be around 0.875
        factor_30k = capital_scaling_adjustment(30_000)
        assert 0.85 < factor_30k < 0.90

    def test_50k_to_200k_aggressive_scaling(self):
        """Capital $50k-$200k should scale from 0.75 to 0.50"""
        from scripts.generate_signal import capital_scaling_adjustment

        # At exactly $50k
        assert abs(capital_scaling_adjustment(50_000) - 0.75) < 0.01

        # At exactly $200k
        assert abs(capital_scaling_adjustment(200_000) - 0.50) < 0.01

        # Midpoint $125k should be around 0.625
        factor_125k = capital_scaling_adjustment(125_000)
        assert 0.60 < factor_125k < 0.65

    def test_large_capital_minimum_scaling(self):
        """Capital >$200k should approach 0.35 asymptotically"""
        from scripts.generate_signal import capital_scaling_adjustment

        # At $200k should be 0.50
        assert abs(capital_scaling_adjustment(200_000) - 0.50) < 0.01

        # At $500k should be lower
        factor_500k = capital_scaling_adjustment(500_000)
        assert 0.35 <= factor_500k <= 0.45

        # At $1M should approach 0.35
        factor_1m = capital_scaling_adjustment(1_000_000)
        assert 0.35 <= factor_1m <= 0.40

        # Should never go below 0.35
        factor_10m = capital_scaling_adjustment(10_000_000)
        assert factor_10m >= 0.35

    def test_scaling_is_monotonic_decreasing(self):
        """Scaling factor should decrease as capital increases"""
        from scripts.generate_signal import capital_scaling_adjustment

        previous_factor = 1.0
        for capital in [1_000, 5_000, 10_000, 25_000, 50_000, 100_000, 200_000, 500_000, 1_000_000]:
            current_factor = capital_scaling_adjustment(capital)
            assert current_factor <= previous_factor, (
                f"Scaling should decrease with capital, but at ${capital:,} "
                f"factor {current_factor:.3f} > previous {previous_factor:.3f}"
            )
            previous_factor = current_factor


class TestCapitalScalingImpact:
    """Test the impact of capital scaling on actual allocations"""

    def test_allocation_scaling_small_capital(self):
        """With small capital, 80% allocation should remain 80%"""
        from scripts.generate_signal import capital_scaling_adjustment

        capital = 5_000
        base_allocation = 0.8
        scale_factor = capital_scaling_adjustment(capital)
        final_allocation = base_allocation * scale_factor

        assert abs(final_allocation - 0.8) < 0.01  # Should be ~80%

    def test_allocation_scaling_medium_capital(self):
        """With medium capital, 80% allocation should be reduced"""
        from scripts.generate_signal import capital_scaling_adjustment

        capital = 100_000
        base_allocation = 0.8
        scale_factor = capital_scaling_adjustment(capital)
        final_allocation = base_allocation * scale_factor

        # At $100k, scale factor ~0.625, so 80% becomes ~50%
        assert 0.45 < final_allocation < 0.55

    def test_allocation_scaling_large_capital(self):
        """With large capital, 80% allocation should be heavily reduced"""
        from scripts.generate_signal import capital_scaling_adjustment

        capital = 500_000
        base_allocation = 0.8
        scale_factor = capital_scaling_adjustment(capital)
        final_allocation = base_allocation * scale_factor

        # At $500k, scale factor ~0.35-0.40, so 80% becomes ~28-32%
        assert 0.25 < final_allocation < 0.35

    def test_absolute_risk_comparison(self):
        """Verify that absolute risk is more reasonable with scaling"""
        from scripts.generate_signal import capital_scaling_adjustment

        # Same 80% base allocation at different capital levels
        base_allocation = 0.8
        market_volatility = 0.10  # 10% potential drop

        # Small capital
        small_capital = 5_000
        small_scale = capital_scaling_adjustment(small_capital)
        small_position = small_capital * base_allocation * small_scale
        small_risk = small_position * market_volatility

        # Large capital
        large_capital = 500_000
        large_scale = capital_scaling_adjustment(large_capital)
        large_position = large_capital * base_allocation * large_scale
        large_risk = large_position * market_volatility

        # With scaling, large capital risk should be <100x small capital risk
        # (Without scaling it would be 100x)
        risk_ratio = large_risk / small_risk
        assert risk_ratio < 50, (
            f"Risk ratio {risk_ratio:.1f}x is too high. "
            f"Small risk: ${small_risk:.0f}, Large risk: ${large_risk:.0f}"
        )

        print(f"✓ Capital scaling reduces risk appropriately:")
        print(f"  Small capital ($5k): Position ${small_position:,.0f}, Risk ${small_risk:,.0f}")
        print(f"  Large capital ($500k): Position ${large_position:,.0f}, Risk ${large_risk:,.0f}")
        print(f"  Risk ratio: {risk_ratio:.1f}x (vs 100x without scaling)")


class TestHalfKellyCalculation:
    """Test half Kelly calculation (note: requires mock data)"""

    def test_half_kelly_with_insufficient_data(self):
        """Half Kelly should default to 0.5 with insufficient data"""
        from scripts.generate_signal import calculate_half_kelly
        from unittest.mock import MagicMock
        from datetime import date

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.all.return_value = []

        half_kelly = calculate_half_kelly(mock_db, date(2025, 1, 1))
        assert half_kelly == 0.5

    def test_half_kelly_bounds(self):
        """Half Kelly should be clamped between 0.1 and 0.8"""
        from scripts.generate_signal import calculate_half_kelly
        from unittest.mock import MagicMock, Mock
        from datetime import date

        # Mock high win rate scenario
        mock_db = MagicMock()
        mock_signals = []

        # Create 20 winning trades
        for i in range(20):
            signal = Mock()
            signal.features_used = {
                'action': 'BUY',
                'confidence_score': 0.9  # High confidence = wins
            }
            mock_signals.append(signal)

        mock_db.query.return_value.filter.return_value.all.return_value = mock_signals

        half_kelly = calculate_half_kelly(mock_db, date(2025, 1, 1))

        # Should be clamped to max 0.8
        assert 0.1 <= half_kelly <= 0.8


class TestIntegratedCapitalScaling:
    """Integration tests for capital scaling in real scenarios"""

    def test_example_small_to_large_capital_journey(self):
        """Simulate capital growth and verify scaling behavior"""
        from scripts.generate_signal import capital_scaling_adjustment

        print("\n📊 Capital Growth Journey - Allocation Scaling:")
        print(f"{'Capital':>12} | {'Scale Factor':>12} | {'80% Becomes':>12} | {'Position $':>12}")
        print("-" * 60)

        for capital in [1_000, 5_000, 10_000, 25_000, 50_000, 100_000, 200_000, 500_000]:
            scale = capital_scaling_adjustment(capital)
            allocation = 0.8 * scale
            position = capital * allocation

            print(f"${capital:>10,} | {scale:>12.3f} | {allocation*100:>11.1f}% | ${position:>10,.0f}")

        # Assertions
        assert capital_scaling_adjustment(1_000) == 1.0
        assert capital_scaling_adjustment(500_000) < 0.40


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
