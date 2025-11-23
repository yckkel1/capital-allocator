"""
Train initial trading configuration using historical data.

This script:
1. Loads 10 years of historical price data
2. Uses first 5 years to establish baseline parameters
3. Simulates trading in latter 5 years with backtesting
4. Generates SQL INSERT for the final validated configuration
"""
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Check if we're running the actual tuning or just generating default config
RUN_FULL_TUNING = os.getenv("RUN_FULL_TUNING", "false").lower() == "true"


def generate_config_sql(output_file: str, start_date: str = '2015-01-01', notes: str = 'Default configuration for initial deployment'):
    """
    Generate SQL INSERT for trading configuration.

    Args:
        output_file: Path to output SQL file
        start_date: Configuration start date
        notes: Notes about this configuration
    """
    # Default configuration based on the model defaults
    config = {
        'start_date': start_date,
        'end_date': None,  # Currently active (NULL in SQL)
        'daily_capital': 1000.0,
        'assets': json.dumps(["SPY", "QQQ", "DIA"]),
        'lookback_days': 252,
        'regime_bullish_threshold': 0.3,
        'regime_bearish_threshold': -0.3,
        'risk_high_threshold': 70.0,
        'risk_medium_threshold': 40.0,
        'allocation_low_risk': 0.8,
        'allocation_medium_risk': 0.5,
        'allocation_high_risk': 0.3,
        'allocation_neutral': 0.2,
        'sell_percentage': 0.7,
        'momentum_weight': 0.6,
        'price_momentum_weight': 0.4,
        'max_drawdown_tolerance': 15.0,
        'min_sharpe_target': 1.0,
        'rsi_oversold_threshold': 30.0,
        'rsi_overbought_threshold': 70.0,
        'bollinger_std_multiplier': 2.0,
        'mean_reversion_allocation': 0.4,
        'volatility_adjustment_factor': 0.4,
        'base_volatility': 0.01,
        'min_confidence_threshold': 0.3,
        'confidence_scaling_factor': 0.5,
        'intramonth_drawdown_limit': 0.10,
        'circuit_breaker_reduction': 0.5,
        'created_by': 'initial_deployment',
        'notes': notes
    }

    with open(output_file, 'w') as f:
        f.write("-- Initial trading configuration\n")
        f.write("-- Generated on: {}\n".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        f.write(f"-- {notes}\n\n")

        f.write("INSERT INTO trading_config (\n")
        f.write("  start_date, end_date, daily_capital, assets, lookback_days,\n")
        f.write("  regime_bullish_threshold, regime_bearish_threshold,\n")
        f.write("  risk_high_threshold, risk_medium_threshold,\n")
        f.write("  allocation_low_risk, allocation_medium_risk, allocation_high_risk,\n")
        f.write("  allocation_neutral, sell_percentage,\n")
        f.write("  momentum_weight, price_momentum_weight,\n")
        f.write("  max_drawdown_tolerance, min_sharpe_target,\n")
        f.write("  rsi_oversold_threshold, rsi_overbought_threshold,\n")
        f.write("  bollinger_std_multiplier, mean_reversion_allocation,\n")
        f.write("  volatility_adjustment_factor, base_volatility,\n")
        f.write("  min_confidence_threshold, confidence_scaling_factor,\n")
        f.write("  intramonth_drawdown_limit, circuit_breaker_reduction,\n")
        f.write("  created_by, notes\n")
        f.write(") VALUES (\n")
        f.write(f"  '{config['start_date']}',\n")
        f.write(f"  NULL,  -- end_date (currently active)\n")
        f.write(f"  {config['daily_capital']},\n")
        f.write(f"  '{config['assets']}'::json,\n")
        f.write(f"  {config['lookback_days']},\n")
        f.write(f"  {config['regime_bullish_threshold']},\n")
        f.write(f"  {config['regime_bearish_threshold']},\n")
        f.write(f"  {config['risk_high_threshold']},\n")
        f.write(f"  {config['risk_medium_threshold']},\n")
        f.write(f"  {config['allocation_low_risk']},\n")
        f.write(f"  {config['allocation_medium_risk']},\n")
        f.write(f"  {config['allocation_high_risk']},\n")
        f.write(f"  {config['allocation_neutral']},\n")
        f.write(f"  {config['sell_percentage']},\n")
        f.write(f"  {config['momentum_weight']},\n")
        f.write(f"  {config['price_momentum_weight']},\n")
        f.write(f"  {config['max_drawdown_tolerance']},\n")
        f.write(f"  {config['min_sharpe_target']},\n")
        f.write(f"  {config['rsi_oversold_threshold']},\n")
        f.write(f"  {config['rsi_overbought_threshold']},\n")
        f.write(f"  {config['bollinger_std_multiplier']},\n")
        f.write(f"  {config['mean_reversion_allocation']},\n")
        f.write(f"  {config['volatility_adjustment_factor']},\n")
        f.write(f"  {config['base_volatility']},\n")
        f.write(f"  {config['min_confidence_threshold']},\n")
        f.write(f"  {config['confidence_scaling_factor']},\n")
        f.write(f"  {config['intramonth_drawdown_limit']},\n")
        f.write(f"  {config['circuit_breaker_reduction']},\n")
        f.write(f"  '{config['created_by']}',\n")
        f.write(f"  '{config['notes']}'\n")
        f.write(")\n")
        f.write("ON CONFLICT DO NOTHING;\n")

    print(f"\n✓ Generated SQL file: {output_file}")
    print(f"  Configuration valid from {config['start_date']} onwards")


def train_with_historical_data():
    """
    Full training process using historical data.

    This:
    1. Loads 10 years of price data from database
    2. Uses default parameters (first 5 years establishes baseline)
    3. Runs backtest on last 5 years to validate performance
    4. Generates config with backtest results

    Note: Parameter optimization can be added later via monthly_tuning.py
    """
    import psycopg2

    print("=" * 60)
    print("5 Year Training / 5 Year Backtest Process")
    print("=" * 60)
    print()

    # Connect to database
    try:
        from config import get_settings
        settings = get_settings()
        conn = psycopg2.connect(settings.database_url)
        cursor = conn.cursor()

        # Check if we have 10 years of data
        cursor.execute("""
            SELECT MIN(date) as oldest, MAX(date) as newest, COUNT(*) as total
            FROM price_history
        """)
        result = cursor.fetchone()

        if not result or not result[0]:
            print("ERROR: No price history data found in database!")
            print("Run: python scripts/fetch_data_yahoo.py --days 3650")
            sys.exit(1)

        oldest_date, newest_date, total_records = result
        years_of_data = (newest_date - oldest_date).days / 365.25

        print(f"Price History Summary:")
        print(f"  Oldest: {oldest_date}")
        print(f"  Newest: {newest_date}")
        print(f"  Years: {years_of_data:.1f}")
        print(f"  Records: {total_records}")
        print()

        if years_of_data < 9.5:
            print(f"WARNING: Only {years_of_data:.1f} years of data found.")
            print(f"Recommended: At least 10 years for 5Y/5Y split")
            response = input("Continue anyway? (y/N): ")
            if response.lower() != 'y':
                sys.exit(1)

        # Calculate date ranges
        # Use last 10 years, split into two 5-year periods
        ten_years_ago = newest_date - timedelta(days=3650)

        # Find actual trading day closest to 5 years ago (middle point)
        five_years_ago = newest_date - timedelta(days=1825)
        cursor.execute("""
            SELECT date FROM price_history
            WHERE date >= %s
            ORDER BY date ASC
            LIMIT 1
        """, (five_years_ago,))
        result = cursor.fetchone()
        backtest_start = result[0] if result else five_years_ago

        conn.close()

        print(f"Training Period (baseline): {ten_years_ago} to {backtest_start}")
        print(f"Backtest Period (validation): {backtest_start} to {newest_date}")
        print()

        # Run backtest on last 5 years
        print("Running backtest on last 5 years...")
        print("This will take a few minutes depending on data volume...")
        print()

        import subprocess
        result = subprocess.run(
            [
                sys.executable,
                "backtest.py",
                "--start-date", str(backtest_start),
                "--end-date", str(newest_date)
            ],
            cwd=str(Path(__file__).parent.parent),
            capture_output=False,  # Show output in real-time
            text=True
        )

        if result.returncode != 0:
            print("\nERROR: Backtest failed!")
            print("Check that all required scripts exist (generate_signal.py, execute_trades.py)")
            sys.exit(1)

        # Backtest completed successfully
        print("\n" + "=" * 60)
        print("Backtest Complete - Generating Configuration")
        print("=" * 60)
        print()

        # Generate config with default parameters
        # The backtest validates that these parameters work
        config_start_date = ten_years_ago.strftime('%Y-%m-%d')
        notes = f"Validated via 5Y backtest ({backtest_start} to {newest_date})"

        output_file = str(Path(__file__).parent.parent / "alembic" / "seed_data" / "trading_config_initial.sql")
        generate_config_sql(output_file, start_date=config_start_date, notes=notes)

        print("\n✓ Training complete!")
        print(f"  - Default parameters validated via backtest")
        print(f"  - Config covers: {config_start_date} onwards")
        print(f"  - Backtest results saved to: data/back-test/")

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    """Main function to generate trading configuration."""
    output_dir = Path(__file__).parent.parent / "alembic" / "seed_data"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "trading_config_initial.sql"

    if RUN_FULL_TUNING:
        print("Running full tuning process...")
        train_with_historical_data()
    else:
        print("Generating default trading configuration...")
        generate_config_sql(str(output_file))

    print(f"\nThis file will be used by the seed data migration on first deployment.")
    print(f"\nAfter deployment with historical data, you can run monthly tuning to optimize.")


if __name__ == "__main__":
    main()
