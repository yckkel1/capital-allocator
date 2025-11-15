# Production Deployment Design

## Overview

This document outlines the production deployment strategy for the Capital Allocator system, including scheduled jobs, execution flows, and configuration requirements.

---

## Cron Jobs Configuration

### Daily Jobs (Trading Days Only: Mon-Fri)

| Job | Cron Expression | Time (ET) | Command | Purpose |
|-----|----------------|-----------|---------|---------|
| **Fetch Market Data** | `35 16 * * 1-5` | 4:35 PM | `python scripts/fetch_data.py` | Collect closing prices from Alpha Vantage |
| **Generate Signal** | `0 6 * * 1-5` | 6:00 AM | `python scripts/generate_signal.py` | Create allocation signal for today |
| **Execute Trades** | `30 9 * * 1-5` | 9:30 AM | `python execute_trades.py` | Execute orders at market open |

### Monthly Jobs

| Job | Cron Expression | Timing | Command | Purpose |
|-----|----------------|--------|---------|---------|
| **Strategy Tuning** | `30 9 1-3 * 1-5` | 9:30 AM, 1st-3rd of month | `./run_monthly_tuning.sh` | Auto-tune parameters based on performance |

---

## Complete Cron Configuration

```bash
# Capital Allocator - Production Cron Schedule
# All times in Eastern Time (ET)

# ===========================================
# DAILY JOBS (Mon-Fri Only)
# ===========================================

# 1. Fetch market data after close (4:35 PM ET)
# - Fetches OHLCV data for SPY, QQQ, DIA
# - Runs 5 minutes after close to ensure data availability
35 16 * * 1-5 cd /path/to/capital-allocator/backend && python scripts/fetch_data.py >> /var/log/capital-allocator/fetch.log 2>&1

# 2. Generate trading signal (6:00 AM ET)
# - Analyzes market regime (bullish/bearish/neutral)
# - Calculates risk score and asset rankings
# - Determines BUY/SELL/HOLD action with allocations
0 6 * * 1-5 cd /path/to/capital-allocator/backend && python scripts/generate_signal.py >> /var/log/capital-allocator/signal.log 2>&1

# 3. Execute trades at market open (9:30 AM ET)
# - Uses opening price for trade execution
# - Updates portfolio positions
# - Records all trades with signal linkage
30 9 * * 1-5 cd /path/to/capital-allocator/backend && python execute_trades.py >> /var/log/capital-allocator/trades.log 2>&1

# ===========================================
# MONTHLY JOBS
# ===========================================

# 4. Strategy tuning (9:30 AM ET, 1st-3rd of month)
# - Only executes on 1st trading day of month
# - Script internally checks for correct timing
30 9 1-3 * 1-5 cd /path/to/capital-allocator && ./run_monthly_tuning.sh >> /var/log/capital-allocator/tuning.log 2>&1

# ===========================================
# OPTIONAL: API Server Health Check
# ===========================================

# 5. Keep API server running (if using main.py)
# Check every 5 minutes, restart if down
*/5 * * * * pgrep -f "uvicorn main:app" || cd /path/to/capital-allocator/backend && uvicorn main:app --host 0.0.0.0 --port 8000 &
```

---

## Logical Flow for Each Job

### 1. Fetch Market Data (4:35 PM ET)

```
fetch_data.py
│
├─► Check Alpha Vantage API Key
│
├─► For each asset [SPY, QQQ, DIA]:
│   │
│   ├─► Fetch daily OHLCV from Alpha Vantage
│   │   └─► API: TIME_SERIES_DAILY
│   │
│   ├─► Check if date already exists in DB
│   │   └─► Skip if duplicate (idempotent)
│   │
│   ├─► Insert into price_history table:
│   │   └─► date, symbol, open, high, low, close, volume
│   │
│   └─► Rate limit: 15s delay between calls (5 calls/min limit)
│
└─► Log: "Fetched data for X assets"

Database Impact:
- INSERT INTO price_history (new daily prices)
- Typically 3 rows per day (one per asset)
```

### 2. Generate Signal (6:00 AM ET)

```
generate_signal.py
│
├─► Load active trading config from database
│   └─► SELECT * FROM trading_config WHERE end_date IS NULL
│
├─► Fetch 60+ days of historical prices for all assets
│
├─► Calculate Features:
│   ├─► Returns: 5d, 20d, 60d for each asset
│   ├─► Volatility: 20d rolling std dev
│   ├─► Moving Averages: SMA-20, SMA-50
│   └─► Price vs MA: % distance from averages
│
├─► Determine Market Regime:
│   ├─► Momentum score = avg(5d, 20d, 60d returns)
│   ├─► Regime score = momentum×0.5 + sma20×0.3 + sma50×0.2
│   └─► Output: -1.0 (bearish) to +1.0 (bullish)
│
├─► Calculate Risk Score (0-100):
│   ├─► Volatility component: 70%
│   ├─► Correlation/diversity risk: 30%
│   └─► Higher score = higher risk
│
├─► Rank Assets by Composite Score:
│   ├─► Risk-adjusted momentum (60%)
│   ├─► Price momentum vs MAs (40%)
│   └─► Trend consistency bonus (1.5x)
│
├─► Determine Action (from config thresholds):
│   │
│   ├─► IF regime < -0.3 (bearish):
│   │   └─► ACTION = SELL (exit 30-70% of positions)
│   │
│   ├─► IF regime -0.3 to 0.3 (neutral):
│   │   └─► ACTION = HOLD or small BUY (20% allocation)
│   │
│   └─► IF regime > 0.3 (bullish):
│       ├─► Risk > 70: Allocate 30%
│       ├─► Risk 40-70: Allocate 50%
│       └─► Risk < 40: Allocate 80%
│
├─► Calculate Dollar Allocations:
│   ├─► Total budget = daily_capital × allocation_pct
│   ├─► Distribute across top assets: 40-50%, 30-35%, 15-25%
│   └─► Only positive-scored assets get allocation
│
└─► Save Signal to Database:
    └─► INSERT INTO daily_signals (trade_date, allocations, features_used)

Database Impact:
- INSERT INTO daily_signals (1 row per day)
- Stores complete signal with features for audit trail
```

### 3. Execute Trades (9:30 AM ET)

```
execute_trades.py
│
├─► Fetch Latest Signal:
│   └─► SELECT * FROM daily_signals WHERE trade_date = TODAY
│
├─► Get Current Portfolio:
│   └─► SELECT * FROM portfolio (all current positions)
│
├─► For each allocation in signal:
│   │
│   ├─► Get Opening Price:
│   │   └─► SELECT open_price FROM price_history
│   │       WHERE date = TODAY AND symbol = X
│   │
│   ├─► Calculate Quantity:
│   │   └─► quantity = allocation_amount / open_price
│   │   └─► Round to 4 decimals (fractional shares)
│   │
│   ├─► Record Trade:
│   │   └─► INSERT INTO trades
│   │       (trade_date, symbol, action, quantity, price, amount, signal_id)
│   │
│   └─► Update Portfolio:
│       ├─► IF BUY:
│       │   ├─► new_qty = old_qty + buy_qty
│       │   └─► new_avg_cost = weighted average
│       │
│       └─► IF SELL:
│           ├─► new_qty = old_qty - sell_qty
│           └─► avg_cost stays same
│
└─► Log execution summary with P&L

Database Impact:
- INSERT INTO trades (multiple rows, one per asset traded)
- UPDATE portfolio (position sizes and avg costs)
- DELETE FROM portfolio (if position fully closed)
```

### 4. Strategy Tuning (Monthly)

```
run_monthly_tuning.sh → strategy_tuning.py
│
├─► Check: Is today 1st trading day of month?
│   └─► Skip if not (unless --force flag)
│
├─► Load Current Config:
│   └─► SELECT * FROM trading_config WHERE end_date IS NULL
│
├─► Analyze Past 3 Months of Trades:
│   │
│   ├─► Score Each Trade (-1 to +1):
│   │   ├─► Profitability (10d forward): ±0.3
│   │   ├─► Sharpe impact: ±0.2
│   │   ├─► Drawdown contribution: -0.4
│   │   └─► Market alignment: ±0.3
│   │
│   ├─► Detect Market Conditions:
│   │   ├─► Momentum (strong trend, R² > 0.6)
│   │   └─► Choppy (low R², high volatility)
│   │
│   └─► Performance by Condition:
│       ├─► Win rate, avg P&L, trade counts
│       └─► Buy vs Hold analysis
│
├─► Generate Recommendations:
│   ├─► IF win rate > 65% but < 50% buys:
│   │   └─► "Be more aggressive"
│   │
│   ├─► IF losing in choppy markets:
│   │   └─► "Reduce neutral allocation"
│   │
│   └─► IF drawdown exceeded tolerance:
│       └─► "Tighten risk thresholds"
│
├─► Adjust Parameters:
│   ├─► Allocation: ±0.05 to ±0.1
│   ├─► Risk thresholds: ±5 points
│   └─► Conservative, incremental changes
│
├─► Version Config in Database:
│   ├─► UPDATE trading_config
│   │   SET end_date = LAST_DAY_OF_PREVIOUS_MONTH
│   │   WHERE end_date IS NULL
│   │
│   └─► INSERT INTO trading_config
│       (start_date = FIRST_OF_CURRENT_MONTH, end_date = NULL)
│
└─► Generate Report:
    └─► Save to data/strategy-tuning/tuning_YYYY-MM.md

Database Impact:
- UPDATE trading_config (close out old config)
- INSERT INTO trading_config (new active config)
- Complete audit trail with start_date, end_date, created_by, notes
```

---

## Daily Trading Configuration

### Active Config Query

```sql
-- Get current active configuration
SELECT * FROM trading_config WHERE end_date IS NULL;
```

### Default Configuration Values

| Parameter | Default Value | Description |
|-----------|--------------|-------------|
| **Capital Management** |||
| `daily_capital` | 1000.0 | Fresh capital injected daily ($) |
| `assets` | ["SPY", "QQQ", "DIA"] | Tradeable ETF symbols |
| `lookback_days` | 252 | Days for feature calculation (~1 year) |
| **Regime Detection** |||
| `regime_bullish_threshold` | 0.3 | Score above = bullish market |
| `regime_bearish_threshold` | -0.3 | Score below = bearish market |
| **Risk Management** |||
| `risk_high_threshold` | 70.0 | Risk score above = high risk |
| `risk_medium_threshold` | 40.0 | Risk score above = medium risk |
| `max_drawdown_tolerance` | 15.0 | Maximum acceptable drawdown % |
| `min_sharpe_target` | 1.0 | Target Sharpe ratio |
| **Allocation Percentages** |||
| `allocation_low_risk` | 0.8 | 80% of daily capital in low risk |
| `allocation_medium_risk` | 0.5 | 50% of daily capital in medium risk |
| `allocation_high_risk` | 0.3 | 30% of daily capital in high risk |
| `allocation_neutral` | 0.2 | 20% in neutral market regime |
| `sell_percentage` | 0.7 | Sell 70% of holdings in bearish regime |
| **Scoring Weights** |||
| `momentum_weight` | 0.6 | 60% weight for momentum in ranking |
| `price_momentum_weight` | 0.4 | 40% weight for price vs MA |

### Example Signal Output

```json
{
  "trade_date": "2025-11-15",
  "model_type": "regime_based",
  "confidence_score": 0.45,
  "allocations": {
    "SPY": 400,
    "QQQ": 350,
    "DIA": 250
  },
  "features_used": {
    "regime": 0.45,
    "risk": 38.5,
    "action": "BUY",
    "allocation_pct": 0.8,
    "assets": {
      "SPY": {
        "returns_5d": 0.018,
        "returns_20d": 0.032,
        "returns_60d": 0.085,
        "volatility": 0.012,
        "score": 0.72
      },
      "QQQ": {
        "returns_5d": 0.022,
        "returns_20d": 0.041,
        "returns_60d": 0.092,
        "volatility": 0.015,
        "score": 0.68
      },
      "DIA": {
        "returns_5d": 0.012,
        "returns_20d": 0.025,
        "returns_60d": 0.065,
        "volatility": 0.010,
        "score": 0.58
      }
    }
  }
}
```

---

## Production Environment Setup

### Required Environment Variables

```bash
# .env.production (never commit to git)

# Database Connection (PostgreSQL)
DATABASE_URL=postgresql://user:password@host:5432/capital_allocator

# API Key (Alpha Vantage)
ALPHAVANTAGE_API_KEY=your_production_api_key
```

### Directory Structure

```
/opt/capital-allocator/           # Production installation
├── backend/                      # Core application
├── data/                         # Output reports
│   ├── back-test/               # Backtest results
│   ├── analytics/               # Performance analytics
│   └── strategy-tuning/         # Monthly tuning reports
├── logs/                         # Cron job logs
│   ├── fetch.log
│   ├── signal.log
│   ├── trades.log
│   └── tuning.log
└── .env.production              # Production secrets
```

### Logging Configuration

All cron jobs should append to log files:

```bash
# Create log directory
mkdir -p /var/log/capital-allocator

# Set up log rotation (add to /etc/logrotate.d/capital-allocator)
/var/log/capital-allocator/*.log {
    daily
    rotate 30
    compress
    missingok
    notifempty
}
```

---

## Holiday & Market Closure Handling

The current implementation runs on weekdays (Mon-Fri) via cron. For market holidays:

### Option 1: Manual Skip (Simple)

The scripts are idempotent - if no market data exists, they will:
- `fetch_data.py`: No data to fetch (gracefully handles)
- `generate_signal.py`: Will use previous day's data
- `execute_trades.py`: No opening price = no execution

### Option 2: Market Calendar Integration (Recommended)

Add market holiday check at the start of each script:

```python
# Add to scripts before execution
import pandas_market_calendars as mcal

def is_market_open(date):
    nyse = mcal.get_calendar('NYSE')
    schedule = nyse.schedule(start_date=date, end_date=date)
    return len(schedule) > 0

# Skip execution if market closed
if not is_market_open(today):
    print(f"Market closed on {today}, skipping execution")
    sys.exit(0)
```

---

## Monitoring & Alerts

### Health Checks

1. **Daily Verification** (end of day):
   - All 3 jobs completed without errors
   - Signal generated for today
   - Trades executed (if signal was BUY/SELL)
   - Price data fetched

2. **Weekly Review**:
   - Portfolio performance metrics
   - Check for any missed executions
   - Verify config is still active

3. **Monthly Review**:
   - Strategy tuning report generated
   - New config activated
   - Parameter changes are reasonable

### Alert Conditions

```bash
# Send alert if any job fails
# Add to cron after each command:
|| mail -s "Capital Allocator: Job Failed" admin@company.com

# Example:
35 16 * * 1-5 cd /app && python scripts/fetch_data.py >> logs/fetch.log 2>&1 || mail -s "Fetch Failed" admin@company.com
```

---

## Disaster Recovery

### Database Backup

```bash
# Daily backup (run after trading closes)
0 18 * * * pg_dump capital_allocator > /backup/capital_allocator_$(date +%Y%m%d).sql

# Retain 30 days
find /backup -name "capital_allocator_*.sql" -mtime +30 -delete
```

### Recovery Procedures

1. **Missing Signal**: Re-run with specific date
   ```bash
   python scripts/generate_signal.py --date YYYY-MM-DD
   ```

2. **Missing Trades**: Re-execute with date
   ```bash
   python execute_trades.py YYYY-MM-DD
   ```

3. **Database Restore**:
   ```bash
   psql capital_allocator < backup_file.sql
   ```

---

## Production Readiness Checklist

- [ ] PostgreSQL database provisioned and accessible
- [ ] `.env.production` configured with production credentials
- [ ] Database migrations applied (`001_add_trading_config.py`)
- [ ] Historical data backfilled (365 days minimum)
- [ ] Initial trading config seeded in database
- [ ] All cron jobs configured and tested
- [ ] Log directory created with proper permissions
- [ ] Log rotation configured
- [ ] Monitoring/alerting set up
- [ ] Database backup schedule configured
- [ ] Tested each job with specific dates
- [ ] Completed dry-run backtest with production config
- [ ] API server running (if dashboard needed)
- [ ] Documentation of manual intervention procedures
