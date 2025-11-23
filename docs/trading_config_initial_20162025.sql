-- Trading configuration trained via continuous backtest with monthly tuning
-- Generated: 2025-11-23 17:30:11
-- Training period: 2016-11-24 to 2025-11-21

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
  '2016-11-24', NULL,
  1000.0, '["SPY", "QQQ", "DIA"]'::json, 252,
  0.2, -0.1,
  70.0, 30.0,
  0.5, 0.3, 0.9,
  0.1, 0.3,
  0.6, 0.4,
  20.0, 0.8,
  20.0, 70.0,
  2.0, 0.6,
  0.2, 0.01,
  0.5, 0.8,
  0.15, 0.5,
  'prod', 'Trained via continuous backtest (2016-11-24 to 2025-11-21)'
)
ON CONFLICT DO NOTHING;
