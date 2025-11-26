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
  -- Regime Calculation Weights
  regime_momentum_weight, regime_sma20_weight, regime_sma50_weight,
  -- Adaptive Threshold Clamps
  adaptive_threshold_clamp_min, adaptive_threshold_clamp_max,
  -- Risk Label Thresholds
  risk_label_high_threshold, risk_label_medium_threshold,
  -- Strategy Tuning Parameters
  -- Market Condition Detection
  market_condition_r_squared_threshold, market_condition_slope_threshold,
  market_condition_choppy_r_squared, market_condition_choppy_volatility,
  -- Trade Evaluation Scoring
  score_profitable_bonus, score_sharpe_bonus, score_low_dd_bonus,
  score_all_horizons_bonus, score_two_horizons_bonus,
  score_unprofitable_penalty, score_high_dd_penalty, score_sharpe_penalty,
  score_momentum_bonus, score_choppy_penalty, score_confidence_bonus, score_mean_reversion_bonus,
  -- Tuning Decision Thresholds
  tune_aggressive_win_rate, tune_aggressive_participation, tune_aggressive_score,
  tune_conservative_win_rate, tune_conservative_dd, tune_conservative_score,
  -- Parameter Adjustment Amounts
  tune_allocation_step, tune_neutral_step, tune_risk_threshold_step, tune_sharpe_aggressive_threshold,
  -- Sell Strategy Tuning
  tune_sell_effective_threshold, tune_sell_underperform_threshold,
  tune_bearish_sell_participation, tune_high_dd_no_sell_threshold,
  tune_sell_major_adjustment, tune_sell_minor_adjustment,
  -- Confidence Tuning
  tune_low_conf_poor_threshold, tune_high_conf_strong_threshold,
  tune_confidence_threshold_step, tune_confidence_scaling_step,
  -- Mean Reversion Tuning
  tune_mr_good_threshold, tune_mr_poor_threshold, tune_rsi_threshold_step,
  -- Validation Thresholds
  validation_sharpe_tolerance, validation_dd_tolerance, validation_passing_score,
  validation_sharpe_weight, validation_drawdown_weight,
  -- Trade Evaluation DD Thresholds
  score_dd_low_threshold, score_dd_high_threshold,
  -- Parameter Tuning Boundary Limits
  tune_allocation_low_risk_max, tune_allocation_low_risk_min,
  tune_allocation_medium_risk_max, tune_allocation_medium_risk_min,
  tune_allocation_high_risk_min, tune_allocation_high_risk_max,
  tune_allocation_neutral_min, tune_allocation_neutral_max,
  tune_risk_medium_threshold_min, tune_risk_medium_threshold_max,
  tune_risk_high_threshold_min, tune_risk_high_threshold_max,
  tune_regime_bullish_threshold_max, tune_regime_bullish_threshold_min,
  tune_sell_percentage_min, tune_sell_percentage_max,
  tune_min_confidence_threshold_max, tune_confidence_scaling_factor_max,
  tune_mean_reversion_allocation_max, tune_rsi_oversold_threshold_min, tune_rsi_oversold_threshold_max,
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
  -- Regime Calculation Weights
  0.5, 0.3, 0.2,
  -- Adaptive Threshold Clamps
  0.7, 1.5,
  -- Risk Label Thresholds
  70.0, 40.0,
  -- Strategy Tuning Parameters
  -- Market Condition Detection
  0.6, 0.1, 0.3, 0.02,
  -- Trade Evaluation Scoring
  0.3, 0.2, 0.2, 0.2, 0.1,
  -0.3, -0.4, -0.2,
  0.3, -0.3, 0.1, 0.15,
  -- Tuning Decision Thresholds
  65.0, 0.5, 0.2,
  45.0, 15.0, -0.1,
  -- Parameter Adjustment Amounts
  0.1, 0.05, 5.0, 1.5,
  -- Sell Strategy Tuning
  0.7, -0.2, 0.3, 15.0, 0.15, 0.1,
  -- Confidence Tuning
  40.0, 70.0, 0.05, 0.1,
  -- Mean Reversion Tuning
  60.0, 45.0, 5.0,
  -- Validation Thresholds
  0.8, 1.2, 0.5,
  0.5, 0.5,
  -- Trade Evaluation DD Thresholds
  5.0, 20.0,
  -- Parameter Tuning Boundary Limits
  1.0, 0.5,  -- allocation_low_risk max/min
  0.7, 0.3,  -- allocation_medium_risk max/min
  0.2, 0.5,  -- allocation_high_risk_min, allocation_high_risk_max (ADDED max)
  0.1, 0.4,  -- allocation_neutral_min, allocation_neutral_max (ADDED max)
  30.0, 60.0,  -- risk_medium_threshold_min, risk_medium_threshold_max (ADDED max)
  60.0, 80.0,  -- risk_high_threshold_min, risk_high_threshold_max (ADDED max)
  0.4, 0.2,  -- regime_bullish_threshold max/min
  0.3, 0.9,  -- sell_percentage min/max
  0.5, 0.8,  -- min_confidence_threshold_max, confidence_scaling_factor_max
  0.6, 20.0, 40.0,  -- mean_reversion_allocation_max, rsi_oversold_threshold_min, rsi_oversold_threshold_max (ADDED max)
  -- Metadata
  'initial_deployment',
  'Default configuration with all tunable parameters'
)
ON CONFLICT DO NOTHING;
