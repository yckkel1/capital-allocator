# Testing Guide for Capital Allocator

This document describes how to run unit tests and check code coverage for the Capital Allocator backend.

## Prerequisites

Ensure you have all dependencies installed:

```bash
cd backend
pip install -r requirements.txt
```

This will install pytest, pytest-cov, and coverage along with other testing dependencies.

## Running Tests

### Run All Tests

From the `backend` directory:

```bash
pytest
```

Or with verbose output:

```bash
pytest -v
```

### Run Specific Test File

```bash
pytest tests/test_config.py
pytest tests/test_analytics.py -v
```

### Run Specific Test Class or Function

```bash
# Run specific test class
pytest tests/test_models.py::TestPriceHistory

# Run specific test function
pytest tests/test_analytics.py::TestCalculateSharpeRatio::test_sharpe_ratio_calculation
```

### Run Tests with Coverage

To run tests with coverage reporting:

```bash
pytest --cov=. --cov-report=term-missing
```

This will show:
- Which lines of code were executed during tests
- Which lines were missed
- Overall coverage percentage

### Generate HTML Coverage Report

```bash
pytest --cov=. --cov-report=html
```

This generates a detailed HTML report in `htmlcov/` directory. Open `htmlcov/index.html` in a browser to view.

### Generate XML Coverage Report (for CI/CD)

```bash
pytest --cov=. --cov-report=xml
```

This creates `coverage.xml` suitable for CI/CD tools.

### Combined Coverage Report

```bash
pytest --cov=. --cov-report=term-missing --cov-report=html --cov-report=xml
```

## Coverage Requirements

The project requires **minimum 80% code coverage**. This is enforced in `pyproject.toml`:

```toml
[tool.coverage.report]
fail_under = 80
```

If coverage falls below 80%, the test run will fail with an error.

## Test Structure

```
backend/
├── tests/
│   ├── __init__.py              # Test package marker
│   ├── conftest.py              # Shared fixtures and test utilities
│   ├── test_data/               # Mock data for tests
│   │   ├── sample_prices.json   # Sample market price data
│   │   ├── sample_signals.json  # Sample trading signals
│   │   └── sample_config.json   # Sample configuration
│   ├── test_config.py           # Tests for config.py
│   ├── test_database.py         # Tests for database.py
│   ├── test_models.py           # Tests for SQLAlchemy models
│   ├── test_config_loader.py    # Tests for config_loader.py
│   ├── test_analytics.py        # Tests for analytics.py
│   ├── test_backtest.py         # Tests for backtest.py
│   ├── test_execute_trades.py   # Tests for execute_trades.py
│   ├── test_strategy_tuning.py  # Tests for strategy_tuning.py
│   ├── test_main.py             # Tests for FastAPI endpoints
│   ├── test_generate_signal.py  # Tests for signal generation
│   └── test_fetch_data.py       # Tests for data fetching
└── pyproject.toml               # Test and coverage configuration
```

## Test Categories

### Unit Tests
All tests are unit tests that mock external dependencies (database, APIs, etc.). No real database connection or API calls are made during testing.

### Mocking Strategy
- **Database connections**: Mocked using `unittest.mock`
- **SQLAlchemy sessions**: Mocked to avoid real database operations
- **External APIs**: Alpha Vantage API calls are mocked
- **File system**: File operations are mocked where needed

## Key Test Fixtures

Available in `conftest.py`:

- `mock_settings` - Mock application settings
- `mock_trading_config` - Mock trading configuration
- `mock_db_session` - Mock SQLAlchemy session
- `mock_psycopg2_connection` - Mock psycopg2 connection
- `sample_price_data` - Sample historical price data
- `sample_signal_data` - Sample trading signal
- `sample_trade_data` - Sample trade records
- `sample_portfolio_data` - Sample portfolio holdings
- `sample_performance_data` - Sample performance metrics

## Example Usage

### Using Fixtures in Tests

```python
def test_get_portfolio_with_holdings(self, mock_db_session):
    """Test getting portfolio with holdings"""
    from main import get_portfolio

    mock_holding = Mock()
    mock_holding.symbol = 'SPY'
    mock_holding.quantity = 1.5
    mock_holding.avg_cost = 575.0

    mock_db_session.query.return_value.all.return_value = [mock_holding]

    response = get_portfolio(mock_db_session)
    assert len(response['positions']) == 1
```

### Mocking Database Operations

```python
@patch('analytics.psycopg2.connect')
@patch('analytics.get_settings')
def test_analytics_init(self, mock_get_settings, mock_connect):
    mock_settings = Mock()
    mock_settings.database_url = "postgresql://test:test@localhost:5432/testdb"
    mock_get_settings.return_value = mock_settings

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_connect.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor

    from analytics import Analytics
    analytics = Analytics(date(2025, 11, 1), date(2025, 11, 15))

    assert analytics.start_date == date(2025, 11, 1)
```

## Common Test Commands

```bash
# Quick test run
pytest -x                          # Stop on first failure

# Run with markers
pytest -m unit                     # Run only unit tests
pytest -m "not slow"               # Skip slow tests

# Run with output
pytest -s                          # Show print statements
pytest --tb=long                   # Long traceback on failure

# Coverage shortcuts
pytest --cov=. --cov-fail-under=80  # Fail if under 80%

# Parallel execution (if pytest-xdist is installed)
pytest -n auto                     # Use all CPU cores
```

## Continuous Integration

For CI/CD pipelines, use:

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests with coverage
cd backend
pytest --cov=. --cov-report=xml --cov-report=term-missing

# Check coverage threshold
python -m coverage report --fail-under=80
```

## Troubleshooting

### Import Errors

If you see import errors, ensure you're running from the `backend` directory:

```bash
cd /path/to/capital-allocator/backend
pytest
```

### Coverage Not Found

Ensure coverage is installed:

```bash
pip install pytest-cov coverage
```

### Test Discovery Issues

Pytest discovers tests by:
- Files matching `test_*.py`
- Classes matching `Test*`
- Functions matching `test_*`

Ensure your tests follow these naming conventions.

### Mock Not Working

If mocks aren't working as expected:
1. Check the import path is correct
2. Ensure you're patching where the object is used, not where it's defined
3. Verify the mock is applied before the import happens

## Best Practices

1. **Keep tests isolated** - Each test should be independent
2. **Mock external dependencies** - No real database or API calls
3. **Test edge cases** - Include error scenarios
4. **Use descriptive names** - Test names should explain what's being tested
5. **Keep tests fast** - Unit tests should run in milliseconds
6. **Maintain coverage** - Keep coverage above 80%

## Adding New Tests

When adding new functionality:

1. Create test file in `tests/` directory
2. Follow naming convention `test_<module>.py`
3. Add necessary fixtures to `conftest.py`
4. Mock all external dependencies
5. Test both success and error cases
6. Run coverage to ensure new code is tested

```bash
# Example workflow
# 1. Write new feature
# 2. Write tests
# 3. Run tests with coverage
pytest tests/test_new_module.py --cov=new_module --cov-report=term-missing
# 4. Ensure coverage is adequate
# 5. Run full test suite
pytest --cov=. --cov-report=term-missing
```

## Support

For questions about testing:
- Check existing tests for examples
- Review `conftest.py` for available fixtures
- See `pyproject.toml` for configuration options
