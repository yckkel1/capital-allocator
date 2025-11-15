#!/usr/bin/env python3
"""
E2E Test Runner
Executes complete end-to-end tests using test database tables.
"""
import os
import sys
import shutil
from datetime import date, timedelta
from pathlib import Path

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.e2e.test_database import E2ETestDatabaseManager
from tests.e2e.e2e_backtest import E2EBacktest
from tests.e2e.e2e_analytics import E2EAnalytics


def clear_test_reports():
    """Clear all test report directories"""
    report_base = Path(__file__).parent.parent.parent.parent / 'data' / 'test-reports'

    if report_base.exists():
        for subdir in ['backtest', 'analytics', 'tuning']:
            subdir_path = report_base / subdir
            if subdir_path.exists():
                for file in subdir_path.glob('*'):
                    if file.is_file():
                        file.unlink()

    print(f"Cleared test reports in {report_base}")


def run_e2e_test_suite():
    """
    Run complete E2E test suite:
    1. Clear test tables
    2. Load price history
    3. Run backtest month 1 + analytics
    4. Run backtest month 2 + analytics
    5. Run backtest month 3 + analytics
    """
    print("\n" + "="*60)
    print("CAPITAL ALLOCATOR E2E TEST SUITE")
    print("="*60 + "\n")

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

        # Reset trading config
        db_manager.reset_test_trading_config()
        print("   Reset test trading config")

        # Load price history
        records_loaded = db_manager.load_price_history_from_file()
        print(f"   Loaded {records_loaded} price history records")

        # Get date range
        date_range = db_manager.get_test_price_history_range()
        print(f"   Date range: {date_range['min_date']} to {date_range['max_date']}")

    print("   Done\n")

    # Define test periods (3 consecutive months)
    # Based on test data: 2024-11-11 to 2025-11-10
    test_periods = [
        (date(2024, 12, 1), date(2024, 12, 31)),  # Month 1: December 2024
        (date(2025, 1, 1), date(2025, 1, 31)),    # Month 2: January 2025
        (date(2025, 2, 1), date(2025, 2, 28)),    # Month 3: February 2025
    ]

    results = []

    # Run backtests for each month
    for i, (start_date, end_date) in enumerate(test_periods, 1):
        print(f"Step {i + 1}: Backtest Month {i} ({start_date} to {end_date})")

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

        results.append({
            'month': i,
            'start_date': start_date,
            'end_date': end_date,
            'backtest': backtest_result,
            'analytics': analytics_result
        })

        print("   Done\n")

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
