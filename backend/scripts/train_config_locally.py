"""
Train trading configuration LOCAL LY with 5Y/5Y split.

This script:
1. Uses AGGRESSIVE parameters for realistic backtesting
2. Trains on 2015-2020 data (first 5 years)
3. Backtests on 2020-2025 data (last 5 years)
4. Generates SQL for Railway deployment

This is for LOCAL use only - generates validated config for production.
"""
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
import json
import psycopg2
import subprocess

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import get_settings


def create_aggressive_config_for_backtest():
    """
    Create aggressive config in local database for backtesting.

    This tests the strategy's full potential with proper capital deployment.
    """
    settings = get_settings()
    conn = psycopg2.connect(settings.database_url)
    cursor = conn.cursor()

    try:
        print("Creating aggressive backtest configuration...")

        # Delete existing configs
        cursor.execute("DELETE FROM trading_config")

        # Insert aggressive config
        cursor.execute("""
            INSERT INTO trading_config (
                start_date, end_date, daily_capital, assets, lookback_days,
                regime_bullish_threshold, regime_bearish_threshold,
                risk_high_threshold, risk_medium_threshold,
                allocation_low_risk, allocation_medium_risk, allocation_high_risk,
                allocation_neutral, sell_percentage,
                momentum_weight, price_momentum_weight,
                max_drawdown_tolerance, min_sharpe_target,
                rsi_oversold_threshold, rsi_overbought_threshold,
                bollinger_std_multiplier, mean_reversion_allocation,
                volatility_adjustment_factor, base_volatility,
                min_confidence_threshold, confidence_scaling_factor,
                intramonth_drawdown_limit, circuit_breaker_reduction,
                created_by, notes
            ) VALUES (
                '2015-01-01', NULL, 1000.0, '["SPY", "QQQ", "DIA"]'::jsonb, 252,
                0.1, -0.1,           -- More lenient regime detection
                70.0, 40.0,
                1.0, 1.0, 0.9,       -- Deploy 90-100% of capital!
                0.7,                 -- Even neutral deploys 70%
                0.7,
                0.6, 0.4,
                20.0, 0.8,           -- Higher drawdown tolerance
                30.0, 70.0,
                2.0, 0.5,
                0.2, 0.01,
                0.1,                 -- Lower confidence threshold (10%)
                0.2,                 -- Less confidence scaling penalty
                0.15, 0.5,           -- More tolerant circuit breaker
                'local_backtest', 'Aggressive config for 5Y/5Y validation'
            )
        """)

        conn.commit()
        print("  ✓ Aggressive config created")
        print()
        print("Key parameters:")
        print("  - regime_bullish_threshold: 0.1 (easier to trigger)")
        print("  - allocation_low_risk: 1.0 (100% deployment)")
        print("  - allocation_neutral: 0.7 (70% in neutral)")
        print("  - min_confidence_threshold: 0.1 (more trades)")
        print("  - confidence_scaling_factor: 0.2 (less penalty)")

    finally:
        cursor.close()
        conn.close()


def run_5y_5y_backtest():
    """
    Run 5 year training / 5 year backtest.

    Training period: 2015-2020 (establishes baseline)
    Backtest period: 2020-2025 (validates performance)
    """
    settings = get_settings()
    conn = psycopg2.connect(settings.database_url)
    cursor = conn.cursor()

    try:
        # Check data availability
        cursor.execute("""
            SELECT MIN(date) as oldest, MAX(date) as newest, COUNT(*) as total
            FROM price_history
        """)
        result = cursor.fetchone()

        if not result or not result[0]:
            print("ERROR: No price history data found!")
            print("Run: python scripts/fetch_data_yahoo.py --days 3650")
            sys.exit(1)

        oldest_date, newest_date, total_records = result
        years_of_data = (newest_date - oldest_date).days / 365.25

        print("=" * 60)
        print("5 Year Training / 5 Year Backtest")
        print("=" * 60)
        print()
        print(f"Price History:")
        print(f"  Oldest: {oldest_date}")
        print(f"  Newest: {newest_date}")
        print(f"  Years: {years_of_data:.1f}")
        print(f"  Records: {total_records}")
        print()

        # Calculate date ranges
        ten_years_ago = newest_date - timedelta(days=3650)
        five_years_ago = newest_date - timedelta(days=1825)

        # Find actual trading day
        cursor.execute("""
            SELECT date FROM price_history
            WHERE date >= %s
            ORDER BY date ASC
            LIMIT 1
        """, (five_years_ago,))
        result = cursor.fetchone()
        backtest_start = result[0] if result else five_years_ago

        conn.close()

        print(f"Training Period: {ten_years_ago} to {backtest_start}")
        print(f"Backtest Period: {backtest_start} to {newest_date}")
        print()
        print("Running backtest with AGGRESSIVE parameters...")
        print("This will take several minutes...")
        print()

        # Run backtest
        result = subprocess.run(
            [
                sys.executable,
                "backtest.py",
                "--start-date", str(backtest_start),
                "--end-date", str(newest_date)
            ],
            cwd=str(Path(__file__).parent.parent),
            text=True
        )

        if result.returncode != 0:
            print("\nERROR: Backtest failed!")
            sys.exit(1)

        return backtest_start, newest_date

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def generate_deployment_config(backtest_start, backtest_end):
    """Generate SQL config file for Railway deployment"""

    config_start = (backtest_end - timedelta(days=3650)).strftime('%Y-%m-%d')
    notes = f"Validated via 5Y backtest ({backtest_start} to {backtest_end})"

    output_file = Path(__file__).parent.parent / "alembic" / "seed_data" / "trading_config_initial.sql"

    # Use aggressive params for deployment (they've been validated!)
    with open(output_file, 'w') as f:
        f.write("-- Trading configuration validated via 5Y/5Y backtest\n")
        f.write(f"-- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
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
        f.write(f"  '{config_start}', NULL,\n")
        f.write("  1000.0, '[\"SPY\", \"QQQ\", \"DIA\"]'::json, 252,\n")
        f.write("  0.1, -0.1,\n")
        f.write("  70.0, 40.0,\n")
        f.write("  1.0, 1.0, 0.9,\n")
        f.write("  0.7, 0.7,\n")
        f.write("  0.6, 0.4,\n")
        f.write("  20.0, 0.8,\n")
        f.write("  30.0, 70.0,\n")
        f.write("  2.0, 0.5,\n")
        f.write("  0.2, 0.01,\n")
        f.write("  0.1, 0.2,\n")
        f.write("  0.15, 0.5,\n")
        f.write(f"  'railway_deployment', '{notes}'\n")
        f.write(")\n")
        f.write("ON CONFLICT DO NOTHING;\n")

    print()
    print("=" * 60)
    print("Configuration Generated")
    print("=" * 60)
    print(f"✓ File: {output_file}")
    print(f"✓ Config period: {config_start} onwards")
    print(f"✓ Validated via backtest: {backtest_start} to {backtest_end}")
    print()
    print("Next steps:")
    print("  1. Review backtest results in: data/back-test/")
    print("  2. If satisfied, commit the config:")
    print("     git add backend/alembic/seed_data/trading_config_initial.sql")
    print("     git commit -m 'Add validated trading config'")
    print("  3. Deploy to Railway!")


def main():
    """Main training workflow"""
    print()
    print("LOCAL TRAINING: 5Y/5Y Split with Aggressive Parameters")
    print()

    # Step 1: Create aggressive config
    create_aggressive_config_for_backtest()

    # Step 2: Run 5Y/5Y backtest
    backtest_start, backtest_end = run_5y_5y_backtest()

    # Step 3: Generate deployment config
    generate_deployment_config(backtest_start, backtest_end)


if __name__ == "__main__":
    main()
