#!/usr/bin/env python3
"""
Monthly Strategy Tuning Runner
Run this script on the 1st trading day of each month

This script:
1. Analyzes the past N months of trading performance
2. Evaluates trades retroactively
3. Detects market conditions (momentum vs choppy)
4. Adjusts strategy parameters
5. Generates a comprehensive report with parameter changes
"""
import os
import sys
import subprocess
from datetime import datetime, date
from pathlib import Path

def is_first_trading_day_of_month() -> bool:
    """
    Check if today is the first trading day of the month
    (Simplified - checks if it's the 1st-3rd of the month and not weekend)
    """
    today = date.today()

    # Check if we're in the first 3 days of the month
    if today.day > 3:
        return False

    # Check if it's a weekday (Monday=0, Sunday=6)
    if today.weekday() >= 5:  # Saturday or Sunday
        return False

    return True


def run_tuning(lookback_months: int = 3) -> bool:
    """
    Run the strategy tuning analysis

    Args:
        lookback_months: Number of months to analyze

    Returns:
        True if successful, False otherwise
    """
    print(f"\n{'='*80}")
    print(f"🗓️  MONTHLY STRATEGY TUNING - {datetime.now().strftime('%Y-%m-%d')}")
    print(f"{'='*80}\n")

    backend_dir = Path(__file__).parent

    try:
        # Run strategy tuning
        result = subprocess.run(
            [sys.executable, 'strategy_tuning.py', '--lookback-months', str(lookback_months)],
            cwd=backend_dir,
            check=True,
            text=True
        )

        return result.returncode == 0

    except subprocess.CalledProcessError as e:
        print(f"\n❌ Strategy tuning failed with exit code {e.returncode}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"\n❌ Strategy tuning failed: {e}", file=sys.stderr)
        return False


def show_parameter_diff():
    """Show a diff of parameter changes if available"""
    backend_dir = Path(__file__).parent
    project_root = backend_dir.parent

    # Check if we have tuned parameters JSON
    json_path = project_root / 'data' / 'strategy-tuning' / 'tuned_parameters.json'

    if json_path.exists():
        import json

        print(f"\n{'='*80}")
        print(f"📊 PARAMETER UPDATE SUMMARY")
        print(f"{'='*80}\n")

        with open(json_path, 'r') as f:
            params = json.load(f)

        print("Updated parameters have been saved to the database.")
        print("\nKey changes to review:")
        print(f"  • Bullish Threshold: {params.get('regime_bullish_threshold', 'N/A')}")
        print(f"  • Low Risk Allocation: {params.get('allocation_low_risk', 'N/A')}")
        print(f"  • Medium Risk Allocation: {params.get('allocation_medium_risk', 'N/A')}")
        print(f"  • Neutral Allocation: {params.get('allocation_neutral', 'N/A')}")
        print()


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Monthly strategy tuning runner',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with default 3-month lookback
  python run_monthly_tuning.py

  # Run with 6-month lookback for more data
  python run_monthly_tuning.py --lookback-months 6

  # Force run even if not 1st trading day
  python run_monthly_tuning.py --force
        """
    )

    parser.add_argument(
        '--lookback-months',
        type=int,
        default=3,
        help='Number of months to analyze (default: 3)'
    )

    parser.add_argument(
        '--force',
        action='store_true',
        help='Force run even if not the 1st trading day of the month'
    )

    args = parser.parse_args()

    # Check if we should run
    if not args.force and not is_first_trading_day_of_month():
        print("\n⚠️  This script is intended to run on the 1st trading day of each month.")
        print(f"   Today is {date.today()}, which may not be the 1st trading day.")
        print("   Use --force to run anyway.\n")
        return 1

    # Run tuning
    success = run_tuning(args.lookback_months)

    if success:
        # Show summary
        show_parameter_diff()

        print(f"{'='*80}")
        print(f"✅ MONTHLY TUNING COMPLETED SUCCESSFULLY")
        print(f"{'='*80}\n")
        print("📋 Next Steps:")
        print("  1. Review the tuning report in data/strategy-tuning/")
        print("  2. New parameters are now active in the database")
        print("  3. Query: SELECT * FROM trading_config WHERE end_date IS NULL;")
        print("  4. Optionally run backtest with new parameters to validate")
        print()

        return 0
    else:
        print(f"\n{'='*80}")
        print(f"❌ MONTHLY TUNING FAILED")
        print(f"{'='*80}\n")
        print("Please check the error messages above and try again.")
        print()
        return 1


if __name__ == "__main__":
    sys.exit(main())
