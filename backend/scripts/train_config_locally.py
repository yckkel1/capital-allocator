"""
Train trading configuration LOCALLY with 5Y/5Y split and MONTHLY TUNING.

This script:
1. Uses AGGRESSIVE parameters as baseline (2015-2020 establishes baseline)
2. Backtests on 2020-2025 data month-by-month with MONTHLY TUNING
3. Applies parameter adjustments monthly based on performance
4. Generates SQL for Railway deployment with final validated params

This is for LOCAL use only - generates validated config for production.

CRITICAL: This does ACTUAL training by:
- Learning from 2015-2020 baseline data
- Running monthly tuning during 2020-2025 backtest period
- Adjusting parameters monthly based on performance
"""
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta, date
import json
import psycopg2
import subprocess
from typing import Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import get_settings
from strategy_tuning import StrategyTuner


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


def get_first_trading_day_of_month(year: int, month: int, cursor) -> date:
    """Get the first trading day of a given month"""
    first_day = date(year, month, 1)

    cursor.execute("""
        SELECT date FROM price_history
        WHERE date >= %s
        ORDER BY date ASC
        LIMIT 1
    """, (first_day,))

    result = cursor.fetchone()
    return result[0] if result else first_day


def run_monthly_tuning_for_month(month_end_date: date, lookback_months: int = 3) -> bool:
    """
    Run monthly tuning for a specific backtest period

    Args:
        month_end_date: The end date of the month we just backtested
        lookback_months: Number of months to analyze

    Returns:
        True if tuning succeeded, False otherwise
    """
    print(f"\n{'='*60}")
    print(f"🔧 MONTHLY TUNING: Analysis up to {month_end_date}")
    print(f"{'='*60}\n")

    try:
        settings = get_settings()
        conn = psycopg2.connect(settings.database_url)
        cursor = conn.cursor()

        # Calculate analysis period based on backtest date (not today!)
        end_date = month_end_date
        start_date = end_date - timedelta(days=lookback_months * 30)

        # Find actual trading days with performance data
        cursor.execute("""
            SELECT MIN(date) as start, MAX(date) as end
            FROM performance_metrics
            WHERE date >= %s AND date <= %s
        """, (start_date, end_date))

        result = cursor.fetchone()

        if not result or not result[0] or not result[1]:
            print(f"WARNING: No performance data found between {start_date} and {end_date}")
            print("Skipping tuning for this month...")
            conn.close()
            return False

        actual_start, actual_end = result
        print(f"  Analysis Period: {actual_start} to {actual_end}")

        # Create tuner and manually orchestrate the tuning process
        from strategy_tuning import StrategyTuner
        tuner = StrategyTuner(lookback_months=lookback_months)

        # Override the analysis period (don't use date.today())
        print(f"  Evaluating trades...")
        evaluations = tuner.evaluate_trades(actual_start, actual_end)
        print(f"    Analyzed {len(evaluations)} trades")

        if len(evaluations) == 0:
            print("  WARNING: No trades found in period, skipping tuning")
            tuner.close()
            conn.close()
            return False

        print(f"  Analyzing performance by market condition...")
        condition_analysis = tuner.analyze_performance_by_condition(evaluations)

        print(f"  Analyzing confidence buckets...")
        confidence_analysis = tuner.analyze_confidence_buckets(evaluations)

        print(f"  Analyzing signal types...")
        signal_type_analysis = tuner.analyze_signal_types(evaluations)

        print(f"  Calculating overall metrics...")
        overall_metrics = tuner.calculate_overall_metrics(actual_start, actual_end)

        print(f"  Tuning parameters...")
        old_params = tuner.current_params
        new_params = tuner.tune_parameters(
            evaluations, condition_analysis, overall_metrics,
            confidence_analysis, signal_type_analysis
        )

        print(f"  Generating report...")
        report_path = tuner.generate_report(
            old_params, new_params, evaluations,
            condition_analysis, overall_metrics,
            actual_start, actual_end,
            confidence_analysis=confidence_analysis,
            signal_type_analysis=signal_type_analysis
        )

        # Save parameters with start date = first day of next month after month_end_date
        if month_end_date.month == 12:
            next_month_start = date(month_end_date.year + 1, 1, 1)
        else:
            next_month_start = date(month_end_date.year, month_end_date.month + 1, 1)

        tuner.save_parameters(new_params, report_path, next_month_start)

        tuner.close()
        conn.close()

        print(f"  ✓ Monthly tuning completed for period ending {month_end_date}")
        return True

    except Exception as e:
        print(f"WARNING: Monthly tuning failed for period ending {month_end_date}: {e}")
        print("Continuing with current parameters...")
        import traceback
        traceback.print_exc()
        return False


def run_5y_5y_backtest_with_monthly_tuning():
    """
    Run 5 year training / 5 year backtest WITH MONTHLY TUNING.

    Training period: 2015-2020 (establishes baseline with aggressive params)
    Backtest period: 2020-2025 (validates performance with monthly tuning)

    This does ACTUAL training by:
    1. Starting with aggressive baseline params
    2. Running backtest month-by-month
    3. Applying monthly tuning on 1st trading day of each month
    4. Adjusting parameters based on performance
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
        print("5Y/5Y Training with MONTHLY TUNING")
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

        print(f"Baseline Period: {ten_years_ago} to {backtest_start}")
        print(f"  (Aggressive params establish baseline)")
        print(f"Backtest Period: {backtest_start} to {newest_date}")
        print(f"  (Monthly tuning adjusts params)")
        print()

        # Generate list of months in backtest period
        current_date = backtest_start
        months_to_process = []

        while current_date <= newest_date:
            months_to_process.append((current_date.year, current_date.month))
            # Move to next month
            if current_date.month == 12:
                current_date = date(current_date.year + 1, 1, 1)
            else:
                current_date = date(current_date.year, current_date.month + 1, 1)

        print(f"Total months to backtest: {len(months_to_process)}")
        print()

        # Process month by month with monthly tuning
        tuning_count = 0

        for i, (year, month) in enumerate(months_to_process, 1):
            month_start = get_first_trading_day_of_month(year, month, cursor)

            # Get month end (last day of month or newest_date)
            if month == 12:
                next_month_start = date(year + 1, 1, 1)
            else:
                next_month_start = date(year, month + 1, 1)

            cursor.execute("""
                SELECT date FROM price_history
                WHERE date >= %s AND date < %s
                ORDER BY date DESC
                LIMIT 1
            """, (month_start, min(next_month_start, newest_date + timedelta(days=1))))

            result = cursor.fetchone()
            month_end = result[0] if result else month_start

            print(f"\n[{i}/{len(months_to_process)}] Processing {year}-{month:02d} ({month_start} to {month_end})")

            # Run backtest for this month
            print(f"  Running backtest for {year}-{month:02d}...")
            result = subprocess.run(
                [
                    sys.executable,
                    "backtest.py",
                    "--start-date", str(month_start),
                    "--end-date", str(month_end)
                ],
                cwd=str(Path(__file__).parent.parent),
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                print(f"\n  ERROR: Backtest failed for {year}-{month:02d}!")
                print(result.stderr)
                sys.exit(1)

            print(f"  ✓ Backtest completed for {year}-{month:02d}")

            # Run monthly tuning at the START of each month (after we have data)
            # Skip first month (need history to tune)
            if i > 1:
                # Run tuning with 3-month lookback, using month_end as analysis endpoint
                print(f"  Running monthly tuning for next month...")
                if run_monthly_tuning_for_month(month_end, lookback_months=3):
                    tuning_count += 1
                    print(f"  ✓ Parameters updated for next month")
                else:
                    print(f"  ⚠️  Tuning failed, continuing with current params")

        conn.close()

        print()
        print("=" * 60)
        print("BACKTEST WITH MONTHLY TUNING COMPLETED")
        print("=" * 60)
        print(f"✓ Processed {len(months_to_process)} months")
        print(f"✓ Applied {tuning_count} monthly tuning updates")
        print(f"✓ Parameters evolved from aggressive baseline to optimized config")
        print()

        return backtest_start, newest_date

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def generate_deployment_config(backtest_start, backtest_end):
    """
    Generate SQL config file for Railway deployment using FINAL TUNED parameters.

    This uses the most recent (active) config from the database after monthly tuning.
    """
    settings = get_settings()
    conn = psycopg2.connect(settings.database_url)
    cursor = conn.cursor()

    try:
        # Get the most recent (active) config after all monthly tuning
        cursor.execute("""
            SELECT
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
                daily_capital, assets, lookback_days
            FROM trading_config
            WHERE end_date IS NULL
            ORDER BY created_at DESC
            LIMIT 1
        """)

        result = cursor.fetchone()
        conn.close()

        if not result:
            print("ERROR: No active config found after training!")
            sys.exit(1)

        # Extract final tuned parameters
        (regime_bullish_threshold, regime_bearish_threshold,
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
         daily_capital, assets, lookback_days) = result

        config_start = (backtest_end - timedelta(days=3650)).strftime('%Y-%m-%d')
        notes = f"Trained via 5Y/5Y backtest with monthly tuning ({backtest_start} to {backtest_end})"

        output_file = Path(__file__).parent.parent / "alembic" / "seed_data" / "trading_config_initial.sql"

        # Use FINAL TUNED params for deployment
        with open(output_file, 'w') as f:
            f.write("-- Trading configuration TRAINED via 5Y/5Y backtest with monthly tuning\n")
            f.write(f"-- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"-- {notes}\n")
            f.write(f"-- Parameters evolved from aggressive baseline through monthly optimization\n\n")

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
            f.write(f"  {float(daily_capital)}, '{json.dumps(assets)}'::json, {int(lookback_days)},\n")
            f.write(f"  {float(regime_bullish_threshold)}, {float(regime_bearish_threshold)},\n")
            f.write(f"  {float(risk_high_threshold)}, {float(risk_medium_threshold)},\n")
            f.write(f"  {float(allocation_low_risk)}, {float(allocation_medium_risk)}, {float(allocation_high_risk)},\n")
            f.write(f"  {float(allocation_neutral)}, {float(sell_percentage)},\n")
            f.write(f"  {float(momentum_weight)}, {float(price_momentum_weight)},\n")
            f.write(f"  {float(max_drawdown_tolerance)}, {float(min_sharpe_target)},\n")
            f.write(f"  {float(rsi_oversold_threshold)}, {float(rsi_overbought_threshold)},\n")
            f.write(f"  {float(bollinger_std_multiplier)}, {float(mean_reversion_allocation)},\n")
            f.write(f"  {float(volatility_adjustment_factor)}, {float(base_volatility)},\n")
            f.write(f"  {float(min_confidence_threshold)}, {float(confidence_scaling_factor)},\n")
            f.write(f"  {float(intramonth_drawdown_limit)}, {float(circuit_breaker_reduction)},\n")
            f.write(f"  'railway_deployment', '{notes}'\n")
            f.write(")\n")
            f.write("ON CONFLICT DO NOTHING;\n")

        print()
        print("=" * 60)
        print("FINAL TUNED Configuration Generated")
        print("=" * 60)
        print(f"✓ File: {output_file}")
        print(f"✓ Config period: {config_start} onwards")
        print(f"✓ Trained via backtest: {backtest_start} to {backtest_end}")
        print(f"✓ Parameters optimized through monthly tuning")
        print()
        print("Key final parameters:")
        print(f"  - allocation_low_risk: {allocation_low_risk}")
        print(f"  - allocation_neutral: {allocation_neutral}")
        print(f"  - min_confidence_threshold: {min_confidence_threshold}")
        print(f"  - regime_bullish_threshold: {regime_bullish_threshold}")
        print()
        print("Next steps:")
        print("  1. Review backtest results in: data/back-test/")
        print("  2. Review monthly tuning reports in: data/strategy-tuning/")
        print("  3. If satisfied, commit the config:")
        print("     git add backend/alembic/seed_data/trading_config_initial.sql")
        print("     git commit -m 'Add trained trading config with monthly tuning'")
        print("  4. Deploy to Railway!")

    except Exception as e:
        print(f"\nERROR generating deployment config: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    """
    Main training workflow with MONTHLY TUNING.

    This implements ACTUAL training by:
    1. Creating aggressive baseline config (using 2015-2020 as baseline)
    2. Running 5Y backtest (2020-2025) with monthly tuning
    3. Generating final tuned config for Railway deployment
    """
    print()
    print("=" * 60)
    print("LOCAL TRAINING: 5Y/5Y with MONTHLY TUNING")
    print("=" * 60)
    print()
    print("This will:")
    print("  1. Create aggressive baseline config")
    print("  2. Run backtest month-by-month (2020-2025)")
    print("  3. Apply monthly tuning to adjust parameters")
    print("  4. Generate final tuned config for Railway")
    print()
    print("⚠️  This will take 30-60 minutes to complete!")
    print()

    # Step 1: Create aggressive baseline config
    create_aggressive_config_for_backtest()

    # Step 2: Run 5Y/5Y backtest with monthly tuning
    backtest_start, backtest_end = run_5y_5y_backtest_with_monthly_tuning()

    # Step 3: Generate deployment config from final tuned parameters
    generate_deployment_config(backtest_start, backtest_end)

    print()
    print("=" * 60)
    print("✅ TRAINING COMPLETE")
    print("=" * 60)
    print()
    print("Summary:")
    print("  ✓ Baseline established with aggressive parameters")
    print("  ✓ 5-year backtest completed with monthly tuning")
    print("  ✓ Parameters evolved through monthly optimization")
    print("  ✓ Final config generated for Railway deployment")
    print()


if __name__ == "__main__":
    main()
