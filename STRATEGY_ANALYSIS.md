# Trading Strategy Issues - Analysis & Fixes

## Problems Identified

### 1. Too Few SELL Actions (24 sells vs 2691 buys)
**Current Logic:**
- Only sells when:
  - risk_score > 85 (extreme, rare)
  - OR bearish regime + has holdings
- In neutral/bullish: almost never sells

**Issue:** No profit-taking mechanism, no rebalancing, positions held forever

### 2. Too Conservative (mostly 33-44% allocation, rarely >50%)
**Current Logic:**
```python
# Base allocation (70-100%)
→ Scaled by confidence (typically 0.1-0.5)
→ Further reduced by risk penalties
→ Result: 33-44% actual allocation
```

**Issue:** Double-penalty system (confidence AND risk both reduce allocation)

### 3. Excessive HOLDs (entire 2022 = all HOLD)
**Current Logic:**
- Neutral regime + risk > 60: HOLD
- Bullish regime + risk > 75: HOLD
- Risk scores often > 60 in normal markets

**Issue:** Risk threshold too low, stays defensive too long

### 4. No Contrarian Signals
**Current Logic:**
- Mean reversion only triggers in neutral + low risk
- Doesn't buy aggressively during crashes
- Doesn't sell during euphoria

**Issue:** Momentum-only, misses counter-cyclical opportunities

### 5. Past Trauma Persists Too Long
**Current Logic:**
- Volatility calculated over 252 days
- One bad month affects next 12 months
- Recent stability discount helps but not enough

**Issue:** Historical volatility dominates recent conditions

## Root Cause: EV Calculation

**Current approach has NO explicit EV calculation!**
- Decision based on: regime + risk thresholds
- Allocation based on: fixed % × confidence scaling
- No consideration of:
  - Expected return vs risk
  - Sharpe ratio optimization
  - Kelly criterion
  - Position sizing based on edge

## Proposed Fixes

### Fix 1: Add Proper SELL Logic
```python
# SELL when:
1. Portfolio up >10% this month → take profits (25% sell)
2. Individual position up >20% → trim winner (30% sell)
3. Bearish regime → reduce exposure
4. Risk >80 → emergency exit
```

### Fix 2: Remove Double-Penalty
```python
# Current: allocation = base × confidence × (1 - risk_penalty)
# New: allocation = base × MAX(confidence, 1 - risk_penalty)
# Don't penalize twice for same thing
```

### Fix 3: Lower Risk Thresholds
```python
# Current: HOLD if risk > 60 (too conservative)
# New: HOLD if risk > 80 (emergency only)
# Let base allocations handle medium risk
```

### Fix 4: Add Contrarian Signals
```python
# Market dumps >5% in week → BUY MORE (1.5× allocation)
# Market rallies >3 days straight + RSI >70 → SELL 20%
# VIX spikes → opportunity, not threat
```

### Fix 5: Reduce Historical Memory
```python
# Current: 252-day volatility lookback
# New: 60-day volatility for decision-making
#      252-day for context only
```

### Fix 6: Add EV-Based Position Sizing
```python
def calculate_ev_allocation(regime_score, sharpe_estimate, volatility):
    # Kelly-lite: f = edge / odds
    expected_return = regime_score * 0.1  # 10% per regime unit
    edge = expected_return / volatility
    kelly_fraction = edge / 2  # Half-Kelly for safety
    return min(1.0, max(0.3, kelly_fraction))
```

## Implementation Priority

1. **CRITICAL: Fix SELL logic** - add profit-taking and rebalancing
2. **CRITICAL: Remove risk double-penalty** - let confidence OR risk determine allocation, not both
3. **HIGH: Add contrarian signals** - buy dumps, sell rallies
4. **MEDIUM: Lower risk thresholds** - 60 → 80 for HOLD trigger
5. **MEDIUM: Reduce volatility lookback** - 252 → 60 days
6. **LOW: Add EV calculation** - nice-to-have, can be tuned later

## Expected Outcomes

- **More SELLs**: ~10-15% of days (vs current 1%)
- **Higher allocations**: 60-80% average (vs current 35-45%)
- **Fewer HOLDs**: ~20% of days (vs current 40-50%)
- **Better drawdown recovery**: Re-enter within 2-4 weeks (vs current 3-6 months)
- **Contrarian gains**: Buy dumps at -10%, sell rallies at +15%
