-- Initial strategy constraints
-- Generated on: 2025-11-23
-- These are system constraints that rarely change but are stored in DB for flexibility

INSERT INTO strategy_constraints (
  start_date, end_date,
  -- Position Management
  min_holding_threshold,
  -- Capital Scaling Breakpoints
  capital_scale_tier1_threshold, capital_scale_tier1_factor,
  capital_scale_tier2_threshold, capital_scale_tier2_factor,
  capital_scale_tier3_threshold, capital_scale_tier3_factor,
  capital_scale_max_reduction,
  -- Kelly Criterion
  min_trades_for_kelly, kelly_confidence_threshold,
  -- Data Requirements
  min_data_days,
  -- Time Horizons
  pnl_horizon_short, pnl_horizon_medium, pnl_horizon_long,
  -- Risk-Free Rate
  risk_free_rate,
  -- Metadata
  created_by, notes
) VALUES (
  '2015-01-01',
  NULL,  -- end_date (currently active)
  -- Position Management
  10.0,  -- min_holding_threshold: Minimum 10% holding to avoid loops
  -- Capital Scaling Breakpoints
  10000.0, 1.0,    -- Tier 1: < $10k, 100% allocation
  50000.0, 0.75,   -- Tier 2: $10k-$50k, 75% allocation
  200000.0, 0.50,  -- Tier 3: $50k-$200k, 50% allocation
  0.35,            -- Max reduction: 35% minimum allocation for very large capital
  -- Kelly Criterion
  10, 0.6,  -- Require 10 trades minimum, 0.6 confidence threshold for wins
  -- Data Requirements
  60,  -- Minimum 60 days of price history required
  -- Time Horizons
  10, 20, 30,  -- P&L evaluation horizons (10d, 20d, 30d)
  -- Risk-Free Rate
  0.05,  -- 5% annual risk-free rate
  -- Metadata
  'initial_deployment',
  'Default system constraints for initial deployment'
)
ON CONFLICT DO NOTHING;
