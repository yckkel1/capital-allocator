# End-to-End Testing Guide

This document describes the end-to-end (E2E) testing infrastructure for Capital Allocator. E2E tests use isolated test database tables to run complete workflows without affecting production data.

## Overview

The E2E testing framework provides:
- **Isolated test tables** - Mirror production tables with `test_` prefix
- **Synthetic test data** - 1 year of realistic price history (2024-11-11 to 2025-11-10)
- **Complete workflow testing** - Backtest, analytics, and strategy tuning
- **Separate test reports** - Output files in `data/test-reports/`

## Test Table Structure

E2E tests use dedicated test tables that mirror production schemas:

| Production Table | Test Table | Purpose |
|-----------------|------------|---------|
| `price_history` | `test_price_history` | Historical price data |
| `daily_signals` | `test_daily_signals` | Trading signals |
| `trades` | `test_trades` | Executed trades |
| `portfolio` | `test_portfolio` | Current holdings |
| `performance_metrics` | `test_performance_metrics` | Daily performance |
| `trading_config` | `test_trading_config` | Strategy parameters |

## Setup

### 1. Run Database Migration

First, create the test tables by running the migration:

```bash
cd backend
python migrations/003_add_test_tables.py
```

To rollback:
```bash
python migrations/003_add_test_tables.py rollback
```

### 2. Generate Test Price Data

The test framework includes synthetic price data. To regenerate:

```bash
cd backend
python tests/fixtures/generate_test_price_data.py
```

This creates `tests/fixtures/price_history_test_data.json` with:
- 1 year of trading data (2024-11-11 to 2025-11-10)
- 3 symbols: SPY, QQQ, DIA
- ~783 records (261 trading days × 3 symbols)
- Realistic price movements with correlations

### 3. Export Real Price Data (Optional)

To use your actual price history data for E2E tests:

```bash
cd backend
python scripts/export_price_history.py
```

This exports all `price_history` data to `tests/fixtures/price_history_test_data.json`.

## Running E2E Tests

### Quick Start: Run Complete E2E Test Suite

```bash
cd backend
python tests/e2e/e2e_runner.py
```

This executes:
1. Clear all test tables and old reports
2. Load price history from fixtures (2024-11-11 to 2025-11-10)
3. **Train initial parameters** using 8 months of historical data (2024-11-11 to 2025-06-30)
4. **Run Month 1 (July 2025)** - Backtest + Analytics
5. **Tune parameters** for Month 2 using all data through July 2025
6. **Run Month 2 (August 2025)** - Backtest + Analytics
7. **Tune parameters** for Month 3 using all data through August 2025
8. **Run Month 3 (September 2025)** - Backtest + Analytics
9. Generate comprehensive summary report

Output reports are saved to:
- `data/test-reports/backtest/` - Monthly backtest reports
- `data/test-reports/analytics/` - Performance metrics (Sharpe, drawdown, volatility)
- `data/test-reports/tuning/` - Parameter optimization reports
- `data/test-reports/summary/` - Overall test summary

### Key Features

**Initial Parameter Training:**
- Uses 8 months of historical data (166+ trading days) for robust parameter estimation
- Analyzes volatility patterns, momentum trends, and RSI/Bollinger Band patterns
- Automatically tunes regime thresholds, risk allocations, and confidence settings

**Monthly Parameter Retuning:**
- On the first day of each test month, parameters are retuned using all accumulated historical data
- Adapts to evolving market conditions
- Reports saved for each tuning session

**Actual Trading Strategy Logic:**
- Uses regime detection (bullish/neutral/bearish) based on multi-timeframe momentum
- RSI and Bollinger Band analysis for mean reversion signals
- Risk-adjusted position sizing with confidence scaling
- Diversified asset allocation based on composite scores

### Running Pytest E2E Tests

```bash
# Run all E2E tests
pytest tests/e2e/ -v

# Run specific E2E test file
pytest tests/e2e/test_e2e_backtest.py -v

# Run with e2e marker
pytest -m e2e -v

# Run with coverage
pytest tests/e2e/ --cov=tests/e2e --cov-report=term-missing
```

### Running Individual Components

```python
from datetime import date
from tests.e2e.test_database import E2ETestDatabaseManager
from tests.e2e.e2e_backtest import E2EBacktest
from tests.e2e.e2e_analytics import E2EAnalytics

# Setup test database
with E2ETestDatabaseManager() as db:
    db.clear_all_test_tables()
    db.load_price_history_from_file()
    db.reset_test_trading_config()

# Run backtest
backtest = E2EBacktest(date(2024, 12, 1), date(2024, 12, 31))
result = backtest.run()
print(f"Report: {result['report_file']}")
backtest.close()

# Run analytics
analytics = E2EAnalytics(date(2024, 12, 1), date(2024, 12, 31))
metrics = analytics.run()
print(f"Sharpe Ratio: {metrics['sharpe_ratio']:.3f}")
analytics.close()
```

## E2E Test Workflow

### Standard E2E Test Procedure

1. **Clear Test Environment**
   ```python
   with E2ETestDatabaseManager() as db:
       db.clear_all_test_tables()
   ```

2. **Load Test Data**
   ```python
   with E2ETestDatabaseManager() as db:
       db.load_price_history_from_file()
       db.reset_test_trading_config()
   ```

3. **Run Backtest**
   - Generates signals using `test_price_history`
   - Executes trades into `test_trades`
   - Updates `test_portfolio`
   - Calculates metrics into `test_performance_metrics`

4. **Run Analytics**
   - Reads from `test_performance_metrics`
   - Calculates Sharpe ratio, max drawdown, volatility
   - Generates report files

5. **Verify Results**
   - Check performance metrics
   - Validate report files generated
   - Compare against expected benchmarks

## File Structure

```
backend/
├── tests/
│   ├── e2e/
│   │   ├── __init__.py              # E2E package marker
│   │   ├── test_database.py         # Test database management
│   │   ├── e2e_backtest.py          # Backtest using test tables (actual strategy logic)
│   │   ├── e2e_analytics.py         # Analytics using test tables
│   │   ├── e2e_strategy_tuner.py    # Parameter training and tuning
│   │   ├── e2e_runner.py            # Complete E2E test runner
│   │   └── test_e2e_backtest.py     # Pytest E2E tests
│   └── fixtures/
│       ├── generate_test_price_data.py  # Generate synthetic data
│       └── price_history_test_data.json # Test price data
├── migrations/
│   └── 003_add_test_tables.py       # Migration for test tables
├── scripts/
│   └── export_price_history.py      # Export real data for testing
└── data/
    └── test-reports/                # E2E test output directory
        ├── backtest/                # Backtest reports
        ├── analytics/               # Analytics reports
        ├── tuning/                  # Strategy tuning reports
        └── summary/                 # Overall test summaries
```

## Test Data Management

### E2ETestDatabaseManager Methods

| Method | Description |
|--------|-------------|
| `clear_all_test_tables()` | Delete all data from test tables |
| `clear_test_trading_data()` | Clear only signals/trades/portfolio/metrics (keep prices) |
| `load_price_history_from_file()` | Load price data from JSON fixture |
| `reset_test_trading_config()` | Reset to default trading configuration |
| `get_test_price_history_range()` | Get min/max dates and record count |
| `get_test_trading_days()` | Get trading days in date range |
| `verify_test_tables_exist()` | Check all test tables are present |

### Test Report Cleanup

Reports are automatically cleared when running `e2e_runner.py`. To manually clear:

```python
from tests.e2e.e2e_runner import clear_test_reports
clear_test_reports()
```

## Writing New E2E Tests

### Example: Testing a New Strategy

```python
import pytest
from datetime import date
from tests.e2e.test_database import E2ETestDatabaseManager
from tests.e2e.e2e_backtest import E2EBacktest

class TestNewStrategy:

    @pytest.fixture
    def setup_test_db(self):
        """Setup test database with data"""
        with E2ETestDatabaseManager() as db:
            db.clear_all_test_tables()
            db.load_price_history_from_file()
            db.reset_test_trading_config()
        yield

    def test_strategy_generates_positive_return(self, setup_test_db):
        """Test that strategy generates positive returns"""
        backtest = E2EBacktest(date(2024, 12, 1), date(2024, 12, 31))
        try:
            result = backtest.run()
            assert result['trading_days'] > 0
            # Add assertions for your strategy
        finally:
            backtest.close()
```

## Coverage Requirements

The E2E test framework maintains 80%+ code coverage:

- E2E test modules are excluded from coverage calculations
- Production code tested through E2E workflows
- Unit tests complement E2E tests for edge cases

Run coverage report:
```bash
pytest --cov=. --cov-report=term-missing --cov-report=html
```

## Troubleshooting

### Test Tables Don't Exist

```bash
# Run migration
python migrations/003_add_test_tables.py
```

### No Price Data Found

```bash
# Regenerate test data
python tests/fixtures/generate_test_price_data.py
```

### Database Connection Failed

Check your `.env` file (in repository root) has correct `DATABASE_URL`:
```
DATABASE_URL=postgresql://user:password@localhost/allocator_db
```

### Old Reports Not Cleared

```python
from tests.e2e.e2e_runner import clear_test_reports
clear_test_reports()
```

## Best Practices

1. **Isolate Tests** - Always use test tables, never production
2. **Clean State** - Clear tables before each test run
3. **Deterministic Data** - Use consistent test fixtures
4. **Report Separation** - Keep test reports in `data/test-reports/`
5. **Verify Setup** - Check test tables exist before running
6. **Close Connections** - Always close database connections

## Integration with CI/CD

E2E tests can be integrated into CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
e2e_tests:
  runs-on: ubuntu-latest
  services:
    postgres:
      image: postgres:14
      env:
        POSTGRES_DB: allocator_db
        POSTGRES_USER: test
        POSTGRES_PASSWORD: test
  steps:
    - uses: actions/checkout@v3
    - name: Setup Python
      uses: actions/setup-python@v4
    - name: Install dependencies
      run: pip install -r requirements.txt
    - name: Run migrations
      run: python migrations/003_add_test_tables.py
    - name: Run E2E tests
      run: pytest tests/e2e/ -v
```

## Future Enhancements

- [x] ~~Add strategy tuning E2E tests~~ (Implemented with E2EStrategyTuner)
- [x] ~~Add initial parameter training~~ (Uses 8 months of historical data)
- [x] ~~Monthly parameter retuning~~ (Retunes on first day of each test month)
- [ ] Support multiple test data scenarios
- [ ] Add performance benchmarking against market indices
- [ ] Integrate with real-time data simulation
- [ ] Add regression test automation
- [ ] Walk-forward optimization testing
