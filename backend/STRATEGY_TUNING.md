# Monthly Strategy Tuning

## Overview

The monthly strategy tuning system analyzes past trading performance and automatically adjusts strategy parameters to improve future results. It's designed to run on the **1st trading day of each month** to ensure your strategy adapts to changing market conditions.

## How It Works

### 1. Trade Evaluation

The system retroactively evaluates every trade from the past N months (default: 3) based on:

- **Drawdown Impact**: Trades that caused maximum drawdown to surge are identified and penalized
- **Profitability**: Whether the trade was profitable over a 10-day horizon
- **Market Condition Alignment**: Whether the trade matched the market condition (momentum vs choppy)
- **Risk-Adjusted Returns**: Impact on the overall Sharpe ratio

Each trade receives a score from -1 (very bad) to +1 (very good).

### 2. Market Condition Detection

For each trade, the system determines whether the market was in:

- **Momentum condition**: Strong trending market with high R² (>0.6) and clear directional movement
- **Choppy condition**: Sideways or volatile market with low R² (<0.3) or high volatility
- **Mixed condition**: Neither strongly trending nor clearly choppy

### 3. Performance Analysis

The system analyzes performance across different conditions:

- **Momentum performance**: Win rate, P&L, and risk metrics during trending markets
- **Choppy performance**: Same metrics during uncertain markets
- **Overall performance**: Sharpe ratio, max drawdown, total return

### 4. Parameter Adjustment

Based on the analysis, the system adjusts strategy parameters:

#### Adjustments for Being Too Conservative in Momentum
- **Indicators**: High win rate (>65%) but low participation (<50% of trades are BUYs) during momentum
- **Action**: Increase `allocation_low_risk` and `allocation_medium_risk` by 0.1

#### Adjustments for Being Too Aggressive in Momentum
- **Indicators**: Low win rate, high drawdown contribution
- **Action**: Decrease allocation percentages by 0.1

#### Adjustments for Choppy Markets
- **Indicators**: Poor performance (low win rate, high drawdown) during choppy conditions
- **Action**: Reduce `allocation_neutral` and lower `risk_medium_threshold`

#### Drawdown Management
- **Indicators**: Max drawdown exceeded tolerance threshold
- **Action**: Tighten risk controls by reducing `risk_high_threshold` and `allocation_high_risk`

#### Sharpe Ratio Optimization
- **Below target**: Increase selectivity by raising `regime_bullish_threshold` and lowering `risk_medium_threshold`
- **Above target**: Can afford to be more aggressive, reduce `regime_bullish_threshold`

#### Bearish Market Performance
- **Indicators**: Poor average score during bearish regime
- **Action**: Increase `sell_percentage` to exit positions faster

## Usage

### Running on 1st Trading Day

```bash
cd backend
python run_monthly_tuning.py
```

The script will:
1. Check if today is the 1st trading day of the month
2. Analyze the past 3 months of performance
3. Generate a comprehensive report
4. Update `.env.dev` with new parameters
5. Save a JSON file with parameter values

### Force Running (For Testing)

```bash
python run_monthly_tuning.py --force
```

### Custom Lookback Period

```bash
python run_monthly_tuning.py --lookback-months 6
```

## Output Files

### 1. Tuning Report (`.txt`)

Location: `data/strategy-tuning/strategy_tuning_report_YYYY-MM-DD_to_YYYY-MM-DD_TIMESTAMP.txt`

Contains:
- Overall performance metrics (return, Sharpe, max drawdown)
- Trade evaluation summary (good vs bad trades)
- Performance breakdown by market condition
- **Parameter changes table** showing old vs new values
- Insights and recommendations

### 2. Updated Parameters (`.env.dev`)

Location: `.env.dev` (project root)

Contains all strategy parameters with updated values. **You must manually copy parameters to your `.env` file to apply them.**

### 3. Parameters JSON

Location: `data/strategy-tuning/tuned_parameters.json`

JSON format of all parameters for programmatic access.

## Understanding the Report

### Trade Evaluation Summary

```
Total Trades Analyzed: 45
Good Trades (score > 0.3): 28 (62.2%)
Trades That Should Have Been Avoided: 8 (17.8%)

❌ Worst Trades (should have avoided):
  2024-01-15 | QQQ BUY | Condition: choppy | DD contribution: 35.2% | P&L: $-125.43
```

This shows trades that:
- Contributed significantly to drawdown (>20%)
- Were made during choppy markets but weren't profitable
- Had negative Sharpe impact

### Performance by Condition

```
MOMENTUM:
  Trades: 25
  Win Rate: 72.0%
  Avg Score: +0.245
  💡 INSIGHT: Strategy is too conservative in momentum conditions
```

This insight indicates you're missing opportunities - the strategy should be more aggressive.

```
CHOPPY:
  Trades: 15
  Win Rate: 40.0%
  Avg Score: -0.123
  ⚠️  INSIGHT: Strategy is too aggressive in choppy conditions
```

This indicates poor performance during uncertainty - reduce exposure.

### Parameter Changes

```
Parameter                                Old Value       New Value       Change
------------------------------------------------------------------------------------
📈 allocation_low_risk                   0.800           0.900          +0.100
📉 allocation_neutral                    0.200           0.150          -0.050
  regime_bullish_threshold               0.300           0.300          --
```

- 📈 = Parameter increased
- 📉 = Parameter decreased
- (no icon) = No change

## Applying Parameter Changes

1. **Review the report** in `data/strategy-tuning/`
2. **Open `.env.dev`** to see updated parameters
3. **Copy parameters to `.env`** that you want to apply:

```bash
# Example: Copy specific parameters
# From .env.dev to .env

ALLOCATION_LOW_RISK=0.9
ALLOCATION_NEUTRAL=0.15
```

4. **Validate with backtest** (optional but recommended):

```bash
# Run backtest with new parameters
python run_backtest_with_analytics.py --start-date 2024-10-01 --end-date 2024-11-12
```

5. **Monitor performance** over the next month

## Strategy Parameters Reference

| Parameter | Description | Default | Range |
|-----------|-------------|---------|-------|
| `regime_bullish_threshold` | Minimum regime score to consider market bullish | 0.3 | 0.1 - 0.5 |
| `regime_bearish_threshold` | Maximum regime score to consider market bearish | -0.3 | -0.5 - -0.1 |
| `risk_high_threshold` | Risk score above which is considered high risk | 70.0 | 60 - 80 |
| `risk_medium_threshold` | Risk score above which is considered medium risk | 40.0 | 30 - 50 |
| `allocation_low_risk` | % of capital to allocate in bullish/low-risk regime | 0.8 | 0.5 - 1.0 |
| `allocation_medium_risk` | % of capital to allocate in bullish/medium-risk regime | 0.5 | 0.3 - 0.7 |
| `allocation_high_risk` | % of capital to allocate in bullish/high-risk regime | 0.3 | 0.2 - 0.5 |
| `allocation_neutral` | % of capital to allocate in neutral regime | 0.2 | 0.1 - 0.4 |
| `sell_percentage` | % of holdings to sell in bearish regime | 0.7 | 0.5 - 0.9 |
| `max_drawdown_tolerance` | Target max drawdown % | 15.0 | 10 - 25 |
| `min_sharpe_target` | Target Sharpe ratio | 1.0 | 0.5 - 2.0 |

## Best Practices

1. **Run Monthly**: Execute on the 1st trading day to incorporate the previous month's data
2. **Review Changes**: Don't blindly apply all changes - review the reasoning in the report
3. **Gradual Adjustments**: The system makes conservative 0.05-0.1 adjustments to avoid over-fitting
4. **Validate**: Run backtests with new parameters before going live
5. **Monitor**: Track how parameter changes affect real-world performance
6. **Keep History**: Reports are timestamped - compare month-over-month trends

## Troubleshooting

### Error: "No performance data found"

**Cause**: Not enough backtest data in the database

**Solution**: Run backtest for at least 2-3 months:
```bash
python run_backtest_with_analytics.py --start-date 2024-08-01 --end-date 2024-11-12
```

### No Parameter Changes Recommended

**Cause**: Strategy is performing well within targets

**Action**: This is good! No changes needed. The report will say:
```
✅ No parameter changes recommended - current strategy is performing well!
```

### Large Parameter Changes

**Cause**: Significant performance issues detected

**Action**:
1. Review the "Worst Trades" section to understand what went wrong
2. Check the market condition analysis
3. Consider applying changes gradually (50% of recommended change)

## Technical Details

### Market Condition Detection Algorithm

1. Get 20-day price history
2. Calculate linear regression slope and R²
3. Calculate volatility (std dev of returns)
4. Classification:
   - **Momentum**: R² > 0.6 AND abs(slope) > 0.1
   - **Choppy**: R² < 0.3 OR volatility > 0.02
   - **Mixed**: Everything else

### Trade Score Calculation

```python
score = 0.0

# Positive factors (+)
if profitable: score += 0.3
if sharpe_impact > 0: score += 0.2
if drawdown_contribution < 5%: score += 0.2
if momentum_market AND buy AND profitable: score += 0.3

# Negative factors (-)
if not profitable: score -= 0.3
if drawdown_contribution > 20%: score -= 0.4
if sharpe_impact < 0: score -= 0.2
if choppy_market AND buy AND not profitable: score -= 0.3

# Clamp to [-1, 1]
```

### Drawdown Contribution Calculation

1. Find peak value before trade
2. Find trough value after trade (up to 10 days)
3. Calculate drawdown percentage
4. Attribute trade's P&L proportionally to the drawdown

## Future Enhancements

Potential improvements for future versions:

- [ ] Machine learning-based parameter optimization
- [ ] Multi-objective optimization (Sharpe, drawdown, return)
- [ ] Regime-specific parameter sets
- [ ] Automatic parameter application (with safeguards)
- [ ] Email/Slack notifications of parameter changes
- [ ] A/B testing framework for parameter validation

## Questions?

Review the generated reports in `data/strategy-tuning/` for detailed analysis and insights.
