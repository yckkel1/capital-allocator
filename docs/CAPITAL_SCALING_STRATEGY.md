# Capital-Scaled Position Sizing Strategy

## Critical Issue: Fixed Allocation Percentages Don't Scale

### The Problem

**Current Implementation:** The system uses fixed allocation percentages regardless of capital size:
- `allocation_low_risk = 0.8` (80%)
- `allocation_medium_risk = 0.5` (50%)
- `allocation_high_risk = 0.3` (30%)

**Why This Is Wrong:**

| Capital Size | 80% Allocation | Absolute Risk | Risk Appropriateness |
|--------------|----------------|---------------|----------------------|
| $1,000       | $800           | Can lose $80 (10% drop) | ✓ Acceptable |
| $10,000      | $8,000         | Can lose $800 (10% drop) | ⚠️ Questionable |
| $100,000     | $80,000        | Can lose $8,000 (10% drop) | ❌ Too aggressive |
| $500,000     | $400,000       | Can lose $40,000 (10% drop) | ❌ Catastrophic risk |

**The mathematical perspective ("80% is 80%") ignores fundamental investment principles:**

1. **Risk of Ruin** - Larger positions increase probability of unrecoverable losses
2. **Market Impact** - Large positions harder to exit, worse slippage
3. **Volatility Drag** - Larger percentage swings hurt compound returns
4. **Psychological Limits** - Losing $40k in a day is not 50x worse than losing $800
5. **Opportunity Cost** - Large positions limit diversification and flexibility

---

## Quantitative Framework for Capital Scaling

### 1. Kelly Criterion (Optimal Bet Sizing)

**Formula:**
```
f* = (bp - q) / b

where:
- f* = fraction of capital to bet
- b = odds received (payoff ratio)
- p = probability of winning
- q = probability of losing (1 - p)
```

**Application:**
```python
def kelly_allocation(win_rate: float, avg_win: float, avg_loss: float,
                      capital: float, kelly_fraction: float = 0.25) -> float:
    """
    Calculate Kelly-optimal position size, scaled by capital

    Args:
        win_rate: Historical win rate (0-1)
        avg_win: Average winning trade return (%)
        avg_loss: Average losing trade return (%)
        capital: Current capital size
        kelly_fraction: Fractional Kelly (0.25 = quarter Kelly for safety)

    Returns:
        Recommended allocation percentage (0-1)
    """
    if avg_loss == 0:
        return 0.0

    payoff_ratio = abs(avg_win / avg_loss)
    kelly_pct = (win_rate * payoff_ratio - (1 - win_rate)) / payoff_ratio

    # Use fractional Kelly for safety
    allocation = max(0, min(1, kelly_pct * kelly_fraction))

    # Scale down allocation as capital grows
    capital_scale_factor = capital_scaling_adjustment(capital)

    return allocation * capital_scale_factor
```

**Key Insight:** Even full Kelly is too aggressive. Professional traders use 1/4 to 1/2 Kelly.

---

### 2. Capital Scaling Factor

**Proposed Formula:**
```python
def capital_scaling_adjustment(capital: float) -> float:
    """
    Reduce allocation percentage as capital grows

    Rationale:
    - Small capital ($1k-$10k): Can afford aggressive bets
    - Medium capital ($10k-$100k): Moderate scaling
    - Large capital ($100k+): Conservative scaling

    Returns:
        Multiplier between 0.3-1.0
    """
    if capital < 10_000:
        # Small capital: Full allocation
        return 1.0
    elif capital < 50_000:
        # Medium capital: Gradual reduction
        # Linear scale: $10k=1.0, $50k=0.7
        return 1.0 - (capital - 10_000) / 133_333
    elif capital < 200_000:
        # Large capital: More aggressive reduction
        # Linear scale: $50k=0.7, $200k=0.4
        return 0.7 - (capital - 50_000) / 500_000
    else:
        # Very large capital: Conservative minimum
        # Asymptotic approach to 0.3
        return max(0.3, 0.4 - (capital - 200_000) / 2_000_000)
```

**Example Scaling:**

| Capital    | Scale Factor | 80% Allocation Becomes | 50% Allocation Becomes |
|------------|--------------|------------------------|------------------------|
| $1,000     | 1.00         | 80%                    | 50%                    |
| $10,000    | 1.00         | 80%                    | 50%                    |
| $50,000    | 0.70         | 56%                    | 35%                    |
| $100,000   | 0.55         | 44%                    | 27.5%                  |
| $200,000   | 0.40         | 32%                    | 20%                    |
| $500,000   | 0.35         | 28%                    | 17.5%                  |
| $1,000,000 | 0.30         | 24%                    | 15%                    |

---

### 3. Volatility-Adjusted Position Sizing

**Concept:** Scale position size inversely with volatility to maintain constant risk.

```python
def volatility_adjusted_allocation(base_allocation: float,
                                    current_volatility: float,
                                    target_volatility: float = 0.01) -> float:
    """
    Adjust position size to maintain constant volatility contribution

    Args:
        base_allocation: Base allocation from regime/risk logic
        current_volatility: Current market volatility (e.g., 0.02 = 2%)
        target_volatility: Target portfolio volatility contribution

    Returns:
        Volatility-adjusted allocation
    """
    if current_volatility <= 0:
        return base_allocation

    vol_adjustment = target_volatility / current_volatility

    # Clamp to reasonable range
    return base_allocation * min(2.0, max(0.5, vol_adjustment))
```

**Example:**
- Base allocation: 50%
- Normal volatility (1%): 50% × 1.0 = 50%
- High volatility (2%): 50% × 0.5 = 25% ← Reduced exposure
- Low volatility (0.5%): 50% × 2.0 = 100% (capped) ← Increased exposure

---

### 4. Risk Parity Approach

**Concept:** Allocate capital such that each position contributes equal risk.

```python
def risk_parity_allocation(capital: float,
                           asset_volatilities: Dict[str, float],
                           total_risk_budget: float = 0.10) -> Dict[str, float]:
    """
    Calculate risk parity allocations

    Args:
        capital: Total available capital
        asset_volatilities: {symbol: annualized_volatility}
        total_risk_budget: Total portfolio risk target (e.g., 0.10 = 10% annual vol)

    Returns:
        {symbol: dollar_allocation}
    """
    # Inverse volatility weighting
    inv_vols = {s: 1/v for s, v in asset_volatilities.items()}
    total_inv_vol = sum(inv_vols.values())

    # Equal risk contribution weights
    weights = {s: iv/total_inv_vol for s, iv in inv_vols.items()}

    # Scale to risk budget
    allocations = {}
    for symbol, weight in weights.items():
        # Allocation = (weight × risk_budget × capital) / volatility
        allocations[symbol] = (weight * total_risk_budget * capital) / asset_volatilities[symbol]

    return allocations
```

---

## Recommended Implementation Strategy

### Phase 1: Add Capital Scaling to Current System

**Modify `generate_signal.py`:**

```python
def calculate_scaled_allocation(base_allocation: float,
                                 cash_balance: float,
                                 current_volatility: float) -> float:
    """
    Apply capital scaling and volatility adjustments to base allocation

    Args:
        base_allocation: Allocation from decide_action (e.g., 0.8)
        cash_balance: Current accumulated cash
        current_volatility: Market volatility

    Returns:
        Scaled allocation percentage
    """
    # 1. Capital scaling
    capital_factor = capital_scaling_adjustment(cash_balance)

    # 2. Volatility adjustment
    vol_factor = volatility_adjusted_allocation(1.0, current_volatility)

    # 3. Combined scaling
    scaled_allocation = base_allocation * capital_factor * vol_factor

    # 4. Enforce minimum/maximum bounds
    return max(0.05, min(0.60, scaled_allocation))
```

**Integration Point (Line ~831):**
```python
if action == "BUY":
    # Get base allocation from decide_action
    base_allocation = adjusted_allocation  # e.g., 0.8

    # Apply capital scaling
    scaled_allocation = calculate_scaled_allocation(
        base_allocation=base_allocation,
        cash_balance=cash_balance,
        current_volatility=avg_volatility
    )

    # Deploy capital with scaled allocation
    available_cash = cash_balance + trading_config.daily_capital
    buy_amount = available_cash * scaled_allocation

    print(f"  Base allocation: {base_allocation*100:.0f}%")
    print(f"  Capital-scaled allocation: {scaled_allocation*100:.0f}%")
    print(f"  Deploying: ${buy_amount:,.2f}")
```

---

### Phase 2: Enhanced Risk Management

**Add to `decide_action()`:**

```python
def decide_action(..., cash_balance: float = 0.0) -> tuple:
    """
    Enhanced decision logic with capital awareness
    """
    # ... existing regime/risk logic ...

    # NEW: Adjust base allocation based on capital size
    if action == "BUY":
        # Start with regime-based allocation
        base_pct = allocation_pct  # e.g., 0.8 for bullish_momentum

        # Check if we're in "large capital" territory
        if cash_balance > 100_000:
            # Reduce aggressiveness for large capital
            max_allocation = 0.4  # Cap at 40% for 6-figure portfolios
            allocation_pct = min(base_pct, max_allocation)

            if allocation_pct < base_pct:
                signal_type += "_capital_scaled"
```

---

### Phase 3: Strategy Tuning Adjustments

**Modify `strategy_tuning.py` to account for capital levels:**

```python
def evaluate_trades_by_capital_regime(evaluations: List[TradeEvaluation]) -> Dict:
    """
    Analyze trade performance across different capital levels

    Returns performance metrics segmented by:
    - Small capital (<$10k)
    - Medium capital ($10k-$100k)
    - Large capital (>$100k)
    """
    # Get capital at time of each trade
    # Evaluate if allocation percentages were appropriate
    # Tune parameters separately for each capital regime
```

---

## Risk Metrics to Monitor

### 1. Position Size as % of Capital

**Warning Thresholds:**
- Single position > 30% of capital → High concentration risk
- Single position > 50% of capital → Extreme risk
- Total deployed > 70% of capital with high volatility → Overexposed

### 2. Value at Risk (VaR)

```python
def calculate_var(position_value: float,
                  volatility: float,
                  confidence: float = 0.95,
                  time_horizon_days: int = 1) -> float:
    """
    Calculate Value at Risk

    Returns: Maximum expected loss at confidence level
    """
    from scipy.stats import norm

    z_score = norm.ppf(1 - confidence)
    daily_var = position_value * volatility * z_score * math.sqrt(time_horizon_days)

    return abs(daily_var)
```

**Example:**
- Position: $400,000
- Volatility: 2% daily
- 95% confidence VaR (1 day) = $400k × 0.02 × 1.645 = $13,160

**Action:** If VaR > 5% of total capital, reduce position size.

### 3. Maximum Drawdown by Capital Level

**Track separately:**
- Max drawdown when capital < $10k
- Max drawdown when capital $10k-$100k
- Max drawdown when capital > $100k

**Expectation:** Drawdowns should be SMALLER (as %) with larger capital due to conservative scaling.

---

## Testing Requirements

### Backtest Scenarios

1. **Small Capital Growth ($1k → $10k)**
   - Should use aggressive allocations (60-80%)
   - Fast growth acceptable
   - Higher volatility tolerable

2. **Medium Capital Growth ($10k → $100k)**
   - Gradually reducing allocations (40-60%)
   - Moderate risk taking
   - Balance growth vs preservation

3. **Large Capital Preservation ($100k+)**
   - Conservative allocations (20-40%)
   - Capital preservation priority
   - Smooth equity curves expected

### Validation Metrics

| Capital Level | Target Metrics |
|---------------|----------------|
| < $10k | Max allocation: 80%, Max drawdown: 15%, Sharpe > 1.0 |
| $10k-$100k | Max allocation: 60%, Max drawdown: 12%, Sharpe > 1.2 |
| > $100k | Max allocation: 40%, Max drawdown: 10%, Sharpe > 1.5 |

---

## Alternative Approaches to Consider

### 1. Fixed Dollar Risk Per Trade

Instead of percentage allocation, risk fixed dollars:

```python
MAX_RISK_PER_TRADE = 5000  # Never risk more than $5k per position

def fixed_dollar_risk_allocation(entry_price: float,
                                  stop_loss_pct: float) -> float:
    """
    Position size based on fixed dollar risk

    Returns: Number of shares to buy
    """
    risk_per_share = entry_price * stop_loss_pct
    shares = MAX_RISK_PER_TRADE / risk_per_share
    return shares
```

**Pros:** Simple, intuitive, automatically scales with capital
**Cons:** Doesn't account for volatility differences between assets

### 2. Maximum Position Limits

```python
def apply_position_limits(buy_amount: float,
                          total_capital: float,
                          current_positions_value: float) -> float:
    """
    Apply hard position size limits
    """
    # No single new position > 25% of total capital
    max_single_position = total_capital * 0.25

    # Total deployed (existing + new) < 70% of capital
    max_total_deployed = total_capital * 0.70
    max_new_deployment = max_total_deployed - current_positions_value

    return min(buy_amount, max_single_position, max_new_deployment)
```

### 3. Gradual Deployment with DCA

For large cash balances, deploy gradually:

```python
def calculate_dca_schedule(total_cash: float,
                           target_allocation_pct: float,
                           num_days: int = 10) -> float:
    """
    Deploy large cash reserves over multiple days

    Args:
        total_cash: Available cash to deploy
        target_allocation_pct: e.g., 0.5 for 50%
        num_days: Deploy over this many days

    Returns:
        Amount to deploy per day
    """
    total_to_deploy = total_cash * target_allocation_pct
    daily_deployment = total_to_deploy / num_days

    return daily_deployment
```

---

## Recommended Next Steps

1. **Review this document** - Validate approach and formulas

2. **Choose primary strategy:**
   - Option A: Capital scaling factor (recommended - simplest)
   - Option B: Kelly criterion (more sophisticated)
   - Option C: Risk parity (most conservative)
   - Option D: Hybrid approach

3. **Define parameters:**
   - Capital breakpoints ($10k, $50k, $100k, $200k?)
   - Scaling factors at each level
   - Maximum single position size
   - Maximum total deployment %

4. **Implementation plan:**
   - Where to add scaling logic (generate_signal.py)
   - How to track capital regime in signals
   - Updates to strategy_tuning.py
   - Backtest validation

5. **Testing strategy:**
   - Backtest on historical data with different capital levels
   - Validate that larger capital = smoother equity curves
   - Ensure no catastrophic single-day losses

---

## Conclusion

**The core issue:** Fixed allocation percentages (30%, 50%, 80%) are fundamentally inappropriate for variable capital sizes. An 80% allocation is acceptable with $1,000 but reckless with $500,000.

**The solution:** Implement capital-scaled position sizing that:
1. Reduces allocation percentages as capital grows
2. Adjusts for market volatility
3. Enforces hard limits on position sizes
4. Maintains lower drawdowns with larger capital

**Expected outcome:**
- Small capital: Aggressive growth (high risk acceptable)
- Large capital: Steady compounding (capital preservation priority)
- All capital levels: Risk-adjusted returns improve with proper scaling
