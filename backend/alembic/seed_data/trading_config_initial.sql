-- Initial trading configuration
-- Generated on: 2025-11-22 20:44:16
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
  'initial_deployment',
  'Default configuration for initial deployment'
)
ON CONFLICT DO NOTHING;
