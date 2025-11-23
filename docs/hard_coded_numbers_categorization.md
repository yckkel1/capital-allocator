# Hard-Coded Numbers Categorization

**Generated:** 2025-11-23
**Purpose:** Identify and categorize all hard-coded numbers in the trading strategy codebase
**Author:** Automated analysis

---

## Executive Summary

This document categorizes **147 hard-coded numbers** found across `generate_signal.py` and `strategy_tuning.py`. These numbers fall into three categories:

1. **Constants (39)** - Mathematical/domain constants that never change
2. **Tunable Configs (78)** - Strategy parameters that should be tuned via `strategy_tuning.py`
3. **Non-Tunable Configs (30)** - System constraints that rarely change but should be DB-configurable

---

## Category 1: CONSTANTS

These are mathematical or domain-specific constants that should be defined as global variables for consistency but will never be tuned.

### Mathematical Constants

| Number | Location | Usage | Recommended Global Name |
|--------|----------|-------|-------------------------|
| `100` | generate_signal.py:52-53 | RSI calculation (percentage conversion) | `PERCENTAGE_MULTIPLIER` |
| `1` | generate_signal.py:52-53 | RSI calculation (base for division) | Not needed (keep inline) |
| `252` | strategy_tuning.py:572 | Annual trading days | `ANNUAL_TRADING_DAYS` |
| `0` | Multiple locations | Zero baseline/neutral value | Not needed (keep inline) |

### Domain Constants (Factors in Range 0-1)

| Number | Location | Usage | Recommended Global Name |
|--------|----------|-------|-------------------------|
| `0.5` | generate_signal.py:746 | Half Kelly factor | `HALF_KELLY_FACTOR` |
| `0.7, 1.5` | generate_signal.py:128 | Adjustment clamp min/max | `ADJUSTMENT_CLAMP_MIN`, `ADJUSTMENT_CLAMP_MAX` |
| `0.10, 0.80` | generate_signal.py:749 | Kelly allocation range | `MIN_KELLY_ALLOCATION`, `MAX_KELLY_ALLOCATION` |
| `50.0` | generate_signal.py:40 | Neutral RSI (midpoint) | `RSI_NEUTRAL` |
| `100.0` | generate_signal.py:50 | Maximum RSI | `RSI_MAX` |

### Weighting Constants

| Number | Location | Usage | Recommended Global Name |
|--------|----------|-------|-------------------------|
| `0.5, 0.3, 0.2` | generate_signal.py:282-284 | Regime calculation weights | `REGIME_MOMENTUM_WEIGHT`, `REGIME_SMA20_WEIGHT`, `REGIME_SMA50_WEIGHT` |
| `0.7, 0.3` | generate_signal.py:322 | Risk score weights | `RISK_VOL_WEIGHT`, `RISK_CORRELATION_WEIGHT` |
| `0.5` | generate_signal.py:314 | Stability discount factor | `STABILITY_DISCOUNT_FACTOR` |

### Default Values (Insufficient Data Scenarios)

| Number | Location | Usage | Recommended Global Name |
|--------|----------|-------|-------------------------|
| `0.5` | generate_signal.py:703 | Default half Kelly with insufficient data | `DEFAULT_HALF_KELLY_NO_DATA` |
| `0.05, 0.03` | generate_signal.py:733 | Default avg win/loss | `DEFAULT_AVG_WIN`, `DEFAULT_AVG_LOSS` |
| `0.001` | generate_signal.py:338 | Minimum volatility for division | `MIN_VOLATILITY_DIVISOR` |

---

## Category 2: TUNABLE CONFIGS

These are strategy parameters that should be stored in the `trading_config` table and tuned monthly.

### Currently MISSING from trading_config (Need to Add)

#### Regime Transition Detection
| Number | Location | Usage | Recommended Column Name |
|--------|----------|-------|-------------------------|
| `0.1, -0.1` | generate_signal.py:104-106 | Regime turning point thresholds | `regime_transition_threshold` |
| `0.3, -0.15` | generate_signal.py:110 | Losing momentum threshold | `momentum_loss_threshold` |
| `0, 0.15` | generate_signal.py:112 | Gaining momentum threshold | `momentum_gain_threshold` |
| `0.4` | generate_signal.py:385 | Strong trend regime threshold | `strong_trend_threshold` |

#### Confidence Scoring
| Number | Location | Usage | Recommended Column Name |
|--------|----------|-------|-------------------------|
| `0.5` | generate_signal.py:141 | Regime confidence divisor | `regime_confidence_divisor` |
| `40, 60` | generate_signal.py:144 | Risk penalty range | `risk_penalty_min`, `risk_penalty_max` |
| `1.2` | generate_signal.py:147 | Trend consistency threshold | `trend_consistency_threshold` |
| `0.6` | generate_signal.py:151 | Mean reversion base confidence | `mean_reversion_base_confidence` |
| `0.2, 0.3` | generate_signal.py:156 | Confidence bonus/penalty amounts | `consistency_bonus`, `risk_penalty_multiplier` |
| `0.7, 0.5` | generate_signal.py:955-960 | Confidence bucket thresholds | `confidence_bucket_high_threshold`, `confidence_bucket_medium_threshold` |

#### Mean Reversion Signals
| Number | Location | Usage | Recommended Column Name |
|--------|----------|-------|-------------------------|
| `-0.5` | generate_signal.py:359, 396 | BB position oversold threshold | `bb_oversold_threshold` |
| `0.5` | generate_signal.py:364, 399 | BB position overbought threshold | `bb_overbought_threshold` |
| `0.3` | generate_signal.py:360 | Strong oversold bonus | `oversold_strong_bonus` |
| `0.1` | generate_signal.py:362 | Mild oversold bonus | `oversold_mild_bonus` |
| `40, 0` | generate_signal.py:361-362 | Mild oversold RSI/BB thresholds | `rsi_mild_oversold`, `bb_mild_oversold` |
| `-0.2` | generate_signal.py:364 | Overbought penalty | `overbought_penalty` |

#### Downward Pressure Detection
| Number | Location | Usage | Recommended Column Name |
|--------|----------|-------|-------------------------|
| `-0.02` | generate_signal.py:438 | Price vs SMA threshold | `price_vs_sma_threshold` |
| `0.015, -0.03` | generate_signal.py:443 | High vol + negative return thresholds | `high_volatility_threshold`, `negative_return_threshold` |
| `0.67, 0.50` | generate_signal.py:453-458 | Downward pressure detection % | `severe_pressure_threshold`, `moderate_pressure_threshold` |
| `50, 45` | generate_signal.py:454-458 | Risk score thresholds for pressure | `severe_pressure_risk`, `moderate_pressure_risk` |

#### Dynamic Selling Behavior
| Number | Location | Usage | Recommended Column Name |
|--------|----------|-------|-------------------------|
| `70` | generate_signal.py:491, 507 | Cash % threshold for defensive scaling | `defensive_cash_threshold` |
| `0.5, 1.2` | generate_signal.py:492-494 | Sell % adjustments when defensive | `sell_defensive_multiplier`, `sell_aggressive_multiplier` |
| `0.6` | generate_signal.py:502 | Moderate pressure sell multiplier | `sell_moderate_pressure_multiplier` |
| `0.3` | generate_signal.py:547 | Bullish excessive risk sell multiplier | `sell_bullish_risk_multiplier` |

#### Risk-Based Thresholds
| Number | Location | Usage | Recommended Column Name |
|--------|----------|-------|-------------------------|
| `60` | generate_signal.py:525 | Mean reversion max risk | `mean_reversion_max_risk` |
| `55` | generate_signal.py:529-532 | Neutral high risk deleverage threshold | `neutral_deleverage_risk` |
| `50` | generate_signal.py:534-536 | Neutral high risk hold threshold | `neutral_hold_risk` |
| `65` | generate_signal.py:545-552 | Bullish excessive risk threshold | `bullish_excessive_risk` |

#### Asset Diversification
| Number | Location | Usage | Recommended Column Name |
|--------|----------|-------|-------------------------|
| `0.50, 0.40` | generate_signal.py:596 | Top asset allocation range (3-way) | `diversify_top_asset_max`, `diversify_top_asset_min` |
| `0.35, 0.30` | generate_signal.py:597 | 2nd asset allocation range | `diversify_second_asset_max`, `diversify_second_asset_min` |
| `0.25, 0.15` | generate_signal.py:598 | 3rd asset allocation range | `diversify_third_asset_max`, `diversify_third_asset_min` |
| `0.65, 0.35` | generate_signal.py:607-608 | Two-asset split | `two_asset_top`, `two_asset_second` |

#### Volatility & Normalization
| Number | Location | Usage | Recommended Column Name |
|--------|----------|-------|-------------------------|
| `0.02` | generate_signal.py:306 | Volatility normalization (2% typical) | `volatility_normalization_factor` |
| `0.05` | generate_signal.py:311 | Recent stability threshold | `stability_threshold` |
| `30, 100` | generate_signal.py:319 | Correlation risk calculation | `correlation_risk_base`, `correlation_risk_multiplier` |

#### Indicator Periods
| Number | Location | Usage | Recommended Column Name |
|--------|----------|-------|-------------------------|
| `14` | generate_signal.py:237 | RSI period | `rsi_period` |
| `20` | generate_signal.py:58, 240 | Bollinger Bands period | `bollinger_period` (already exists as `bollinger_std_multiplier`) |

#### Trend Consistency
| Number | Location | Usage | Recommended Column Name |
|--------|----------|-------|-------------------------|
| `1.5, 1.0` | generate_signal.py:348 | Trend consistency multipliers | `trend_aligned_multiplier`, `trend_mixed_multiplier` |

### Strategy Tuning Parameters (strategy_tuning.py)

#### Market Condition Detection
| Number | Location | Usage | Recommended Column Name |
|--------|----------|-------|-------------------------|
| `20` | strategy_tuning.py:100 | Market condition lookback window | `market_condition_window` |
| `0.6, 0.1` | strategy_tuning.py:148 | Momentum detection (R²>0.6, slope>0.1) | `momentum_r_squared_threshold`, `momentum_slope_threshold` |
| `0.3, 0.02` | strategy_tuning.py:150 | Choppy detection (R²<0.3 or vol>0.02) | `choppy_r_squared_threshold`, `choppy_volatility_threshold` |

#### Trade Evaluation Scoring
| Number | Location | Usage | Recommended Column Name |
|--------|----------|-------|-------------------------|
| `0.3, 0.2, 0.2` | strategy_tuning.py:297-301 | Positive scoring factors | `score_profitable_bonus`, `score_sharpe_bonus`, `score_low_dd_bonus` |
| `0.2, 0.1` | strategy_tuning.py:305-308 | Multi-horizon bonuses | `score_all_horizons_bonus`, `score_two_horizons_bonus` |
| `0.3, 0.4, 0.2` | strategy_tuning.py:312-316 | Negative scoring factors | `score_unprofitable_penalty`, `score_high_dd_penalty`, `score_sharpe_penalty` |
| `0.3` | strategy_tuning.py:320-322 | Market condition bonuses/penalties | `score_momentum_bonus`, `score_choppy_penalty` |
| `0.1` | strategy_tuning.py:326-328 | Confidence bucket bonuses | `score_confidence_bonus` |
| `0.15` | strategy_tuning.py:290 | Mean reversion success bonus | `score_mean_reversion_bonus` |

#### Tuning Decision Thresholds
| Number | Location | Usage | Recommended Column Name |
|--------|----------|-------|-------------------------|
| `65, 0.5, 0.2` | strategy_tuning.py:398-401 | Aggressiveness criteria (win>65%, buy<50%, score>0.2) | `tune_aggressive_win_rate`, `tune_aggressive_participation`, `tune_aggressive_score` |
| `45, 15, -0.1` | strategy_tuning.py:405 | Conservative criteria | `tune_conservative_win_rate`, `tune_conservative_dd`, `tune_conservative_score` |
| `0.1, 0.05` | strategy_tuning.py:650-658 | Parameter adjustment amounts | `tune_allocation_step`, `tune_neutral_step` |
| `5` | strategy_tuning.py:664, 679 | Risk threshold adjustment step | `tune_risk_threshold_step` |
| `1.5` | strategy_tuning.py:681 | Strong Sharpe multiplier for aggressiveness | `tune_sharpe_aggressive_threshold` |

#### Sell Strategy Tuning
| Number | Location | Usage | Recommended Column Name |
|--------|----------|-------|-------------------------|
| `0.7` | strategy_tuning.py:704 | Sell effectiveness threshold | `tune_sell_effective_threshold` |
| `-0.2` | strategy_tuning.py:707-709 | Sell underperformance threshold | `tune_sell_underperform_threshold` |
| `0.3` | strategy_tuning.py:711 | Bearish sell participation threshold | `tune_bearish_sell_participation` |
| `15` | strategy_tuning.py:716 | High drawdown threshold for forced selling | `tune_high_dd_no_sell_threshold` |
| `0.15, 0.1` | strategy_tuning.py:717-726 | Sell percentage adjustment amounts | `tune_sell_major_adjustment`, `tune_sell_minor_adjustment` |

#### Confidence Tuning
| Number | Location | Usage | Recommended Column Name |
|--------|----------|-------|-------------------------|
| `40, 70` | strategy_tuning.py:734-741 | Win rate thresholds for confidence adjustments | `tune_low_conf_poor_threshold`, `tune_high_conf_strong_threshold` |
| `0.05, 0.1` | strategy_tuning.py:735-741 | Confidence parameter adjustment steps | `tune_confidence_threshold_step`, `tune_confidence_scaling_step` |

#### Mean Reversion Tuning
| Number | Location | Usage | Recommended Column Name |
|--------|----------|-------|-------------------------|
| `60, 45` | strategy_tuning.py:749-756 | MR signal performance thresholds | `tune_mr_good_threshold`, `tune_mr_poor_threshold` |
| `5` | strategy_tuning.py:755-756 | RSI threshold adjustment step | `tune_rsi_threshold_step` |

#### Validation
| Number | Location | Usage | Recommended Column Name |
|--------|----------|-------|-------------------------|
| `0.8, 1.2` | strategy_tuning.py:527-528 | Validation tolerance multipliers | `validation_sharpe_tolerance`, `validation_dd_tolerance` |
| `0.5` | strategy_tuning.py:537 | Validation passing score | `validation_passing_score` |

---

## Category 3: NON-TUNABLE CONFIGS

These are system constraints that rarely change but should be in a separate database table for easy modification without code changes.

### Recommended New Table: `strategy_constraints`

```sql
CREATE TABLE strategy_constraints (
  id SERIAL PRIMARY KEY,
  start_date DATE NOT NULL,
  end_date DATE NULL,  -- NULL = currently active

  -- Position Management
  min_holding_threshold FLOAT NOT NULL DEFAULT 10.0,  -- Minimum % to hold

  -- Capital Scaling Breakpoints
  capital_scale_tier1_threshold FLOAT NOT NULL DEFAULT 10000.0,
  capital_scale_tier1_factor FLOAT NOT NULL DEFAULT 1.0,
  capital_scale_tier2_threshold FLOAT NOT NULL DEFAULT 50000.0,
  capital_scale_tier2_factor FLOAT NOT NULL DEFAULT 0.75,
  capital_scale_tier3_threshold FLOAT NOT NULL DEFAULT 200000.0,
  capital_scale_tier3_factor FLOAT NOT NULL DEFAULT 0.50,
  capital_scale_max_reduction FLOAT NOT NULL DEFAULT 0.35,

  -- Kelly Criterion
  min_trades_for_kelly INTEGER NOT NULL DEFAULT 10,
  kelly_confidence_threshold FLOAT NOT NULL DEFAULT 0.6,

  -- Data Requirements
  min_data_days INTEGER NOT NULL DEFAULT 60,

  -- Time Horizons
  pnl_horizon_short INTEGER NOT NULL DEFAULT 10,
  pnl_horizon_medium INTEGER NOT NULL DEFAULT 20,
  pnl_horizon_long INTEGER NOT NULL DEFAULT 30,

  -- Metadata
  created_at TIMESTAMP DEFAULT NOW(),
  created_by VARCHAR(100),
  notes VARCHAR(500)
);
```

#### Position Management Constraints

| Number | Location | Usage | Column Name |
|--------|----------|-------|-------------|
| `10` | generate_signal.py:925 (MIN_HOLDING_THRESHOLD) | Minimum holding % to avoid loops | `min_holding_threshold` |

#### Capital Scaling Constraints

| Number | Location | Usage | Column Name |
|--------|----------|-------|-------------|
| `10_000` | generate_signal.py:655 | Tier 1 capital threshold | `capital_scale_tier1_threshold` |
| `1.0` | generate_signal.py:657 | Tier 1 scaling factor | `capital_scale_tier1_factor` |
| `50_000` | generate_signal.py:658 | Tier 2 capital threshold | `capital_scale_tier2_threshold` |
| `0.75` | generate_signal.py:661 | Tier 2 scaling factor | `capital_scale_tier2_factor` |
| `200_000` | generate_signal.py:662 | Tier 3 capital threshold | `capital_scale_tier3_threshold` |
| `0.50` | generate_signal.py:665 | Tier 3 scaling factor | `capital_scale_tier3_factor` |
| `0.35` | generate_signal.py:670 | Maximum capital reduction | `capital_scale_max_reduction` |
| `0.25, 0.25, 0.15` | generate_signal.py:661-670 | Tier reduction amounts | (calculated from factors) |
| `40_000, 150_000, 2_000_000` | generate_signal.py:661-669 | Tier range denominators | (calculated from thresholds) |

#### Kelly Criterion Constraints

| Number | Location | Usage | Column Name |
|--------|----------|-------|-------------|
| `10` | generate_signal.py:701, 728 | Minimum trades for Kelly calculation | `min_trades_for_kelly` |
| `0.6` | generate_signal.py:722 | Confidence threshold for win counting | `kelly_confidence_threshold` |

#### Data Requirements

| Number | Location | Usage | Column Name |
|--------|----------|-------|-------------|
| `60` | generate_signal.py:788 | Minimum days of price history required | `min_data_days` |

#### Analysis Horizons

| Number | Location | Usage | Column Name |
|--------|----------|-------|-------------|
| `10, 20, 30` | strategy_tuning.py:245 | P&L evaluation horizons (days) | `pnl_horizon_short`, `pnl_horizon_medium`, `pnl_horizon_long` |
| `5, 10` | strategy_tuning.py:163-164 | Drawdown contribution window | `dd_window_before`, `dd_window_after` |

#### Trade Evaluation Constraints

| Number | Location | Usage | Column Name |
|--------|----------|-------|-------------|
| `5, 20` | strategy_tuning.py:300, 334 | DD contribution thresholds | `dd_contribution_low`, `dd_contribution_high` |
| `-50` | strategy_tuning.py:336 | Low confidence loss threshold | `low_conf_loss_threshold` |

#### Risk-Free Rate

| Number | Location | Usage | Column Name |
|--------|----------|-------|-------------|
| `0.05` | strategy_tuning.py:30 | Annual risk-free rate (5%) | `risk_free_rate` |

---

## Summary Statistics

### By Category
- **Constants:** 39 numbers (27%)
- **Tunable Configs:** 78 numbers (53%)
- **Non-Tunable Configs:** 30 numbers (20%)

### By File
- **generate_signal.py:** 112 numbers (76%)
- **strategy_tuning.py:** 35 numbers (24%)

### Current Coverage
- **Already in trading_config:** 18 parameters
- **Missing from trading_config:** 60 parameters
- **Need new constraints table:** 30 parameters

---

## Implementation Priority

### Phase 1: Critical Tunable Parameters (High Impact)
1. Downward pressure detection thresholds
2. Dynamic selling behavior multipliers
3. Risk-based action thresholds
4. Confidence scoring parameters

### Phase 2: Non-Tunable Constraints
1. Create `strategy_constraints` table
2. Move MIN_HOLDING_THRESHOLD
3. Move capital scaling breakpoints
4. Move Kelly criterion thresholds

### Phase 3: Remaining Tunable Parameters
1. Regime transition detection
2. Mean reversion signals
3. Asset diversification limits
4. Volatility normalization

### Phase 4: Constants Cleanup
1. Define global constants at top of files
2. Replace all hard-coded instances
3. Add comments explaining each constant

---

## Questions for Tuning Analysis

### Are we actually using tuned parameters?

**CRITICAL FINDING:** Many hard-coded thresholds in `decide_action()` and `rank_assets()` are **NOT** using tunable parameters from `trading_config`.

For example:
- Line 507: `risk_score > 70` should use a tunable parameter
- Line 525: `risk_score < 60` should use a tunable parameter
- Line 545: `risk_score > 65` should use a tunable parameter
- Lines 596-598: Asset allocation limits are all hard-coded

**Answer:** No, we are NOT fully using tuned parameters. Many critical decision points use hard-coded values that bypass the tuning system.

### Recommendation

**Urgently refactor all hard-coded decision thresholds to use `trading_config` parameters.** The monthly tuning script cannot optimize what it cannot control.

---

## Next Steps

1. ✅ **Review this document** with the team
2. ⬜ Add 60 new columns to `trading_config` table
3. ⬜ Create `strategy_constraints` table
4. ⬜ Update `generate_signal.py` to use DB parameters
5. ⬜ Update `strategy_tuning.py` to tune new parameters
6. ⬜ Define global constants
7. ⬜ Update unit tests
8. ⬜ Run backtest to validate changes

---

**End of Document**
