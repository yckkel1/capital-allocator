#!/usr/bin/env python3
"""
E2E Test Runner
Executes complete end-to-end tests using test database tables.
Includes initial parameter training and monthly parameter tuning.
"""
import os
import sys
import shutil
import json
from datetime import date, timedelta
from pathlib import Path

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.e2e.test_database import E2ETestDatabaseManager
from tests.e2e.e2e_backtest import E2EBacktest
from tests.e2e.e2e_analytics import E2EAnalytics
from tests.e2e.e2e_strategy_tuner import E2EStrategyTuner


def clear_test_reports():
    """Clear all test report directories"""
    report_base = Path(__file__).parent.parent.parent.parent / 'data' / 'test-reports'

    # Create directories if they don't exist
    report_base.mkdir(parents=True, exist_ok=True)
    for subdir in ['backtest', 'analytics', 'tuning', 'summary']:
        (report_base / subdir).mkdir(exist_ok=True)

    # Clear existing files
    if report_base.exists():
        for subdir in ['backtest', 'analytics', 'tuning', 'summary']:
            subdir_path = report_base / subdir
            if subdir_path.exists():
                for file in subdir_path.glob('*'):
                    if file.is_file():
                        file.unlink()

    print(f"Cleared test reports in {report_base}")


def save_summary_report(results: list, report_dir: Path):
    """Save a comprehensive summary report"""
    summary_file = report_dir / 'summary' / f'e2e_summary_{date.today().isoformat()}.txt'

    with open(summary_file, 'w') as f:
        f.write("=" * 60 + "\n")
        f.write("CAPITAL ALLOCATOR E2E TEST SUITE SUMMARY\n")
        f.write("=" * 60 + "\n\n")

        for result in results:
            f.write(f"Month {result['month']}: {result['start_date']} to {result['end_date']}\n")
            f.write(f"   Trading Days: {result['backtest']['trading_days']}\n")
            f.write(f"   Return: {result['analytics'].get('total_return_pct', 0):.2f}%\n")
            f.write(f"   Sharpe: {result['analytics'].get('sharpe_ratio', 0):.3f}\n")
            f.write(f"   Max Drawdown: {result['analytics'].get('max_drawdown', 0):.2f}%\n")
            f.write(f"   Volatility: {result['analytics'].get('volatility', 0):.2f}%\n")
            if 'tuning_report' in result:
                f.write(f"   Tuning Report: {result['tuning_report']}\n")
            f.write("\n")

        f.write("=" * 60 + "\n")

    return str(summary_file)


def run_e2e_test_suite():
    """
    Run complete E2E test suite with proper parameter training:
    1. Clear test tables and load price history
    2. Train initial parameters using 2024-11 data (before test period)
    3. For each test month:
       a. Tune parameters on first day using historical data
       b. Run backtest for the month
       c. Run analytics for the month
    4. Generate comprehensive reports
    """
    print("\n" + "="*60)
    print("CAPITAL ALLOCATOR E2E TEST SUITE")
    print("(With Initial Training and Monthly Parameter Tuning)")
    print("="*60 + "\n")

    report_base = Path(__file__).parent.parent.parent.parent / 'data' / 'test-reports'

    # Step 0: Clear old test reports
    print("Step 0: Clearing old test reports...")
    clear_test_reports()
    print("   Done\n")

    # Step 1: Set up test database
    print("Step 1: Setting up test database...")
    with E2ETestDatabaseManager() as db_manager:
        # Verify test tables exist
        exists, msg = db_manager.verify_test_tables_exist()
        if not exists:
            print(f"   ERROR: {msg}")
            print("   Please run migration 003_add_test_tables.py first")
            return False

        # Clear all test data
        db_manager.clear_all_test_tables()
        print("   Cleared all test tables")

        # Reset trading config (this will be replaced by trained config)
        db_manager.reset_test_trading_config()
        print("   Reset test trading config (temporary)")

        # Load price history
        records_loaded = db_manager.load_price_history_from_file()
        print(f"   Loaded {records_loaded} price history records")

        # Get date range
        date_range = db_manager.get_test_price_history_range()
        print(f"   Date range: {date_range['min_date']} to {date_range['max_date']}")

    print("   Done\n")

    # Step 2: Train initial parameters using data from 2024-11
    # Training period: Use first 30 days of data before first test period
    print("Step 2: Training initial parameters on historical data...")
    train_start = date(2024, 11, 11)  # Data starts here
    train_end = date(2024, 11, 30)    # Train on November data
    first_test_start = date(2024, 12, 1)

    tuner = E2EStrategyTuner(train_start, train_end)
    try:
        tuning_result = tuner.run(effective_date=first_test_start)
        print(f"   Initial parameters trained and saved")
        print(f"   Report: {tuning_result['report_file']}")
    finally:
        tuner.close()

    print("   Done\n")

    # Define test periods (3 consecutive months)
    # Test starts Dec 2024, uses Nov 2024 for initial training
    test_periods = [
        (date(2024, 12, 1), date(2024, 12, 31)),  # Month 1: December 2024
        (date(2025, 1, 1), date(2025, 1, 31)),    # Month 2: January 2025
        (date(2025, 2, 1), date(2025, 2, 28)),    # Month 3: February 2025
    ]

    results = []

    # Run backtests for each month
    for i, (start_date, end_date) in enumerate(test_periods, 1):
        print(f"Step {i + 2}: Month {i} ({start_date} to {end_date})")

        # On first day of each month (except first), tune parameters
        tuning_report = None
        if i > 1:
            print(f"   Tuning parameters for month {i}...")
            # Use all historical data up to the start of this month
            retune_start = date(2024, 11, 11)
            retune_end = start_date - timedelta(days=1)

            retuner = E2EStrategyTuner(retune_start, retune_end)
            try:
                retune_result = retuner.run(effective_date=start_date)
                tuning_report = retune_result['report_file']
                print(f"   Parameters tuned for {start_date}")
                print(f"   Report: {tuning_report}")
            finally:
                retuner.close()

        # Run backtest
        print(f"   Running backtest...")
        backtest = E2EBacktest(start_date, end_date)
        try:
            backtest_result = backtest.run()
            print(f"   Backtest completed: {backtest_result['trading_days']} trading days")
            print(f"   Report: {backtest_result['report_file']}")
        finally:
            backtest.close()

        # Run analytics
        print(f"   Running analytics...")
        analytics = E2EAnalytics(start_date, end_date)
        try:
            analytics_result = analytics.run()
            print(f"   Analytics completed:")
            print(f"      Total Return: {analytics_result.get('total_return_pct', 0):.2f}%")
            print(f"      Sharpe Ratio: {analytics_result.get('sharpe_ratio', 0):.3f}")
            print(f"      Max Drawdown: {analytics_result.get('max_drawdown', 0):.2f}%")
            print(f"   Report: {analytics_result.get('report_file', 'N/A')}")
        finally:
            analytics.close()

        result_entry = {
            'month': i,
            'start_date': start_date,
            'end_date': end_date,
            'backtest': backtest_result,
            'analytics': analytics_result
        }
        if tuning_report:
            result_entry['tuning_report'] = tuning_report

        results.append(result_entry)

        print("   Done\n")

    # Save comprehensive summary report
    summary_file = save_summary_report(results, report_base)
    print(f"Summary report saved: {summary_file}\n")

    # Summary
    print("="*60)
    print("E2E TEST SUITE SUMMARY")
    print("="*60 + "\n")

    for result in results:
        print(f"Month {result['month']}: {result['start_date']} to {result['end_date']}")
        print(f"   Trading Days: {result['backtest']['trading_days']}")
        print(f"   Return: {result['analytics'].get('total_return_pct', 0):.2f}%")
        print(f"   Sharpe: {result['analytics'].get('sharpe_ratio', 0):.3f}")
        print()

    print("All E2E tests completed successfully!")
    print("="*60 + "\n")

    return True


if __name__ == "__main__":
    success = run_e2e_test_suite()
    sys.exit(0 if success else 1)
