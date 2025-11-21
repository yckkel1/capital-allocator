# Capital Allocator

An automated, self-optimizing algorithmic trading system that makes daily allocation decisions across major market indexes using advanced quantitative strategies, mean reversion signals, and adaptive risk management.

---

## Table of Contents

1. [Investment Proposition](#investment-proposition)
2. [Core Investment Strategy](#core-investment-strategy)
3. [Technical Details](#technical-details)
4. [Workflow & Automation](#workflow--automation)
5. [UI & Monitoring](#ui--monitoring)
6. [Quick Start](#quick-start)
7. [Additional Documentation](#additional-documentation)

---

## Investment Proposition

### Capital Structure

- **Daily Capital Grant**: $1,000 per trading day
- **Available Assets**: Three major US market indexes
  - **SPY** (S&P 500 ETF) - Large-cap US equities
  - **QQQ** (Nasdaq-100 ETF) - Technology-focused large-caps
  - **DIA** (Dow Jones ETF) - Blue-chip industrial companies

### Trading Rules & Constraints

1. **No Same-Day Trading**:
   - Trading decisions are made at market close on Day D-1
   - Orders are executed at market opening price on Day D
   - This eliminates intraday timing risk and reduces trading costs

2. **Available Actions**:
   - **HOLD**: Maintain current positions, no trades executed
   - **BUY**: Purchase shares using available cash balance
   - **SELL**: Liquidate existing positions (typically 30-70% of holdings)

3. **Decision Timeline**:
   ```
   Day D-1, 4:35 PM ET  → Fetch closing prices for SPY, QQQ, DIA
   Day D-1, 6:00 AM ET  → Generate allocation signal based on analysis
   Day D, 9:30 AM ET    → Execute trades at market opening price
   ```

### Capital Allocation Philosophy

The system dynamically allocates capital based on:
- **Market Regime** (Bullish, Neutral, Bearish)
- **Risk Assessment** (Volatility, correlation, drawdown limits)
- **Signal Confidence** (Higher conviction → larger positions)
- **Mean Reversion Opportunities** (Oversold/overbought conditions)

Unlike traditional buy-and-hold strategies, Capital Allocator actively adjusts exposure to optimize risk-adjusted returns while preserving capital during adverse market conditions.

---

## Core Investment Strategy

### Strategy Overview: Enhanced Multi-Factor Regime-Based Approach

Capital Allocator employs a sophisticated quantitative strategy combining **momentum**, **mean reversion**, and **adaptive risk management** techniques. The system self-optimizes monthly using out-of-sample validation to prevent overfitting.

---

### 1. Market Regime Detection

**Purpose**: Identify the current market environment (Bullish, Neutral, or Bearish)

**Methodology**:
- **Multi-Timeframe Momentum**: Analyzes 5-day, 20-day, and 60-day returns
- **Moving Average Analysis**: Price position relative to SMA-20 and SMA-50
- **Weighted Scoring**:
  - Momentum: 50%
  - SMA-20 position: 30%
  - SMA-50 position: 20%

**Regime Classification**:
- **Bullish**: Regime score > 0.3 → Increase exposure
- **Neutral**: Regime score between -0.3 and 0.3 → Cautious positioning
- **Bearish**: Regime score < -0.3 → Reduce exposure

**Adaptive Thresholds**: Regime thresholds adjust based on current volatility to reduce false signals during high-volatility periods.

---

### 2. Mean Reversion Signals

**Purpose**: Capture oversold bounces and overbought corrections

**Technical Indicators**:
- **RSI (Relative Strength Index)**: 14-period RSI identifies extreme conditions
  - RSI < 30 → Oversold (potential buy)
  - RSI > 70 → Overbought (potential sell)
- **Bollinger Bands**: 20-period bands with 2 standard deviations
  - Price < Lower Band → Extreme oversold
  - Price > Upper Band → Extreme overbought

**Mean Reversion Logic**:
- In **neutral regimes**, prioritize mean reversion opportunities
- Buy signals: RSI < 30 AND Bollinger position < -0.5
- Default allocation: 40% of capital (configurable via `mean_reversion_allocation`)

**Impact**: Complements momentum strategy by capturing reversals in ranging markets.

---

### 3. Regime Transition Detection

**Purpose**: Identify early momentum shifts before full regime confirmation

**Transition Types**:
- `turning_bullish`: Regime score increasing from negative territory
- `turning_bearish`: Regime score decreasing from positive territory
- `gaining_momentum`: Already bullish and strengthening
- `losing_momentum`: Already bullish but weakening
- `stable`: No significant change

**Advantage**: Allows early entry/exit signals, capturing more of price moves while reducing lag.

---

### 4. Confidence-Based Position Sizing

**Purpose**: Size positions based on signal conviction using a Kelly Criterion-inspired approach

**Confidence Calculation**:
Combines multiple factors to produce a 0-1 confidence score:
- **Regime Strength**: How far from neutral (0-40%)
- **Risk Score**: Lower volatility increases confidence (0-30%)
- **Trend Consistency**: All timeframes aligned (0-20%)
- **Mean Reversion Alignment**: Technical indicators agree (0-10%)

**Position Sizing Formula**:
```
position_size = base_allocation × (1 + confidence × scaling_factor)
```

**Parameters**:
- `min_confidence_threshold`: Filters out low-conviction trades (default: 0.3)
- `confidence_scaling_factor`: Controls position size variance (default: 0.5)

**Example**:
- Base allocation: 50% ($500)
- Confidence score: 0.8 (high conviction)
- Position size: $500 × (1 + 0.8 × 0.5) = $700

---

### 5. Risk Management & Circuit Breakers

**Purpose**: Limit losses during adverse market conditions

**Circuit Breaker Mechanism**:
- **Monitors**: Cumulative P&L of all trades within current month
- **Trigger**: Drawdown exceeds `intramonth_drawdown_limit` (default: 10%)
- **Action**: Reduces all position sizes by `circuit_breaker_reduction` (default: 50%)
- **Reset**: Next calendar month

**Additional Risk Controls**:
- **Max Drawdown Tolerance**: 15% maximum drawdown from peak (configurable)
- **Target Sharpe Ratio**: 1.0 minimum (used in optimization)
- **Volatility Adjustment**: Position sizes decrease as volatility rises

---

### 6. Asset Ranking & Selection

**Purpose**: Identify which index(es) to allocate capital to

**Ranking Methodology**:
1. **Risk-Adjusted Momentum**: `momentum / volatility` (60% weight)
2. **Price Momentum vs Moving Averages**: Price position vs SMA-20/50 (40% weight)
3. **Trend Consistency Bonus**: 1.5× multiplier if all timeframes (5d, 20d, 60d) align
4. **Mean Reversion Bonus**: Additional scoring for oversold conditions in neutral regimes

**Allocation Distribution**:
- **Top Ranked Asset**: 40-50% of total allocation
- **Second Ranked**: 30-35%
- **Third Ranked**: 15-25%
- Only assets with positive composite scores receive capital

---

### 7. Trading Decision Logic

**Bearish Regime** (regime < -0.3):
- **Action**: SELL
- **Amount**: Liquidate `sell_percentage` (default: 70%) of weakest positions
- **Rationale**: Preserve capital, avoid drawdowns

**Neutral Regime** (-0.3 ≤ regime ≤ 0.3):
- **Action**: HOLD or small BUY
- **Amount**: `allocation_neutral` (default: 20% = $200)
- **Focus**: Mean reversion opportunities
- **Rationale**: Cautious, wait for clearer signals

**Bullish Regime** (regime > 0.3):
- **Action**: BUY
- **Amount**: Risk-adjusted allocation
  - **Low Risk** (risk < 40): `allocation_low_risk` = 80% ($800)
  - **Medium Risk** (40 ≤ risk < 70): `allocation_medium_risk` = 50% ($500)
  - **High Risk** (risk ≥ 70): `allocation_high_risk` = 30% ($300)
- **Rationale**: Maximize exposure when conditions are favorable

---

### 8. Configuration System

**Initial Configuration Selection**:
- Default parameters defined in `/home/user/capital-allocator/backend/config_loader.py:20-75`
- 27 configurable parameters covering regime detection, risk management, allocations, and mean reversion
- Stored in `trading_config` database table with versioning support

**Key Configuration Parameters**:

| Category | Parameter | Default | Description |
|----------|-----------|---------|-------------|
| **Basic** | `daily_capital` | $1,000 | Daily capital grant |
| | `assets` | [SPY, QQQ, DIA] | Tradeable indexes |
| | `lookback_days` | 252 | Historical data window (1 year) |
| **Regime** | `regime_bullish_threshold` | 0.3 | Threshold for bullish classification |
| | `regime_bearish_threshold` | -0.3 | Threshold for bearish classification |
| **Risk** | `risk_high_threshold` | 70 | Risk score above = high risk |
| | `risk_medium_threshold` | 40 | Risk score above = medium risk |
| | `max_drawdown_tolerance` | 15% | Maximum acceptable drawdown |
| | `min_sharpe_target` | 1.0 | Target Sharpe ratio |
| **Allocations** | `allocation_low_risk` | 80% | Allocation in low risk environment |
| | `allocation_medium_risk` | 50% | Allocation in medium risk environment |
| | `allocation_high_risk` | 30% | Allocation in high risk environment |
| | `allocation_neutral` | 20% | Allocation in neutral regime |
| **Mean Reversion** | `rsi_oversold_threshold` | 30 | RSI level for oversold |
| | `rsi_overbought_threshold` | 70 | RSI level for overbought |
| | `bollinger_std_multiplier` | 2.0 | Bollinger band standard deviations |
| | `mean_reversion_allocation` | 40% | Capital for mean reversion trades |
| **Confidence** | `min_confidence_threshold` | 0.3 | Minimum confidence to trade |
| | `confidence_scaling_factor` | 0.5 | Kelly-lite scaling factor |
| **Circuit Breaker** | `intramonth_drawdown_limit` | 10% | Monthly drawdown trigger |
| | `circuit_breaker_reduction` | 50% | Position size reduction when triggered |

**Configuration Versioning**:
- Each parameter set has `start_date` and `end_date`
- Active config: `WHERE end_date IS NULL`
- Monthly tuning creates new version with optimized parameters
- Complete audit trail for all parameter changes

---

### 9. Monthly Parameter Tuning

**Purpose**: Self-optimize strategy parameters based on recent performance

**Tuning Process** (runs on 1st trading day of each month):

1. **Data Collection**: Gather last 3 months of trade history
2. **Multi-Horizon Evaluation**: Analyze trade outcomes at 10, 20, and 30 days
3. **Performance Analysis**:
   - **Confidence Bucket Analysis**: High vs medium vs low confidence trades
   - **Signal Type Analysis**: Momentum vs mean reversion effectiveness
   - **Market Condition Detection**: Trending vs choppy market identification
4. **Parameter Optimization**: Adjust 12+ parameters including:
   - Regime thresholds
   - Risk thresholds
   - Allocation percentages
   - Mean reversion parameters
   - Confidence thresholds
5. **Out-of-Sample Validation**:
   - Train on 2/3 of data
   - Validate on remaining 1/3
   - Only deploy if validation Sharpe ratio ≥ target
6. **Configuration Versioning**: Create new config version, close previous version

**Tuned Parameters**:
- Regime detection thresholds
- Risk level thresholds
- Allocation percentages per risk level
- Mean reversion indicator thresholds
- Confidence scoring weights
- Circuit breaker sensitivity

**Tuning Script**: `/home/user/capital-allocator/backend/run_monthly_tuning.py`

**Safeguards**:
- Only tunes if sufficient trade history (30+ trades)
- Validation Sharpe ratio must exceed threshold
- Prevents overfitting via out-of-sample testing
- Generates detailed tuning report to `/data/strategy-tuning/`

---

### 10. Latest Optimizations (2024-2025)

**Major Enhancements**:

1. **Mean Reversion Integration**: Added RSI and Bollinger Bands to complement momentum strategy
2. **Regime Transition Detection**: 5 transition types for early signal generation
3. **Adaptive Thresholds**: Volatility-adjusted regime detection
4. **Confidence-Based Sizing**: Kelly-lite approach for position sizing
5. **Circuit Breakers**: Intra-month drawdown protection
6. **Multi-Horizon Evaluation**: 10d, 20d, 30d trade analysis for better optimization
7. **Market Condition Detection**: Identifies trending vs choppy markets for adaptive tuning

**Performance Impact**:
- Improved win rate in ranging markets via mean reversion
- Reduced false signals during high volatility via adaptive thresholds
- Better capital preservation via circuit breakers
- Higher risk-adjusted returns via confidence-based sizing

For detailed technical documentation, see: [ENHANCED_QUANT_STRATEGY.md](./docs/ENHANCED_QUANT_STRATEGY.md)

---

## Technical Details

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Capital Allocator System                  │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐      ┌──────────────┐      ┌───────────┐ │
│  │ Alpha Vantage│ ───► │  PostgreSQL  │ ◄──► │  FastAPI  │ │
│  │     API      │      │   Database   │      │    API    │ │
│  └──────────────┘      └──────────────┘      └───────────┘ │
│         │                      │                     │      │
│         ▼                      ▼                     ▼      │
│  ┌──────────────┐      ┌──────────────┐      ┌───────────┐ │
│  │ fetch_data.py│      │Trading Engine│      │    UI     │ │
│  │  (4:35 PM)   │      │generate_signal│     │ Dashboard │ │
│  └──────────────┘      │ execute_trades│     │(In Progress)│
│                        │  (6AM & 9:30AM)│     └───────────┘ │
│                        └──────────────┘              │      │
│                               │                      │      │
│                        ┌──────────────┐              │      │
│                        │Strategy Tuner│              │      │
│                        │  (Monthly)   │              │      │
│                        └──────────────┘              │      │
└─────────────────────────────────────────────────────────────┘
```

---

### Project Setup

#### Prerequisites

- **Python**: 3.8 or higher
- **PostgreSQL**: 12 or higher
- **API Key**: Alpha Vantage (free tier: 25 calls/day, sufficient for this system)
- **Operating System**: Linux/macOS recommended (cron scheduling)

#### Installation Steps

1. **Clone Repository**:
   ```bash
   git clone https://github.com/your-org/capital-allocator.git
   cd capital-allocator
   ```

2. **Create Python Virtual Environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables**:
   Create `.env` file in `/backend/` directory:
   ```bash
   DATABASE_URL=postgresql://username:password@localhost:5432/capital_allocator
   ALPHAVANTAGE_API_KEY=your_api_key_here
   ```

5. **Initialize Database**:
   ```bash
   # Create database
   createdb capital_allocator

   # Run migrations
   python -c "from database import init_db; init_db()"
   ```

6. **Verify Installation**:
   ```bash
   # Run tests
   pytest --cov=. --cov-report=term-missing

   # Should show 80%+ coverage
   ```

---

### Database Schema

#### PostgreSQL Tables Overview

The system uses 7 core tables for production and mirrored `test_*` tables for isolated testing.

#### Table Definitions

**1. `price_history` - Daily OHLCV Market Data**

Stores historical price data for SPY, QQQ, DIA from Alpha Vantage.

| Column | Type | Description |
|--------|------|-------------|
| `id` | SERIAL PRIMARY KEY | Auto-incrementing ID |
| `date` | DATE NOT NULL | Trading date |
| `symbol` | VARCHAR(10) NOT NULL | Ticker (SPY/QQQ/DIA) |
| `open_price` | NUMERIC(10,2) | Opening price |
| `high_price` | NUMERIC(10,2) | Intraday high |
| `low_price` | NUMERIC(10,2) | Intraday low |
| `close_price` | NUMERIC(10,2) NOT NULL | Closing price (used for analysis) |
| `volume` | BIGINT | Trading volume |
| `created_at` | TIMESTAMP | Record creation timestamp |

**Indexes**: `(date, symbol)` UNIQUE, `(symbol, date)` for efficient queries

**Typical Size**: ~750 rows/year (3 assets × 250 trading days)

---

**2. `daily_signals` - AI-Generated Trading Signals**

Stores the output of signal generation algorithm with rich metadata.

| Column | Type | Description |
|--------|------|-------------|
| `id` | SERIAL PRIMARY KEY | Auto-incrementing ID |
| `trade_date` | DATE NOT NULL | Date for which signal applies |
| `generated_at` | TIMESTAMP | When signal was generated |
| `allocations` | JSONB NOT NULL | Asset allocations with dollar amounts |
| `model_type` | VARCHAR(50) | Always "enhanced_regime_based" |
| `confidence_score` | NUMERIC(5,4) | Signal confidence (0-1) |
| `features_used` | JSONB | Feature values (regime, risk, RSI, etc.) |

**Example `allocations` JSON**:
```json
{
  "action": "BUY",
  "regime": "bullish",
  "regime_score": 0.45,
  "risk_level": "medium",
  "risk_score": 52,
  "assets": {
    "SPY": {"allocation": 400, "score": 0.78},
    "QQQ": {"allocation": 100, "score": 0.45}
  },
  "circuit_breaker_active": false
}
```

**Typical Size**: ~250 rows/year (1 signal per trading day)

---

**3. `trades` - Executed Trade History**

Records all executed trades with linkage to originating signal.

| Column | Type | Description |
|--------|------|-------------|
| `id` | SERIAL PRIMARY KEY | Auto-incrementing ID |
| `trade_date` | DATE NOT NULL | Execution date |
| `executed_at` | TIMESTAMP | Exact execution time |
| `symbol` | VARCHAR(10) NOT NULL | Asset ticker |
| `action` | VARCHAR(10) NOT NULL | BUY, SELL, or HOLD |
| `quantity` | NUMERIC(10,4) | Number of shares |
| `price` | NUMERIC(10,2) | Execution price (opening price) |
| `amount` | NUMERIC(12,2) | Total dollar amount (qty × price) |
| `signal_id` | INTEGER | Foreign key to `daily_signals.id` |

**Indexes**: `(trade_date)`, `(symbol)`, `(signal_id)` for fast joins

**Typical Size**: ~2-3 trades/day, ~600 rows/year

---

**4. `portfolio` - Current Holdings**

Tracks current positions with weighted average cost basis.

| Column | Type | Description |
|--------|------|-------------|
| `id` | SERIAL PRIMARY KEY | Auto-incrementing ID |
| `symbol` | VARCHAR(10) UNIQUE NOT NULL | Asset ticker |
| `quantity` | NUMERIC(10,4) NOT NULL | Current shares held |
| `avg_cost` | NUMERIC(10,2) NOT NULL | Weighted average cost per share |
| `last_updated` | TIMESTAMP | Last modification timestamp |

**Note**: Updated on every BUY (weighted avg) and SELL (no cost basis change)

**Typical Size**: 0-3 rows (one per held asset)

---

**5. `performance_metrics` - Daily P&L Tracking**

Calculates and stores daily performance metrics for analytics.

| Column | Type | Description |
|--------|------|-------------|
| `id` | SERIAL PRIMARY KEY | Auto-incrementing ID |
| `date` | DATE UNIQUE NOT NULL | Calculation date |
| `portfolio_value` | NUMERIC(12,2) | Market value of holdings |
| `cash_balance` | NUMERIC(12,2) | Available cash |
| `total_value` | NUMERIC(12,2) | Portfolio + cash |
| `daily_return` | NUMERIC(8,6) | % return vs previous day |
| `cumulative_return` | NUMERIC(10,6) | % return since inception |
| `sharpe_ratio` | NUMERIC(6,4) | Rolling Sharpe ratio |
| `max_drawdown` | NUMERIC(8,6) | Peak-to-trough drawdown % |
| `created_at` | TIMESTAMP | Record creation timestamp |

**Typical Size**: ~250 rows/year (1 per trading day)

---

**6. `trading_config` - Versioned Strategy Parameters**

Stores all 27 configurable parameters with version control.

| Column | Type | Description |
|--------|------|-------------|
| `id` | SERIAL PRIMARY KEY | Config version ID |
| `daily_capital` | NUMERIC(10,2) | Daily capital grant ($1000) |
| `assets` | TEXT[] | Array of tickers |
| `lookback_days` | INTEGER | Historical window (252) |
| `regime_bullish_threshold` | NUMERIC(5,2) | Bullish regime threshold |
| `regime_bearish_threshold` | NUMERIC(5,2) | Bearish regime threshold |
| `risk_high_threshold` | NUMERIC(5,2) | High risk score threshold |
| `risk_medium_threshold` | NUMERIC(5,2) | Medium risk score threshold |
| `allocation_low_risk` | NUMERIC(5,2) | % allocation (low risk) |
| `allocation_medium_risk` | NUMERIC(5,2) | % allocation (medium risk) |
| `allocation_high_risk` | NUMERIC(5,2) | % allocation (high risk) |
| `allocation_neutral` | NUMERIC(5,2) | % allocation (neutral) |
| `sell_percentage` | NUMERIC(5,2) | % to sell (bearish) |
| `rsi_oversold_threshold` | NUMERIC(5,2) | RSI oversold level (30) |
| `rsi_overbought_threshold` | NUMERIC(5,2) | RSI overbought level (70) |
| `bollinger_std_multiplier` | NUMERIC(5,2) | Bollinger band multiplier |
| `mean_reversion_allocation` | NUMERIC(5,2) | Mean reversion % |
| `volatility_adjustment_factor` | NUMERIC(5,4) | Vol adjustment factor |
| `base_volatility` | NUMERIC(6,4) | Base volatility reference |
| `min_confidence_threshold` | NUMERIC(5,4) | Min confidence to trade |
| `confidence_scaling_factor` | NUMERIC(5,4) | Kelly-lite scaling |
| `intramonth_drawdown_limit` | NUMERIC(5,2) | Circuit breaker % |
| `circuit_breaker_reduction` | NUMERIC(5,2) | Position reduction % |
| `max_drawdown_tolerance` | NUMERIC(5,2) | Max acceptable drawdown |
| `min_sharpe_target` | NUMERIC(6,4) | Target Sharpe ratio |
| `start_date` | DATE NOT NULL | Config effective date |
| `end_date` | DATE | Config end date (NULL = active) |
| `created_by` | VARCHAR(100) | Creator (user/system) |
| `notes` | TEXT | Version notes |
| `created_at` | TIMESTAMP | Creation timestamp |

**Active Config Query**:
```sql
SELECT * FROM trading_config WHERE end_date IS NULL;
```

**Typical Size**: 1 new version per month, ~12 rows/year

---

**7. `test_*` Tables**

Mirror production tables for isolated end-to-end testing:
- `test_price_history`
- `test_daily_signals`
- `test_trades`
- `test_portfolio`
- `test_performance_metrics`
- `test_trading_config`

Allows full workflow testing without contaminating production data.

---

### Project Structure

```
capital-allocator/
├── backend/                          # Core application
│   ├── scripts/                      # Automation scripts
│   │   ├── fetch_data.py            # Alpha Vantage data fetcher
│   │   └── generate_signal.py       # Signal generation engine (779 lines)
│   ├── migrations/                   # Database schema migrations
│   ├── tests/                        # Unit & E2E tests (80%+ coverage)
│   │   ├── e2e/                     # End-to-end testing framework
│   │   │   ├── e2e_runner.py        # E2E test orchestrator
│   │   │   └── test_data_generator.py # Synthetic data generator
│   │   ├── fixtures/                # Test fixtures & mocks
│   │   └── test_*.py                # Unit test modules (12 files)
│   ├── models.py                    # SQLAlchemy database models (156 lines)
│   ├── database.py                  # Database connection & initialization
│   ├── config_loader.py             # Configuration management (322 lines)
│   ├── config.py                    # Environment settings (Pydantic)
│   ├── execute_trades.py            # Trade execution engine (388 lines)
│   ├── backtest.py                  # Backtesting framework (463 lines)
│   ├── analytics.py                 # Performance analytics (427 lines)
│   ├── strategy_tuning.py           # Monthly optimization (1059 lines)
│   ├── main.py                      # FastAPI application (218 lines)
│   ├── run_monthly_tuning.py        # Tuning CLI wrapper
│   └── requirements.txt             # Python dependencies
├── data/                            # Generated output files
│   ├── back-test/                   # Backtest results & reports
│   ├── analytics/                   # Performance analysis reports
│   ├── strategy-tuning/             # Monthly tuning reports
│   └── test-reports/                # E2E test outputs
├── docs/                            # Documentation
│   ├── ENHANCED_QUANT_STRATEGY.md   # Detailed strategy documentation
│   ├── PRODUCTION_DEPLOYMENT.md     # Deployment guide
│   ├── TESTING.md                   # Testing documentation
│   └── E2E_TESTING.md               # E2E testing guide
├── .env                             # Environment variables (gitignored)
└── README.md                        # This file
```

---

### Key Backend Modules

| File | Lines | Purpose |
|------|-------|---------|
| `scripts/generate_signal.py` | 779 | Enhanced signal generation with 12 functions (regime detection, mean reversion, confidence scoring, circuit breakers) |
| `strategy_tuning.py` | 1059 | Monthly parameter optimization with multi-horizon evaluation and out-of-sample validation |
| `backtest.py` | 463 | Historical simulation framework with benchmark comparison |
| `analytics.py` | 427 | Risk-adjusted metrics (Sharpe, Calmar, max drawdown, volatility) |
| `execute_trades.py` | 388 | Trade execution engine with portfolio management |
| `config_loader.py` | 322 | Configuration versioning and management |
| `scripts/fetch_data.py` | 241 | Alpha Vantage API integration with rate limiting |
| `main.py` | 218 | FastAPI REST API with 7 endpoints |
| `models.py` | 156 | SQLAlchemy database models for 7 tables |

---

### Testing Infrastructure

**Unit Tests**: 80%+ code coverage
- Framework: `pytest` with `pytest-cov`
- Mocking: All database and API calls mocked
- Test modules: 12 files covering all core modules
- Run: `pytest --cov=. --cov-report=term-missing`

**End-to-End Tests**: Full workflow validation
- Location: `backend/tests/e2e/`
- Generates: 1 year of synthetic price data
- Tests: Complete cycle (fetch → signal → execute → tune)
- Isolation: Uses `test_*` database tables
- Run: `python tests/e2e/e2e_runner.py`

**Test Coverage**:
- `test_generate_signal.py`: 59+ test cases
- All core modules: 80%+ line coverage
- E2E: Complete 12-month backtest with 3 retuning cycles

---

## Workflow & Automation

### Overview

Capital Allocator operates autonomously via scheduled cron jobs that:
1. Fetch market data after close
2. Generate trading signals overnight
3. Execute trades at market open
4. Self-optimize parameters monthly

All times are in **Eastern Time (ET)** to align with US market hours.

---

### Daily Workflow (Monday-Friday)

#### Job 1: Fetch Market Data (4:35 PM ET)

**Cron Expression**: `35 16 * * 1-5`

**Command**:
```bash
cd /path/to/capital-allocator/backend && python scripts/fetch_data.py
```

**Process**:
1. Connects to Alpha Vantage API (requires `ALPHAVANTAGE_API_KEY` in `.env`)
2. Fetches daily OHLCV (Open, High, Low, Close, Volume) for SPY, QQQ, DIA
3. Checks for duplicate dates (idempotent operation)
4. Inserts new records into `price_history` table
5. Respects rate limits: 15-second delay between API calls (5 calls/minute limit)

**API Calls**: 3 per day (one per asset)

**Database Impact**: Inserts 3 rows into `price_history`

**Logs**: `/var/log/capital-allocator/fetch.log` (recommended)

**Error Handling**:
- API failures logged with retry recommendation
- Duplicate dates skipped silently
- Rate limit violations handled with automatic delays

---

#### Job 2: Generate Trading Signal (6:00 AM ET)

**Cron Expression**: `0 6 * * 1-5`

**Command**:
```bash
cd /path/to/capital-allocator/backend && python scripts/generate_signal.py
```

**Process**:
1. **Load Configuration**: Retrieves active config from `trading_config` table
2. **Fetch Historical Data**: Loads 60+ days of price history for all assets
3. **Calculate Features**:
   - Returns: 5-day, 20-day, 60-day momentum
   - Volatility: 20-day rolling standard deviation
   - Moving Averages: SMA-20, SMA-50
   - RSI: 14-period Relative Strength Index
   - Bollinger Bands: 20-period with 2 std dev
4. **Detect Market Regime**: Calculates weighted regime score (-1 to +1)
5. **Identify Transitions**: Detects early momentum shifts
6. **Calculate Risk Score**: Combines volatility and correlation (0-100)
7. **Detect Mean Reversion**: Checks for oversold/overbought conditions
8. **Check Circuit Breaker**: Monitors intra-month drawdown
9. **Rank Assets**: Composite scoring of SPY, QQQ, DIA
10. **Determine Action**: BUY/SELL/HOLD based on regime and risk
11. **Calculate Allocations**: Distributes capital with confidence-based sizing
12. **Store Signal**: Inserts record into `daily_signals` with rich metadata

**Database Impact**: Inserts 1 row into `daily_signals`

**Logs**: `/var/log/capital-allocator/signal.log` (recommended)

**Output Example**:
```json
{
  "trade_date": "2025-01-15",
  "action": "BUY",
  "regime": "bullish",
  "regime_score": 0.52,
  "risk_level": "low",
  "risk_score": 35,
  "confidence_score": 0.78,
  "circuit_breaker_active": false,
  "allocations": {
    "QQQ": {"amount": 450, "score": 0.85},
    "SPY": {"amount": 350, "score": 0.72}
  }
}
```

---

#### Job 3: Execute Trades (9:30 AM ET)

**Cron Expression**: `30 9 * * 1-5`

**Command**:
```bash
cd /path/to/capital-allocator/backend && python execute_trades.py
```

**Process**:
1. **Fetch Latest Signal**: Retrieves most recent record from `daily_signals`
2. **Get Opening Prices**: Queries `price_history` for today's opening prices
3. **Execute Trades**:
   - **BUY Orders**: Calculate shares = amount / opening_price, insert into `trades`, update `portfolio` with weighted average cost
   - **SELL Orders**: Calculate shares from portfolio, insert into `trades`, update `portfolio` quantity
   - **HOLD**: No trades executed
4. **Update Performance**: Calculate portfolio value, daily return, metrics
5. **Record Linkage**: All trades linked to originating `signal_id`

**Database Impact**:
- Inserts 1-5 rows into `trades` (depending on action)
- Updates 1-3 rows in `portfolio`
- Inserts 1 row into `performance_metrics`

**Logs**: `/var/log/capital-allocator/trades.log` (recommended)

**Example Trade Execution**:
```
Signal: BUY $450 QQQ, $350 SPY
Opening Prices: QQQ = $375, SPY = $450
Trades Executed:
  - BUY 1.2 shares QQQ @ $375 = $450
  - BUY 0.78 shares SPY @ $450 = $351
Portfolio Updated:
  - QQQ: 1.2 shares @ $375 avg cost
  - SPY: 0.78 shares @ $450 avg cost
```

---

### Monthly Workflow

#### Job 4: Strategy Tuning (1st-3rd of Month, 9:30 AM ET)

**Cron Expression**: `30 9 1-3 * 1-5`

**Command**:
```bash
cd /path/to/capital-allocator && ./run_monthly_tuning.sh
```

**Purpose**: Self-optimize strategy parameters based on recent performance

**Process**:
1. **Check Timing**: Only runs on 1st trading day of month (script enforces this)
2. **Collect Trade History**: Gathers last 3 months (default) of trades from database
3. **Multi-Horizon Evaluation**:
   - For each trade, calculate P&L at 10, 20, and 30 days after execution
   - Uses best horizon for profitability assessment
4. **Performance Analysis**:
   - **By Confidence Bucket**: High (≥0.7), medium (0.5-0.7), low (<0.5)
   - **By Signal Type**: Momentum-based vs mean reversion
   - **By Market Condition**: Trending vs choppy
5. **Market Condition Detection**:
   - Analyzes recent volatility, trend strength
   - Identifies if market is momentum-friendly or range-bound
6. **Parameter Optimization**:
   - Adjusts 12+ parameters based on what worked
   - Example: If mean reversion trades outperformed, increase `mean_reversion_allocation`
   - Example: If high confidence trades were profitable, lower `min_confidence_threshold`
7. **Out-of-Sample Validation**:
   - Splits data: 2/3 training, 1/3 validation
   - Calculates validation Sharpe ratio
   - Only deploys new config if validation Sharpe ≥ `min_sharpe_target`
8. **Configuration Versioning**:
   - Creates new row in `trading_config` with `start_date` = tomorrow
   - Sets `end_date` = today on previous config version
   - Logs changes in `notes` field
9. **Generate Report**: Saves detailed tuning report to `/data/strategy-tuning/tuning_report_YYYY-MM-DD.json`

**Tuned Parameters**:
- Regime thresholds (bullish/bearish)
- Risk level thresholds (high/medium)
- Allocation percentages (low/medium/high risk, neutral)
- Mean reversion parameters (RSI thresholds, allocation %)
- Confidence thresholds and scaling factors

**Safeguards**:
- Requires 30+ trades for statistical significance
- Out-of-sample validation prevents overfitting
- Sharpe ratio gating (must meet `min_sharpe_target`)
- Manual override: `--force` flag skips validation

**Database Impact**: Inserts 1 row into `trading_config`, updates 1 row (sets `end_date`)

**Logs**: `/var/log/capital-allocator/tuning.log` (recommended)

**Report Output Example**:
```json
{
  "tuning_date": "2025-02-01",
  "lookback_months": 3,
  "total_trades": 187,
  "training_trades": 124,
  "validation_trades": 63,
  "training_sharpe": 1.32,
  "validation_sharpe": 1.18,
  "market_condition": "momentum",
  "changes": [
    {"parameter": "allocation_low_risk", "old": 0.80, "new": 0.85},
    {"parameter": "mean_reversion_allocation", "old": 0.40, "new": 0.35}
  ],
  "deployed": true
}
```

---

### Complete Cron Configuration

**File**: `/etc/cron.d/capital-allocator` or user crontab

```bash
# Capital Allocator - Production Cron Schedule
# All times in Eastern Time (ET)

# ===========================================
# DAILY JOBS (Mon-Fri Only)
# ===========================================

# 1. Fetch market data after close (4:35 PM ET)
35 16 * * 1-5 cd /path/to/capital-allocator/backend && python scripts/fetch_data.py >> /var/log/capital-allocator/fetch.log 2>&1

# 2. Generate trading signal (6:00 AM ET)
0 6 * * 1-5 cd /path/to/capital-allocator/backend && python scripts/generate_signal.py >> /var/log/capital-allocator/signal.log 2>&1

# 3. Execute trades at market open (9:30 AM ET)
30 9 * * 1-5 cd /path/to/capital-allocator/backend && python execute_trades.py >> /var/log/capital-allocator/trades.log 2>&1

# ===========================================
# MONTHLY JOBS
# ===========================================

# 4. Strategy tuning (9:30 AM ET, 1st-3rd of month)
# Script internally checks for 1st trading day
30 9 1-3 * 1-5 cd /path/to/capital-allocator && ./run_monthly_tuning.sh >> /var/log/capital-allocator/tuning.log 2>&1
```

**Note**: Adjust paths (`/path/to/capital-allocator`) and log directories as needed.

---

### Manual Execution

For testing or backfilling, all scripts support manual execution:

**Fetch Data**:
```bash
python scripts/fetch_data.py                    # Fetch today's data
python scripts/fetch_data.py --date 2025-01-15 # Fetch specific date
python scripts/fetch_data.py --backfill 30      # Backfill last 30 days
```

**Generate Signal**:
```bash
python scripts/generate_signal.py                    # Generate signal for today
python scripts/generate_signal.py --date 2025-01-15 # Generate for specific date
```

**Execute Trades**:
```bash
python execute_trades.py            # Execute today's signal
python execute_trades.py 2025-01-15 # Execute signal for specific date
```

**Monthly Tuning**:
```bash
python run_monthly_tuning.py                   # Tune with defaults (3 months lookback)
python run_monthly_tuning.py --lookback-months 6 # Tune with 6 months data
python run_monthly_tuning.py --force           # Skip validation checks
```

**Backtesting**:
```bash
python backtest.py --start-date 2024-01-01 --end-date 2024-12-31
```

**Analytics**:
```bash
python analytics.py --start-date 2024-01-01 --end-date 2024-12-31
```

---

### Monitoring & Alerting

**Log Files** (recommended locations):
- `/var/log/capital-allocator/fetch.log` - Data fetching logs
- `/var/log/capital-allocator/signal.log` - Signal generation logs
- `/var/log/capital-allocator/trades.log` - Trade execution logs
- `/var/log/capital-allocator/tuning.log` - Monthly tuning logs

**Log Rotation** (logrotate configuration):
```
/var/log/capital-allocator/*.log {
    daily
    rotate 90
    compress
    delaycompress
    missingok
    notifempty
}
```

**Health Checks**:
- Monitor log files for ERROR/WARNING entries
- Check `daily_signals` table for daily inserts
- Check `trades` table for expected trade activity
- Monitor `performance_metrics` for unusual drawdowns

**Circuit Breaker Alerts**:
When circuit breaker triggers (10% monthly drawdown), log entry includes:
```
WARNING: Circuit breaker triggered! Intra-month drawdown: 10.5%
Position sizes reduced by 50% for remaining month.
```

Consider setting up email/SMS alerts for this condition.

---

## UI & Monitoring

### FastAPI REST API

The system exposes a REST API for monitoring and integration with frontend dashboards.

**Server**: `/home/user/capital-allocator/backend/main.py` (218 lines)

**Start Server**:
```bash
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000
```

**API Documentation**: `http://localhost:8000/docs` (Swagger UI)

---

### Available Endpoints

#### 1. Health Check
```
GET /
```
**Response**: `{"message": "Capital Allocator API", "status": "running"}`

---

#### 2. Latest Market Prices
```
GET /api/prices/latest
```
**Purpose**: Get most recent closing prices for all assets

**Response**:
```json
{
  "date": "2025-01-14",
  "prices": {
    "SPY": 450.25,
    "QQQ": 375.80,
    "DIA": 340.10
  }
}
```

---

#### 3. Historical Prices
```
GET /api/prices/history/{symbol}?days=30
```
**Parameters**:
- `symbol`: SPY, QQQ, or DIA
- `days`: Number of days to retrieve (default: 30)

**Purpose**: Get historical price data for charting

**Response**:
```json
{
  "symbol": "SPY",
  "data": [
    {"date": "2025-01-14", "close": 450.25, "volume": 75000000},
    {"date": "2025-01-13", "close": 448.50, "volume": 72000000},
    ...
  ]
}
```

---

#### 4. Latest Trading Signal
```
GET /api/signals/latest
```
**Purpose**: Get most recent allocation decision

**Response**:
```json
{
  "trade_date": "2025-01-15",
  "generated_at": "2025-01-15T06:00:12",
  "action": "BUY",
  "confidence_score": 0.78,
  "allocations": {
    "QQQ": {"amount": 450, "score": 0.85},
    "SPY": {"amount": 350, "score": 0.72}
  },
  "features": {
    "regime": "bullish",
    "regime_score": 0.52,
    "risk_level": "low",
    "risk_score": 35,
    "circuit_breaker_active": false
  }
}
```

---

#### 5. Current Portfolio
```
GET /api/portfolio
```
**Purpose**: View current holdings with unrealized P&L

**Response**:
```json
{
  "positions": [
    {
      "symbol": "QQQ",
      "quantity": 2.5,
      "avg_cost": 370.00,
      "current_price": 375.80,
      "market_value": 939.50,
      "unrealized_pnl": 14.50,
      "unrealized_pnl_pct": 1.57
    },
    {
      "symbol": "SPY",
      "quantity": 1.8,
      "avg_cost": 445.00,
      "current_price": 450.25,
      "market_value": 810.45,
      "unrealized_pnl": 9.45,
      "unrealized_pnl_pct": 1.18
    }
  ],
  "total_value": 1749.95,
  "total_pnl": 23.95
}
```

---

#### 6. Trade History
```
GET /api/trades/history?days=30
```
**Parameters**:
- `days`: Lookback period (default: 30)

**Purpose**: View past trade execution history

**Response**:
```json
{
  "trades": [
    {
      "trade_date": "2025-01-15",
      "symbol": "QQQ",
      "action": "BUY",
      "quantity": 1.2,
      "price": 375.00,
      "amount": 450.00,
      "executed_at": "2025-01-15T09:30:05"
    },
    {
      "trade_date": "2025-01-14",
      "symbol": "SPY",
      "action": "SELL",
      "quantity": 0.5,
      "price": 448.00,
      "amount": 224.00,
      "executed_at": "2025-01-14T09:30:03"
    },
    ...
  ]
}
```

---

#### 7. Performance Metrics
```
GET /api/performance?days=90
```
**Parameters**:
- `days`: Lookback period for metrics (default: 90)

**Purpose**: Get risk-adjusted performance statistics

**Response**:
```json
{
  "period": {
    "start_date": "2024-10-15",
    "end_date": "2025-01-14",
    "trading_days": 63
  },
  "returns": {
    "total_return": 12.5,
    "annualized_return": 52.3,
    "daily_avg_return": 0.19
  },
  "risk": {
    "volatility": 18.2,
    "sharpe_ratio": 1.42,
    "max_drawdown": -8.3,
    "calmar_ratio": 6.30
  },
  "benchmark_comparison": {
    "SPY": {"return": 10.2, "sharpe": 1.15},
    "QQQ": {"return": 14.1, "sharpe": 1.28},
    "DIA": {"return": 8.5, "sharpe": 1.05}
  },
  "current_metrics": {
    "portfolio_value": 1749.95,
    "cash_balance": 250.05,
    "total_value": 2000.00
  }
}
```

---

### UI Dashboard (In Progress)

**Status**: Frontend development planned

**Planned Features**:

1. **Performance Dashboard**:
   - Cumulative return chart vs benchmarks (SPY, QQQ, DIA)
   - Sharpe ratio, max drawdown, Calmar ratio cards
   - Monthly performance heatmap
   - Rolling volatility chart

2. **Trade History View**:
   - Sortable/filterable table of all trades
   - Win rate by asset, by month
   - Average holding period
   - P&L distribution histogram

3. **Current Holdings**:
   - Real-time portfolio composition (pie chart)
   - Unrealized P&L for each position
   - Cost basis vs current price
   - Allocation vs target allocation

4. **Signal Preview**:
   - Next trading day's action and allocations
   - Confidence score indicator
   - Regime and risk level visualization
   - Circuit breaker status indicator

5. **Strategy Insights**:
   - Parameter version timeline
   - Tuning history and impact on performance
   - Confidence bucket win rates
   - Mean reversion vs momentum effectiveness

6. **Risk Monitoring**:
   - Current drawdown from peak
   - Circuit breaker proximity gauge
   - Volatility regime indicator
   - Correlation matrix heatmap

**Technology Stack** (Proposed):
- Frontend: React or Vue.js
- Charting: Chart.js or Plotly
- API Integration: Axios or Fetch API
- Hosting: Same server as FastAPI backend

**Access URL** (When Available): `http://localhost:8000/dashboard`

---

### Current Monitoring Options

Until UI is complete, use these methods for monitoring:

**1. API Queries** (curl):
```bash
# Check latest signal
curl http://localhost:8000/api/signals/latest | jq

# Check portfolio
curl http://localhost:8000/api/portfolio | jq

# Check performance
curl http://localhost:8000/api/performance?days=30 | jq
```

**2. Database Queries**:
```sql
-- Latest signal
SELECT * FROM daily_signals ORDER BY trade_date DESC LIMIT 1;

-- Current portfolio
SELECT * FROM portfolio;

-- Recent trades
SELECT * FROM trades WHERE trade_date >= CURRENT_DATE - INTERVAL '7 days' ORDER BY trade_date DESC;

-- Performance summary
SELECT
  date,
  total_value,
  daily_return,
  cumulative_return,
  sharpe_ratio,
  max_drawdown
FROM performance_metrics
WHERE date >= CURRENT_DATE - INTERVAL '30 days'
ORDER BY date DESC;
```

**3. Analytics Reports**:
```bash
# Generate comprehensive performance report
python analytics.py --start-date 2024-01-01 --end-date 2024-12-31

# Output: /data/analytics/analytics_report_YYYY-MM-DD.json
```

**4. Backtest Comparison**:
```bash
# Run backtest for specific period
python backtest.py --start-date 2024-01-01 --end-date 2024-12-31

# Output: /data/back-test/backtest_YYYY-MM-DD_to_YYYY-MM-DD.json
```

---

## Quick Start

### For Developers

**1. Clone & Setup**:
```bash
git clone https://github.com/your-org/capital-allocator.git
cd capital-allocator/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**2. Configure**:
```bash
cp .env.example .env
# Edit .env with your DATABASE_URL and ALPHAVANTAGE_API_KEY
```

**3. Initialize Database**:
```bash
createdb capital_allocator
python -c "from database import init_db; init_db()"
```

**4. Backfill Historical Data**:
```bash
python scripts/fetch_data.py --backfill 60
# Fetches last 60 days of SPY, QQQ, DIA prices
```

**5. Run Backtest**:
```bash
python backtest.py --start-date 2024-01-01 --end-date 2024-12-31
# Simulates trading for 2024, generates report
```

**6. View Results**:
```bash
cat data/back-test/backtest_2024-01-01_to_2024-12-31.json
```

---

### For Production Deployment

**1. Complete Setup** (steps 1-4 above)

**2. Configure Cron Jobs**:
```bash
crontab -e
# Add cron entries from docs/PRODUCTION_DEPLOYMENT.md
```

**3. Setup Log Rotation**:
```bash
sudo cp config/logrotate.conf /etc/logrotate.d/capital-allocator
```

**4. Start API Server** (Optional):
```bash
cd backend
nohup uvicorn main:app --host 0.0.0.0 --port 8000 &
```

**5. Monitor Logs**:
```bash
tail -f /var/log/capital-allocator/*.log
```

---

### For Researchers

**Run Tests**:
```bash
cd backend
pytest --cov=. --cov-report=html
# Open htmlcov/index.html to view coverage
```

**End-to-End Test**:
```bash
python tests/e2e/e2e_runner.py
# Runs full 12-month simulation with monthly tuning
```

**Custom Backtest**:
```bash
python backtest.py --start-date 2023-01-01 --end-date 2024-12-31
```

**Parameter Experimentation**:
```sql
-- Manually create test config
INSERT INTO trading_config (...) VALUES (...);
-- Run backtest with new config active
```

---

## Additional Documentation

- **[ENHANCED_QUANT_STRATEGY.md](./docs/ENHANCED_QUANT_STRATEGY.md)**: Detailed strategy documentation with technical implementation details
- **[PRODUCTION_DEPLOYMENT.md](./docs/PRODUCTION_DEPLOYMENT.md)**: Complete deployment guide with cron configuration and monitoring setup
- **[TESTING.md](./docs/TESTING.md)**: Testing strategy, unit test structure, and mocking patterns
- **[E2E_TESTING.md](./docs/E2E_TESTING.md)**: End-to-end testing framework documentation

---

## Performance Characteristics

**Historical Backtest Results** (2024):
- **Total Return**: ~12-18% (varies by market conditions)
- **Sharpe Ratio**: 1.2-1.5 (target: ≥1.0)
- **Max Drawdown**: 8-12% (limit: 15%)
- **Win Rate**: 55-65% (depends on regime)
- **Avg Trade Duration**: 2-5 days

**Key Performance Drivers**:
- Regime detection accuracy
- Mean reversion capture in neutral markets
- Circuit breaker effectiveness during drawdowns
- Monthly tuning responsiveness

**Risk Management**:
- Daily capital limit: $1,000
- Position sizing: 20-80% of capital depending on risk
- Circuit breaker: Halves positions at 10% monthly loss
- Diversification: Up to 3 assets (SPY, QQQ, DIA)

---

## System Requirements

**Minimum**:
- Python 3.8+
- PostgreSQL 12+
- 1 GB RAM
- 5 GB disk space (database + logs)

**Recommended**:
- Python 3.10+
- PostgreSQL 14+
- 2 GB RAM
- 20 GB disk space (multi-year data + reports)

**Dependencies** (see `requirements.txt`):
- SQLAlchemy, psycopg2-binary (database)
- FastAPI, uvicorn (API server)
- pandas, numpy (data processing)
- alpha-vantage (market data)
- pytest, pytest-cov (testing)
- pydantic, python-dotenv (configuration)

---

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure tests pass: `pytest --cov=. --cov-report=term-missing`
5. Submit a pull request

**Code Style**: Follow PEP 8 conventions

---

## License

[Specify License - e.g., MIT, Apache 2.0, Proprietary]

---

## Contact & Support

- **Issues**: [GitHub Issues](https://github.com/your-org/capital-allocator/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/capital-allocator/discussions)
- **Email**: your-email@example.com

---

## Acknowledgments

- **Alpha Vantage**: Market data provider
- **PostgreSQL**: Database backend
- **FastAPI**: Modern Python web framework
- **Contributors**: [List key contributors]

---

**Last Updated**: January 2025
**Version**: 2.0 (Enhanced Multi-Factor Strategy)
