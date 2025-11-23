-- Initial trading configuration
-- Updated on: 2025-11-23
-- This is a default configuration; tune via monthly_tuning.py after deployment

INSERT INTO trading_config (
  start_date, end_date, daily_capital, assets, lookback_days,
  regime_bullish_threshold, regime_bearish_threshold,
  risk_high_threshold, risk_medium_threshold,
  allocation_low_risk, allocation_medium_risk, allocation_high_risk,
  allocation_neutral, sell_percentage,
  momentum_weight, price_momentum_weight,
  max_drawdown_tolerance, min_sharpe_target,
  rsi_oversold_threshold, rsi_overbought_threshold,
  bollinger_std_multiplier, mean_reversion_allocation,
  volatility_adjustment_factor, base_volatility,
  min_confidence_threshold, confidence_scaling_factor,
  intramonth_drawdown_limit, circuit_breaker_reduction,
  -- Regime Transition Detection
  regime_transition_threshold, momentum_loss_threshold, momentum_gain_threshold, strong_trend_threshold,
  -- Confidence Scoring
  regime_confidence_divisor, risk_penalty_min, risk_penalty_max, trend_consistency_threshold,
  mean_reversion_base_confidence, consistency_bonus, risk_penalty_multiplier,
  confidence_bucket_high_threshold, confidence_bucket_medium_threshold,
  -- Mean Reversion Signals
  bb_oversold_threshold, bb_overbought_threshold, oversold_strong_bonus, oversold_mild_bonus,
  rsi_mild_oversold, bb_mild_oversold, overbought_penalty,
  -- Downward Pressure Detection
  price_vs_sma_threshold, high_volatility_threshold, negative_return_threshold,
  severe_pressure_threshold, moderate_pressure_threshold, severe_pressure_risk, moderate_pressure_risk,
  -- Dynamic Selling Behavior
  defensive_cash_threshold, sell_defensive_multiplier, sell_aggressive_multiplier,
  sell_moderate_pressure_multiplier, sell_bullish_risk_multiplier,
  -- Risk-Based Thresholds
  mean_reversion_max_risk, neutral_deleverage_risk, neutral_hold_risk,
  bullish_excessive_risk, extreme_risk_threshold,
  -- Asset Diversification
  diversify_top_asset_max, diversify_top_asset_min, diversify_second_asset_max, diversify_second_asset_min,
  diversify_third_asset_max, diversify_third_asset_min, two_asset_top, two_asset_second,
  -- Volatility & Normalization
  volatility_normalization_factor, stability_threshold, stability_discount_factor, correlation_risk_base, correlation_risk_multiplier,
  -- Risk Score Calculation Weights
  risk_volatility_weight, risk_correlation_weight,
  -- Indicator Periods
  rsi_period, bollinger_period,
  -- Trend Consistency
  trend_aligned_multiplier, trend_mixed_multiplier,
  -- Metadata
  created_by, notes
) VALUES (
  '2015-01-01',
  NULL,  -- end_date (currently active)
  1000.0,
  '["SPY", "QQQ", "DIA"]'::json,
  252,
  0.3,
  -0.3,
  70.0,
  40.0,
  0.8,
  0.5,
  0.3,
  0.2,
  0.7,
  0.6,
  0.4,
  15.0,
  1.0,
  30.0,
  70.0,
  2.0,
  0.4,
  0.4,
  0.01,
  0.3,
  0.5,
  0.1,
  0.5,
  -- Regime Transition Detection
  0.1, -0.15, 0.15, 0.4,
  -- Confidence Scoring
  0.5, 40.0, 60.0, 1.2,
  0.6, 0.2, 0.3,
  0.7, 0.5,
  -- Mean Reversion Signals
  -0.5, 0.5, 0.3, 0.1,
  40.0, 0.0, -0.2,
  -- Downward Pressure Detection
  -0.02, 0.015, -0.03,
  0.67, 0.50, 50.0, 45.0,
  -- Dynamic Selling Behavior
  70.0, 0.5, 1.2,
  0.6, 0.3,
  -- Risk-Based Thresholds
  60.0, 55.0, 50.0,
  65.0, 70.0,
  -- Asset Diversification
  0.50, 0.40, 0.35, 0.30,
  0.25, 0.15, 0.65, 0.35,
  -- Volatility & Normalization
  0.02, 0.05, 0.5, 30.0, 100.0,
  -- Risk Score Calculation Weights
  0.7, 0.3,
  -- Indicator Periods
  14, 20,
  -- Trend Consistency
  1.5, 1.0,
  -- Metadata
  'initial_deployment',
  'Default configuration with all tunable parameters'
)
ON CONFLICT DO NOTHING;
