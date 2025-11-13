#!/usr/bin/env python3
"""
Cross-Month Backtest Runner
Runs backtest and analytics for any date range, including cross-month periods
"""
import os
import sys
import argparse
import subprocess
from datetime import datetime, date
from pathlib import Path

def validate_date(date_str: str) -> date:
    """Validate and parse date string"""
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        raise ValueError(f"Invalid date format: {date_str}. Use YYYY-MM-DD")

def run_command(command: list, description: str) -> bool:
    """Run a command and return success status"""
    print(f"\n{'='*60}")
    print(f"🔄 {description}")
    print(f"{'='*60}\n")

    try:
        result = subprocess.run(
            command,
            cwd=Path(__file__).parent,
            check=True,
            text=True
        )
        print(f"\n✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ {description} failed with exit code {e.returncode}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"\n❌ {description} failed: {e}", file=sys.stderr)
        return False

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Run backtest and analytics for any date range (supports cross-month)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run backtest for January 2024
  python run_backtest_with_analytics.py --start-date 2024-01-02 --end-date 2024-01-31

  # Run backtest across multiple months (Q1 2024)
  python run_backtest_with_analytics.py --start-date 2024-01-02 --end-date 2024-03-29

  # Run only backtest (skip analytics)
  python run_backtest_with_analytics.py --start-date 2024-01-02 --end-date 2024-02-29 --skip-analytics

  # Run only analytics (if backtest was already run)
  python run_backtest_with_analytics.py --start-date 2024-01-02 --end-date 2024-02-29 --skip-backtest
        """
    )

    parser.add_argument(
        '--start-date',
        required=True,
        help='Start date in YYYY-MM-DD format'
    )
    parser.add_argument(
        '--end-date',
        required=True,
        help='End date in YYYY-MM-DD format'
    )
    parser.add_argument(
        '--skip-backtest',
        action='store_true',
        help='Skip backtest execution (only run analytics)'
    )
    parser.add_argument(
        '--skip-analytics',
        action='store_true',
        help='Skip analytics execution (only run backtest)'
    )

    args = parser.parse_args()

    # Validate dates
    try:
        start_date = validate_date(args.start_date)
        end_date = validate_date(args.end_date)
    except ValueError as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1

    if start_date > end_date:
        print("❌ Error: Start date must be before or equal to end date", file=sys.stderr)
        return 1

    # Calculate date range info
    days_diff = (end_date - start_date).days + 1
    months_span = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month) + 1

    # Display run information
    print("\n" + "="*60)
    print("🚀 CROSS-MONTH BACKTEST RUNNER")
    print("="*60)
    print(f"\n📅 Date Range: {start_date} to {end_date}")
    print(f"   Duration: {days_diff} calendar days")
    print(f"   Months spanned: {months_span}")
    if months_span > 1:
        print(f"   ✨ Cross-month backtest detected!")
    print()

    success = True

    # Run backtest
    if not args.skip_backtest:
        backtest_cmd = [
            sys.executable,
            'backtest.py',
            '--start-date', args.start_date,
            '--end-date', args.end_date
        ]
        success = run_command(backtest_cmd, "Running backtest")

        if not success:
            print("\n❌ Backtest failed. Stopping execution.", file=sys.stderr)
            return 1
    else:
        print("\n⏭️  Skipping backtest (--skip-backtest flag set)")

    # Run analytics
    if not args.skip_analytics:
        analytics_cmd = [
            sys.executable,
            'analytics.py',
            '--start-date', args.start_date,
            '--end-date', args.end_date
        ]
        success = run_command(analytics_cmd, "Running analytics")

        if not success:
            print("\n❌ Analytics failed.", file=sys.stderr)
            return 1
    else:
        print("\n⏭️  Skipping analytics (--skip-analytics flag set)")

    # Summary
    print("\n" + "="*60)
    print("✅ ALL TASKS COMPLETED SUCCESSFULLY")
    print("="*60)
    print(f"\n📊 Results are saved in the data/ directory")
    print(f"   • Backtest reports: data/back-test/")
    print(f"   • Analytics reports: data/analytics/")
    print()

    return 0

if __name__ == "__main__":
    sys.exit(main())
