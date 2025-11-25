# Remaining Hard-Coded Values in strategy_tuning.py

## Category 1: Trade Evaluation DD Thresholds (2 values)

**Location:** `evaluate_trades()` lines 301, 314

```python
# Line 301 - Low DD bonus threshold
if drawdown_contribution < 5:  # Low DD contribution is good
    score += self.config.score_low_dd_bonus

# Line 314 - High DD penalty threshold
if drawdown_contribution > 20:  # High DD contribution is bad
    score += self.config.score_high_dd_penalty
```

**Needed Parameters:**
- `score_dd_low_threshold` = 5.0
- `score_dd_high_threshold` = 20.0

---

## Category 2: Validation Score Weights (2 values)

**Location:** `perform_out_of_sample_validation()` lines 541-544

```python
# Line 541-544 - Validation score increments
if sharpe_passes:
    validation_score += 0.5
if drawdown_passes:
    validation_score += 0.5
```

**Needed Parameters:**
- `validation_sharpe_weight` = 0.5
- `validation_drawdown_weight` = 0.5

---

## Category 3: Parameter Tuning Boundary Limits (40+ values)

### Allocation Parameter Limits (10 values)

**Location:** `tune_parameters()` lines 650-673

```python
# Lines 650-651 - Aggressive allocation increases
new_params.allocation_low_risk = min(1.0, new_params.allocation_low_risk + step)
new_params.allocation_medium_risk = min(0.7, new_params.allocation_medium_risk + step)

# Lines 656-657 - Conservative allocation decreases
new_params.allocation_low_risk = max(0.5, new_params.allocation_low_risk - step)
new_params.allocation_medium_risk = max(0.3, new_params.allocation_medium_risk - step)

# Line 663 - Neutral allocation minimum
new_params.allocation_neutral = max(0.1, new_params.allocation_neutral - step)

# Line 671 - High risk allocation minimum
new_params.allocation_high_risk = max(0.2, new_params.allocation_high_risk - step)
```

**Needed Parameters:**
- `tune_allocation_low_risk_max` = 1.0
- `tune_allocation_low_risk_min` = 0.5
- `tune_allocation_medium_risk_max` = 0.7
- `tune_allocation_medium_risk_min` = 0.3
- `tune_allocation_high_risk_min` = 0.2
- `tune_allocation_neutral_min` = 0.1

### Risk Threshold Limits (4 values)

**Location:** `tune_parameters()` lines 664, 670, 679

```python
# Lines 664, 679 - Medium risk threshold minimum
new_params.risk_medium_threshold = max(30.0, new_params.risk_medium_threshold - step)

# Line 670 - High risk threshold minimum
new_params.risk_high_threshold = max(60.0, new_params.risk_high_threshold - step)
```

**Needed Parameters:**
- `tune_risk_medium_threshold_min` = 30.0
- `tune_risk_high_threshold_min` = 60.0

### Regime Threshold Limits (4 values)

**Location:** `tune_parameters()` lines 678, 683

```python
# Line 678 - Bullish threshold maximum
new_params.regime_bullish_threshold = min(0.4, new_params.regime_bullish_threshold + step)

# Line 683 - Bullish threshold minimum
new_params.regime_bullish_threshold = max(0.2, new_params.regime_bullish_threshold - step)
```

**Needed Parameters:**
- `tune_regime_bullish_threshold_max` = 0.4
- `tune_regime_bullish_threshold_min` = 0.2

### Sell Percentage Limits (4 values)

**Location:** `tune_parameters()` lines 708, 712, 717, 725

```python
# Line 708 - Sell percentage minimum
new_params.sell_percentage = max(0.3, new_params.sell_percentage - adjustment)

# Lines 712, 717, 725 - Sell percentage maximum (appears 3 times)
new_params.sell_percentage = min(0.9, new_params.sell_percentage + adjustment)
```

**Needed Parameters:**
- `tune_sell_percentage_min` = 0.3
- `tune_sell_percentage_max` = 0.9

### Confidence Parameter Limits (4 values)

**Location:** `tune_parameters()` lines 735, 740

```python
# Line 735 - Min confidence threshold maximum
new_params.min_confidence_threshold = min(0.5, new_params.min_confidence_threshold + step)

# Line 740 - Confidence scaling factor maximum
new_params.confidence_scaling_factor = min(0.8, new_params.confidence_scaling_factor + step)
```

**Needed Parameters:**
- `tune_min_confidence_threshold_max` = 0.5
- `tune_confidence_scaling_factor_max` = 0.8

### Mean Reversion Limits (4 values)

**Location:** `tune_parameters()` lines 750, 755

```python
# Line 750 - Mean reversion allocation maximum
new_params.mean_reversion_allocation = min(0.6, new_params.mean_reversion_allocation + step)

# Line 755 - RSI oversold threshold minimum
new_params.rsi_oversold_threshold = max(20.0, new_params.rsi_oversold_threshold - step)
```

**Needed Parameters:**
- `tune_mean_reversion_allocation_max` = 0.6
- `tune_rsi_oversold_threshold_min` = 20.0

---

## Summary

**Total Remaining Hard-Coded Values:** 22 unique parameters needed

### Breakdown:
1. **Trade Evaluation DD Thresholds:** 2 params
2. **Validation Weights:** 2 params
3. **Tuning Boundary Limits:** 18 params
   - Allocation limits: 6
   - Risk threshold limits: 2
   - Regime threshold limits: 2
   - Sell percentage limits: 2
   - Confidence limits: 2
   - Mean reversion limits: 2

---

## Action Plan

1. Add 22 new columns to `trading_config` table in models.py
2. Add 22 new fields to TradingConfig dataclass in config_loader.py
3. Update schema migration with 22 new columns
4. Update seed data SQL with 22 default values
5. Refactor strategy_tuning.py to use all 22 new parameters
