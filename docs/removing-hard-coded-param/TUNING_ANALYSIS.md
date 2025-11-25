# Tunable Configuration Parameters: Tuning Analysis

**Generated:** 2025-11-25
**Purpose:** Comprehensive analysis of how each tunable parameter is adjusted during monthly tuning

---

## Executive Summary

**Total Tunable Parameters:** 151 fields in `trading_config` table
**Parameters Actively Tuned:** 25 parameters (16.6%)
**Parameters Used for Tuning Logic Only:** 67 parameters (44.4%)
**Parameters NOT Tuned:** 59 parameters (39.1%)

### Key Finding: Significant Under-Tuning

**Critical Issue:** Only 16.6% of tunable parameters are actively adjusted during monthly tuning. The majority of "tunable" parameters are either:
1. Used as thresholds in tuning logic but never adjusted themselves
2. Core trading parameters that are not being optimized at all

---

## Category 1: ACTIVELY TUNED PARAMETERS (25 params)

These parameters are adjusted by `strategy_tuning.py` based on performance analysis.

### 1.1 Allocation Parameters (4 params)

| Parameter | Default | Tuning Logic | Magnitude | Bounds |
|-----------|---------|--------------|-----------|--------|
| `allocation_low_risk` | 0.8 | ±0.1 per tuning | ±10% | [0.5, 1.0] |
| `allocation_medium_risk` | 0.5 | ±0.1 per tuning | ±20% | [0.3, 0.7] |
| `allocation_high_risk` | 0.3 | ±0.05 per tuning | ±17% | [0.2, ∞] |
| `allocation_neutral` | 0.2 | ±0.05 per tuning | ±25% | [0.1, ∞] |

**Tuning Triggers:**
- **Increase:** Momentum win rate > 65%, participation < 50%, avg_score > 0.2
- **Decrease:** Momentum win rate < 45% OR avg_drawdown > 15% OR avg_score < -0.1

**Statistical Process:** Rule-based thresholding (NO statistical optimization)

**Issues Identified:**
- ⚠️ **No upper bound for `allocation_high_risk` and `allocation_neutral`** - could grow unbounded
- ⚠️ **Adjustment steps are fixed** - no adaptive step sizing based on confidence
- ⚠️ **No correlation analysis** - parameters tuned independently

---

### 1.2 Risk Threshold Parameters (2 params)

| Parameter | Default | Tuning Logic | Magnitude | Bounds |
|-----------|---------|--------------|-----------|--------|
| `risk_high_threshold` | 70.0 | ±5.0 per tuning | ±7% | [60.0, ∞] |
| `risk_medium_threshold` | 40.0 | ±5.0 per tuning | ±12.5% | [30.0, ∞] |

**Tuning Triggers:**
- **Decrease:** Max drawdown exceeds tolerance OR Sharpe < target
- **Increase:** Never (only decreases)

**Issues Identified:**
- ⚠️ **One-directional tuning** - thresholds only decrease, never increase
- ⚠️ **No upper bounds** - could grow unbounded
- ⚠️ **Fixed step size** - 5.0 is aggressive for a parameter that ranges 30-70

---

### 1.3 Regime Threshold Parameters (1 param)

| Parameter | Default | Tuning Logic | Magnitude | Bounds |
|-----------|---------|--------------|-----------|--------|
| `regime_bullish_threshold` | 0.3 | ±0.05 per tuning | ±17% | [0.2, 0.4] |

**Tuning Triggers:**
- **Increase (more conservative):** Sharpe < target
- **Decrease (more aggressive):** Sharpe > 1.5× target

**Issues Identified:**
- ✅ **Properly bounded** [0.2, 0.4]
- ⚠️ **`regime_bearish_threshold` NOT tuned** - asymmetric tuning

---

### 1.4 Sell Strategy Parameters (1 param)

| Parameter | Default | Tuning Logic | Magnitude | Bounds |
|-----------|---------|--------------|-----------|--------|
| `sell_percentage` | 0.7 | ±0.1 or ±0.15 | ±14-21% | [0.3, 0.9] |

**Tuning Triggers:**
- **Major increase (+0.15):** High drawdown (>15%) with NO sell trades
- **Minor increase (+0.1):** Not selling enough in bearish periods OR poor bearish performance
- **Minor decrease (-0.1):** Sell trades scoring poorly (avg < -0.2)

**Statistical Process:** Trade scoring analysis with win rate calculation

**Issues Identified:**
- ✅ **Well-bounded** [0.3, 0.9]
- ✅ **Multi-condition logic** considers effectiveness, not just volume
- ⚠️ **No optimization** - only rule-based adjustments

---

### 1.5 Confidence Parameters (2 params)

| Parameter | Default | Tuning Logic | Magnitude | Bounds |
|-----------|---------|--------------|-----------|--------|
| `min_confidence_threshold` | 0.3 | ±0.05 per tuning | ±17% | [0, 0.5] |
| `confidence_scaling_factor` | 0.5 | ±0.1 per tuning | ±20% | [0, 0.8] |

**Tuning Triggers:**
- **Increase threshold:** Low confidence trades have win rate < 40%
- **Increase scaling:** High confidence trades have win rate > 70%

**Issues Identified:**
- ✅ **Bounded appropriately**
- ⚠️ **Independent tuning** - no joint optimization of threshold + scaling

---

### 1.6 Mean Reversion Parameters (2 params)

| Parameter | Default | Tuning Logic | Magnitude | Bounds |
|-----------|---------|--------------|-----------|--------|
| `mean_reversion_allocation` | 0.4 | ±0.05 per tuning | ±12.5% | [0, 0.6] |
| `rsi_oversold_threshold` | 30.0 | ±5.0 per tuning | ±17% | [20.0, ∞] |

**Tuning Triggers:**
- **Increase allocation:** Mean reversion signals have win rate > 60%
- **Tighten RSI (decrease):** Mean reversion signals have win rate < 45%

**Issues Identified:**
- ⚠️ **No upper bound for RSI threshold** - could grow unbounded
- ⚠️ **Only tunes oversold, not overbought** - asymmetric

---

### 1.7 Summary: Actively Tuned Parameters

**Total Actively Tuned:** 12 core parameters + their bounds (25 including boundary params)

**Tuning Magnitude:**
- Small adjustments: ±5-20% per month
- Conservative approach: avoids large jumps
- Risk: May be too slow to adapt to regime changes

**Statistical Rigor:**
- ❌ **No gradient-based optimization**
- ❌ **No Bayesian optimization**
- ❌ **No grid search or random search**
- ❌ **No cross-validation**
- ✅ **Rule-based thresholds** (simple but interpretable)

---

## Category 2: TUNING LOGIC PARAMETERS (67 params)

These parameters control HOW tuning decisions are made but are never tuned themselves.

### 2.1 Market Condition Detection (4 params)

| Parameter | Default | Purpose | Never Tuned |
|-----------|---------|---------|-------------|
| `market_condition_r_squared_threshold` | 0.6 | Detect momentum (R² > 0.6) | ⚠️ |
| `market_condition_slope_threshold` | 0.1 | Detect trend strength | ⚠️ |
| `market_condition_choppy_r_squared` | 0.3 | Detect choppy markets | ⚠️ |
| `market_condition_choppy_volatility` | 0.02 | High volatility threshold | ⚠️ |

**Issue:** These thresholds fundamentally affect trade classification but are **never tuned**. If market regime changes (e.g., crypto-like volatility), these fixed thresholds will misclassify conditions.

---

### 2.2 Trade Evaluation Scoring (12 params)

Used to score trades from -1 to +1 for tuning analysis:

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `score_profitable_bonus` | +0.3 | Reward profitable trades |
| `score_sharpe_bonus` | +0.2 | Reward trades that improved Sharpe |
| `score_low_dd_bonus` | +0.2 | Reward trades with DD < 5% |
| `score_all_horizons_bonus` | +0.2 | Reward trades profitable at 10d, 20d, 30d |
| `score_two_horizons_bonus` | +0.1 | Reward 2/3 horizons profitable |
| `score_unprofitable_penalty` | -0.3 | Penalize losing trades |
| `score_high_dd_penalty` | -0.4 | Penalize trades with DD > 20% |
| `score_sharpe_penalty` | -0.2 | Penalize trades that hurt Sharpe |
| `score_momentum_bonus` | +0.3 | Reward momentum-aligned trades |
| `score_choppy_penalty` | -0.3 | Penalize trades in choppy markets |
| `score_confidence_bonus` | +0.1 | Reward high-confidence wins |
| `score_mean_reversion_bonus` | +0.15 | Reward successful MR trades |

**Issue:** These scoring weights are **subjective and never validated**. A trade that scores 0.5 may not actually be "good" - it just matches our arbitrary scoring criteria.

---

### 2.3 Tuning Decision Thresholds (6 params)

Control when to be more/less aggressive:

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `tune_aggressive_win_rate` | 65.0 | Win rate threshold to increase aggression |
| `tune_aggressive_participation` | 0.5 | Participation threshold |
| `tune_aggressive_score` | 0.2 | Score threshold for aggression |
| `tune_conservative_win_rate` | 45.0 | Win rate threshold to decrease aggression |
| `tune_conservative_dd` | 15.0 | Drawdown threshold |
| `tune_conservative_score` | -0.1 | Score threshold for conservation |

**Issue:** These are **magic numbers that control the entire tuning system** but are never tuned themselves. Who says 65% win rate is the right threshold?

---

### 2.4 Parameter Adjustment Step Sizes (4 params)

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `tune_allocation_step` | 0.1 | Step size for allocation changes |
| `tune_neutral_step` | 0.05 | Step size for neutral/regime params |
| `tune_risk_threshold_step` | 5.0 | Step size for risk thresholds |
| `tune_sharpe_aggressive_threshold` | 1.5 | Sharpe multiplier for aggression |

**Issue:** **Fixed step sizes** don't account for:
- Confidence in the tuning decision
- Magnitude of performance deviation
- Recent tuning volatility (should have adaptive step sizes)

---

### 2.5 Sell Strategy Tuning Thresholds (6 params)

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `tune_sell_effective_threshold` | 0.7 | Sell effectiveness threshold |
| `tune_sell_underperform_threshold` | -0.2 | Poor sell performance threshold |
| `tune_bearish_sell_participation` | 0.3 | Expected sell participation in bearish |
| `tune_high_dd_no_sell_threshold` | 15.0 | DD threshold to force more selling |
| `tune_sell_major_adjustment` | 0.15 | Large adjustment size |
| `tune_sell_minor_adjustment` | 0.1 | Small adjustment size |

---

### 2.6 Confidence Tuning Thresholds (4 params)

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `tune_low_conf_poor_threshold` | 40.0 | Low confidence win rate threshold |
| `tune_high_conf_strong_threshold` | 70.0 | High confidence win rate threshold |
| `tune_confidence_threshold_step` | 0.05 | Step size for confidence threshold |
| `tune_confidence_scaling_step` | 0.1 | Step size for confidence scaling |

---

### 2.7 Mean Reversion Tuning (3 params)

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `tune_mr_good_threshold` | 60.0 | MR win rate threshold to increase allocation |
| `tune_mr_poor_threshold` | 45.0 | MR win rate threshold to tighten signals |
| `tune_rsi_threshold_step` | 5.0 | Step size for RSI adjustment |

---

### 2.8 Validation Thresholds (5 params)

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `validation_sharpe_tolerance` | 0.8 | Accept if test Sharpe ≥ 0.8× target |
| `validation_dd_tolerance` | 1.2 | Accept if test DD ≤ 1.2× tolerance |
| `validation_passing_score` | 0.5 | Minimum validation score to pass |
| `validation_sharpe_weight` | 0.5 | Weight for Sharpe in validation |
| `validation_drawdown_weight` | 0.5 | Weight for DD in validation |

**Issue:** Out-of-sample validation is performed but **not enforced**. Parameters can fail validation and still be deployed.

---

### 2.9 Trade Evaluation DD Thresholds (2 params)

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `score_dd_low_threshold` | 5.0 | Low DD bonus threshold |
| `score_dd_high_threshold` | 20.0 | High DD penalty threshold |

---

### 2.10 Parameter Boundary Limits (21 params)

These define min/max bounds for actively tuned parameters:

**Allocation Bounds:**
- `tune_allocation_low_risk_max` = 1.0
- `tune_allocation_low_risk_min` = 0.5
- `tune_allocation_medium_risk_max` = 0.7
- `tune_allocation_medium_risk_min` = 0.3
- `tune_allocation_high_risk_min` = 0.2
- `tune_allocation_neutral_min` = 0.1

**Risk Threshold Bounds:**
- `tune_risk_medium_threshold_min` = 30.0
- `tune_risk_high_threshold_min` = 60.0

**Regime Threshold Bounds:**
- `tune_regime_bullish_threshold_max` = 0.4
- `tune_regime_bullish_threshold_min` = 0.2

**Sell Percentage Bounds:**
- `tune_sell_percentage_min` = 0.3
- `tune_sell_percentage_max` = 0.9

**Confidence Bounds:**
- `tune_min_confidence_threshold_max` = 0.5
- `tune_confidence_scaling_factor_max` = 0.8

**Mean Reversion Bounds:**
- `tune_mean_reversion_allocation_max` = 0.6
- `tune_rsi_oversold_threshold_min` = 20.0

**Issue:** Many bounds are **incomplete** (missing max or min), allowing unbounded growth.

---

## Category 3: NEVER TUNED PARAMETERS (59 params)

These are core trading parameters that are **currently NOT being tuned** by the monthly tuning script.

### 3.1 Core Trading Parameters NOT Being Tuned

#### Regime Detection (9 params)
- ❌ `regime_bearish_threshold` (-0.3) - Only bullish threshold tuned
- ❌ `regime_transition_threshold` (0.1)
- ❌ `momentum_loss_threshold` (-0.15)
- ❌ `momentum_gain_threshold` (0.15)
- ❌ `strong_trend_threshold` (0.4)
- ❌ `regime_momentum_weight` (0.5)
- ❌ `regime_sma20_weight` (0.3)
- ❌ `regime_sma50_weight` (0.2)
- ❌ `regime_confidence_divisor` (0.5)

**Impact:** Regime detection is fundamental to all trading decisions. These parameters should be tuned.

---

#### Confidence Scoring (5 params)
- ❌ `risk_penalty_min` (40.0)
- ❌ `risk_penalty_max` (60.0)
- ❌ `trend_consistency_threshold` (1.2)
- ❌ `mean_reversion_base_confidence` (0.6)
- ❌ `consistency_bonus` (0.2)
- ❌ `risk_penalty_multiplier` (0.3)
- ❌ `confidence_bucket_high_threshold` (0.7)
- ❌ `confidence_bucket_medium_threshold` (0.5)

**Impact:** Confidence scoring determines position sizing. Should be optimized based on realized P&L.

---

#### Mean Reversion Signals (6 params)
- ❌ `bb_oversold_threshold` (-0.5)
- ❌ `bb_overbought_threshold` (0.5)
- ❌ `oversold_strong_bonus` (0.3)
- ❌ `oversold_mild_bonus` (0.1)
- ❌ `rsi_mild_oversold` (40.0)
- ❌ `bb_mild_oversold` (0.0)
- ❌ `overbought_penalty` (-0.2)
- ❌ `rsi_overbought_threshold` (70.0) - Only oversold tuned

**Impact:** Mean reversion strategy has hardcoded thresholds that may not be optimal.

---

#### Downward Pressure Detection (7 params)
- ❌ `price_vs_sma_threshold` (-0.02)
- ❌ `high_volatility_threshold` (0.015)
- ❌ `negative_return_threshold` (-0.03)
- ❌ `severe_pressure_threshold` (0.67)
- ❌ `moderate_pressure_threshold` (0.50)
- ❌ `severe_pressure_risk` (50.0)
- ❌ `moderate_pressure_risk` (45.0)

**Impact:** Downward pressure affects selling behavior. Thresholds should adapt to market conditions.

---

#### Dynamic Selling Behavior (5 params)
- ❌ `defensive_cash_threshold` (70.0)
- ❌ `sell_defensive_multiplier` (0.5)
- ❌ `sell_aggressive_multiplier` (1.2)
- ❌ `sell_moderate_pressure_multiplier` (0.6)
- ❌ `sell_bullish_risk_multiplier` (0.3)

**Impact:** Selling multipliers are hardcoded but should be tuned based on sell effectiveness.

---

#### Risk-Based Thresholds (5 params)
- ❌ `mean_reversion_max_risk` (60.0)
- ❌ `neutral_deleverage_risk` (55.0)
- ❌ `neutral_hold_risk` (50.0)
- ❌ `bullish_excessive_risk` (65.0)
- ❌ `extreme_risk_threshold` (70.0)

**Impact:** Risk-based action thresholds are critical. Should be tuned based on risk-adjusted returns.

---

#### Asset Diversification (8 params)
- ❌ `diversify_top_asset_max` (0.50)
- ❌ `diversify_top_asset_min` (0.40)
- ❌ `diversify_second_asset_max` (0.35)
- ❌ `diversify_second_asset_min` (0.30)
- ❌ `diversify_third_asset_max` (0.25)
- ❌ `diversify_third_asset_min` (0.15)
- ❌ `two_asset_top` (0.65)
- ❌ `two_asset_second` (0.35)

**Impact:** Diversification limits are arbitrary. Should be optimized based on portfolio returns.

---

#### Volatility & Normalization (5 params)
- ❌ `volatility_normalization_factor` (0.02)
- ❌ `stability_threshold` (0.05)
- ❌ `stability_discount_factor` (0.5)
- ❌ `correlation_risk_base` (30.0)
- ❌ `correlation_risk_multiplier` (100.0)

**Impact:** These affect risk scoring. Should be tuned to improve risk-adjusted returns.

---

#### Risk Score Calculation Weights (2 params)
- ❌ `risk_volatility_weight` (0.7)
- ❌ `risk_correlation_weight` (0.3)

**CRITICAL:** This was the original "high-school" formula that was hard-coded. It's now tunable but **NEVER ACTUALLY TUNED**. This defeats the entire purpose of the refactoring!

---

#### Indicator Periods (2 params)
- ❌ `rsi_period` (14)
- ❌ `bollinger_period` (20)

**Impact:** Standard indicator periods may not be optimal for the strategy's time horizon.

---

#### Trend Consistency (2 params)
- ❌ `trend_aligned_multiplier` (1.5)
- ❌ `trend_mixed_multiplier` (1.0)

**Impact:** Trend alignment bonuses are hardcoded. Should be data-driven.

---

#### Adaptive Threshold Clamps (2 params)
- ❌ `adaptive_threshold_clamp_min` (0.7)
- ❌ `adaptive_threshold_clamp_max` (1.5)

---

#### Risk Label Thresholds (2 params)
- ❌ `risk_label_high_threshold` (70.0)
- ❌ `risk_label_medium_threshold` (40.0)

---

#### Circuit Breaker (2 params)
- ❌ `intramonth_drawdown_limit` (0.10)
- ❌ `circuit_breaker_reduction` (0.5)

**Impact:** Circuit breakers are risk controls. Should be tuned based on false positive/negative rates.

---

#### Volatility Adjustment (2 params)
- ❌ `volatility_adjustment_factor` (0.4)
- ❌ `base_volatility` (0.01)

---

#### Basic Parameters (3 params)
- ❌ `daily_capital` (1000.0) - Usually not tuned
- ❌ `assets` (["SPY", "QQQ", "DIA"]) - Configuration, not tunable
- ❌ `lookback_days` (252) - Usually fixed

---

#### Risk Management Targets (2 params)
- ❌ `max_drawdown_tolerance` (15.0) - **Should be tuned** based on actual risk appetite
- ❌ `min_sharpe_target` (1.0) - **Should be tuned** based on achievable performance

---

#### Asset Ranking Weights (2 params)
- ❌ `momentum_weight` (0.6)
- ❌ `price_momentum_weight` (0.4)

**Impact:** Asset ranking determines which assets to buy. Weights should be optimized.

---

#### Mean Reversion Base Parameters (2 params)
- ❌ `bollinger_std_multiplier` (2.0)

---

## Statistical Analysis of Tuning Process

### Current Approach: Rule-Based Thresholding

**Algorithm:**
```
IF condition_metric > threshold:
    parameter += step_size
ELIF condition_metric < threshold:
    parameter -= step_size
```

**Characteristics:**
- ✅ Simple and interpretable
- ✅ Predictable behavior
- ❌ No optimization
- ❌ No statistical rigor
- ❌ No consideration of parameter interactions
- ❌ No confidence intervals
- ❌ No overfitting protection (beyond simple out-of-sample test)

---

### Comparison to Quantitative Best Practices

| Aspect | Current | Best Practice |
|--------|---------|---------------|
| Optimization Method | Rule-based | Bayesian optimization, grid search, genetic algorithms |
| Statistical Testing | None | Hypothesis testing, confidence intervals |
| Overfitting Prevention | Simple train/test split | Cross-validation, regularization, walk-forward |
| Parameter Interactions | Ignored | Correlation analysis, joint optimization |
| Adaptive Step Sizes | Fixed | Learning rate schedules, momentum |
| Multi-objective | None | Pareto optimization (Sharpe vs DD vs Win Rate) |
| Robustness Testing | None | Monte Carlo, stress testing, regime analysis |

---

## Tuning Magnitude Analysis

### Conservative Tuning (May Be Too Slow)

| Parameter Type | Step Size | % Change | Months to 50% Change |
|----------------|-----------|----------|---------------------|
| Allocation | 0.1 | 10-20% | 3-5 months |
| Risk Thresholds | 5.0 | 7-12% | 5-8 months |
| Regime | 0.05 | 17% | 3 months |
| Sell % | 0.1-0.15 | 14-21% | 2-4 months |
| Confidence | 0.05-0.1 | 17-20% | 3-5 months |

**Issue:** If market regime changes suddenly (e.g., 2020 COVID crash, 2022 rate hikes), the strategy takes **3-8 months** to fully adapt.

**Recommendation:** Implement adaptive step sizing based on:
- Magnitude of performance deviation
- Confidence in the tuning decision
- Market volatility (larger steps in stable markets, smaller in volatile)

---

## Overfitting Risk Analysis

### Current Overfitting Protection: WEAK

**Out-of-Sample Validation:**
- ✅ Splits data 67% train / 33% test
- ✅ Evaluates Sharpe and DD on test set
- ❌ **Validation not enforced** - parameters deployed even if they fail
- ❌ **Single split** - no cross-validation
- ❌ **No Monte Carlo testing**
- ❌ **No regime robustness testing**

### Overfitting Risks Identified

1. **Look-Ahead Bias:** Multi-horizon P&L calculation uses future data that wouldn't be available at trade time
2. **Data Snooping:** Tuning thresholds (e.g., 65% win rate) were chosen ad-hoc, not validated
3. **Regime Dependency:** Parameters tuned during bull market may fail in bear market
4. **Small Sample:** 3-month lookback may have insufficient trades for statistical significance
5. **Parameter Persistence:** No mechanism to detect if a parameter change is improving or hurting performance over time

---

## Consistency Analysis: Variable Names

### Database vs Code Consistency: ✅ GOOD

All `trading_config` fields are dynamically loaded via `TradingConfig.from_db_row()`, ensuring consistency.

**Method:**
```python
# config_loader.py line 264-288
def from_db_row(cls, row: Dict) -> 'TradingConfig':
    fields = {f.name: f for f in cls.__dataclass_fields__.values()}
    kwargs = {}
    for field_name, field_info in fields.items():
        if field_name in row and row[field_name] is not None:
            # Auto-conversion to appropriate type
            ...
```

**Verification:**
- ✅ All 151 parameters in seed data match dataclass fields
- ✅ Type conversion handled automatically
- ✅ Missing fields use dataclass defaults

---

## Critical Issues Identified

### 🚨 CRITICAL: Risk Score Weights Never Tuned

**The Original Problem:**
> "risk_score = vol_score * 0.7 + correlation_risk * 0.3 was hard-coded"

**Current State:**
- ✅ Now stored in database as `risk_volatility_weight` (0.7) and `risk_correlation_weight` (0.3)
- ❌ **NEVER TUNED** by `strategy_tuning.py`

**Impact:** The entire refactoring was to enable tuning these weights, but they remain fixed!

**Recommendation:** Add tuning logic to optimize these weights based on risk-adjusted returns.

---

### 🚨 CRITICAL: Most Parameters Never Tuned

**Only 12 core parameters** (out of 80+ trading parameters) are actively tuned:
- Allocations (4)
- Risk thresholds (2)
- Regime threshold (1)
- Sell percentage (1)
- Confidence (2)
- Mean reversion (2)

**59 trading parameters** remain fixed despite being "tunable."

**Recommendation:** Expand tuning to cover:
1. Risk score calculation weights (HIGHEST PRIORITY)
2. Regime detection thresholds
3. Confidence scoring parameters
4. Mean reversion thresholds
5. Diversification limits

---

### ⚠️ Missing Upper Bounds

Several parameters lack maximum bounds and could grow unbounded:
- `allocation_high_risk` (min=0.2, no max)
- `allocation_neutral` (min=0.1, no max)
- `risk_high_threshold` (min=60.0, no max)
- `risk_medium_threshold` (min=30.0, no max)
- `rsi_oversold_threshold` (min=20.0, no max)

**Recommendation:** Add maximum bounds to prevent runaway tuning.

---

### ⚠️ One-Directional Tuning

Some parameters only tune in one direction:
- **Risk thresholds:** Only decrease, never increase
- **RSI:** Only tightens (decreases), never loosens

**Recommendation:** Add bidirectional tuning logic with recovery mechanisms.

---

### ⚠️ No Statistical Significance Testing

Tuning decisions are made without statistical tests:
- No p-values for performance differences
- No confidence intervals on metrics
- No minimum sample size requirements

**Recommendation:** Add statistical testing before making tuning changes.

---

### ⚠️ Fixed Step Sizes

All step sizes are constant and don't adapt to:
- Confidence in the decision
- Magnitude of performance deviation
- Recent parameter volatility

**Recommendation:** Implement adaptive step sizing (e.g., learning rate schedules).

---

### ⚠️ Tuning Thresholds Are Magic Numbers

The tuning system is controlled by 67 "tuning logic" parameters that are **never validated or tuned**:
- Why is 65% the threshold for "good" win rate?
- Why is 45% the threshold for "bad" win rate?
- Why is 0.7 the threshold for "effective" sells?

**Recommendation:** Validate these thresholds using historical data or make them adaptive.

---

## Recommendations for Improvement

### Phase 1: Fix Critical Issues (Immediate)

1. **Add risk score weight tuning**
   - Optimize `risk_volatility_weight` and `risk_correlation_weight`
   - Use Sharpe ratio as optimization target

2. **Add missing upper bounds**
   - Cap all parameters that currently have no maximum

3. **Enable bidirectional tuning**
   - Allow risk thresholds to increase when too conservative
   - Allow RSI thresholds to loosen when too tight

4. **Enforce out-of-sample validation**
   - Reject parameter changes that fail validation
   - Log validation failures for analysis

---

### Phase 2: Expand Tuning Coverage (1-2 weeks)

5. **Add regime detection tuning**
   - Tune regime thresholds and weights based on regime classification accuracy

6. **Add confidence scoring tuning**
   - Optimize confidence parameters based on realized confidence-stratified returns

7. **Add mean reversion tuning**
   - Tune MR thresholds and bonuses based on MR signal performance

8. **Add diversification tuning**
   - Optimize diversification limits based on portfolio Sharpe ratio

---

### Phase 3: Statistical Rigor (2-4 weeks)

9. **Implement Bayesian optimization**
   - Replace rule-based tuning with optimization algorithms
   - Use Gaussian processes for parameter search

10. **Add cross-validation**
    - Replace single train/test split with k-fold or walk-forward CV

11. **Add statistical significance testing**
    - Only make changes if performance difference is statistically significant

12. **Implement adaptive step sizes**
    - Adjust step sizes based on confidence and recent volatility

---

### Phase 4: Advanced Optimization (4+ weeks)

13. **Multi-objective optimization**
    - Optimize for Sharpe, drawdown, and win rate simultaneously
    - Generate Pareto frontier of parameter sets

14. **Parameter interaction analysis**
    - Identify correlations between parameters
    - Perform joint optimization of related parameters

15. **Regime-dependent tuning**
    - Tune parameters separately for bull/bear/neutral markets
    - Automatically switch parameter sets based on regime

16. **Monte Carlo robustness testing**
    - Test tuned parameters on synthetic market data
    - Measure sensitivity to initial conditions

---

## Measurement of Tuning Results

### Current Metrics

**Trade-Level Metrics:**
- P&L at 10d, 20d, 30d horizons
- Win rate
- Drawdown contribution
- Trade score (-1 to +1)

**Portfolio-Level Metrics:**
- Sharpe ratio (annualized)
- Maximum drawdown
- Total return

**Condition-Based Metrics:**
- Performance in momentum vs choppy markets
- Performance by confidence bucket
- Performance by signal type

---

### Missing Metrics

❌ **Risk-Adjusted Metrics:**
- Sortino ratio (downside-only risk)
- Calmar ratio (return / max DD)
- Omega ratio

❌ **Robustness Metrics:**
- Parameter stability over time
- Validation error (train vs test)
- Regime consistency

❌ **Efficiency Metrics:**
- Trade frequency
- Capital utilization
- Turnover costs

❌ **Statistical Metrics:**
- P-values for performance changes
- Confidence intervals on Sharpe
- Statistical significance of win rate changes

---

## Conclusion

### Summary of Findings

1. **✅ Good:** Variable name consistency, comprehensive parameterization
2. **⚠️ Concerning:** Only 16.6% of parameters are actively tuned
3. **🚨 Critical:** Risk score weights (the original problem) are still not tuned
4. **⚠️ Major Gap:** No statistical rigor - purely rule-based tuning
5. **⚠️ Overfitting Risk:** Weak validation, no cross-validation
6. **⚠️ Slow Adaptation:** Fixed step sizes may be too conservative

### Next Steps

**Immediate (This Week):**
1. Run `train_config_locally.py` to verify it executes without errors
2. Fix missing upper bounds
3. Add risk score weight tuning

**Short-Term (This Month):**
4. Expand tuning coverage to critical parameters
5. Implement statistical significance testing
6. Add stronger overfitting protection

**Long-Term (This Quarter):**
7. Replace rule-based tuning with Bayesian optimization
8. Implement cross-validation and regime-dependent tuning
9. Add comprehensive robustness testing

---

**Document Status:** Draft for Review
**Last Updated:** 2025-11-25
**Next Review:** After `train_config_locally.py` execution
