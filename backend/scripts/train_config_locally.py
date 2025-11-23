"""
Train trading configuration by running continuous backtest with monthly tuning.

Simple approach:
1. Start trading from min(date) in price_history with initial aggressive config
2. Run backtest continuously to max(date)
3. Apply monthly tuning along the way (skip first 3 months)
4. Final active trading_config = prod config
"""
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta, date
import json
import psycopg2
import subprocess

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import get_settings
from strategy_tuning import StrategyTuner


def create_initial_config(start_date: date):
    """Create initial aggressive config for training"""
    settings = get_settings()
    conn = psycopg2.connect(settings.database_url)
    cursor = conn.cursor()

    try:
        print("Creating initial trading configuration...")

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
                %s, NULL, 1000.0, '["SPY", "QQQ", "DIA"]'::jsonb, 252,
                0.1, -0.1,
                70.0, 40.0,
                1.0, 1.0, 0.9,
                0.7,
                0.7,
                0.6, 0.4,
                20.0, 0.8,
                30.0, 70.0,
                2.0, 0.5,
                0.2, 0.01,
                0.01,                # Very low confidence threshold (1%) - let trades through, tuning will optimize
                0.2,
                0.15, 0.5,
                'initial_training', 'Initial aggressive config for training'
            )
        """, (start_date,))

        conn.commit()
        print("  ✓ Initial config created")
        print()

    finally:
        cursor.close()
        conn.close()


def run_monthly_tuning(month_end_date: date, months_elapsed: int) -> bool:
    """Run monthly tuning based on performance data"""

    # Skip first 3 months
    if months_elapsed < 3:
        print(f"  ℹ️  Skipping tuning (need 3+ months of data, have {months_elapsed})")
        return False

    print(f"\n{'='*60}")
    print(f"🔧 MONTHLY TUNING: Analysis up to {month_end_date}")
    print(f"{'='*60}\n")

    try:
        settings = get_settings()
        conn = psycopg2.connect(settings.database_url)
        cursor = conn.cursor()

        # Use 3-month lookback
        end_date = month_end_date
        start_date = end_date - timedelta(days=90)

        # Find actual trading days with performance data
        cursor.execute("""
            SELECT MIN(date) as start, MAX(date) as end
            FROM performance_metrics
            WHERE date >= %s AND date <= %s
        """, (start_date, end_date))

        result = cursor.fetchone()

        if not result or not result[0] or not result[1]:
            print(f"  ⚠️  No performance data found, skipping tuning")
            conn.close()
            return False

        actual_start, actual_end = result
        print(f"  Analysis Period: {actual_start} to {actual_end}")

        # Create tuner
        tuner = StrategyTuner(lookback_months=3)

        # Evaluate trades
        print(f"  Evaluating trades...")
        evaluations = tuner.evaluate_trades(actual_start, actual_end)
        print(f"    Analyzed {len(evaluations)} trades")

        if len(evaluations) == 0:
            print("  ⚠️  No trades found, skipping tuning")
            tuner.close()
            conn.close()
            return False

        print(f"  Analyzing performance...")
        condition_analysis = tuner.analyze_performance_by_condition(evaluations)
        confidence_analysis = tuner.analyze_confidence_buckets(evaluations)
        signal_type_analysis = tuner.analyze_signal_types(evaluations)
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

        # Save parameters with start date = first day of next month
        if month_end_date.month == 12:
            next_month_start = date(month_end_date.year + 1, 1, 1)
        else:
            next_month_start = date(month_end_date.year, month_end_date.month + 1, 1)

        tuner.save_parameters(new_params, report_path, next_month_start)

        tuner.close()
        conn.close()

        print(f"  ✓ Monthly tuning completed")
        return True

    except Exception as e:
        print(f"  ⚠️  Tuning failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_continuous_backtest_with_tuning():
    """Run continuous backtest from min to max date with monthly tuning"""
    settings = get_settings()
    conn = psycopg2.connect(settings.database_url)
    cursor = conn.cursor()

    try:
        # Get date range from price_history
        cursor.execute("""
            SELECT MIN(date) as oldest, MAX(date) as newest, COUNT(DISTINCT date) as total
            FROM price_history
        """)
        result = cursor.fetchone()

        if not result or not result[0]:
            print("ERROR: No price history data found!")
            sys.exit(1)

        oldest_date, newest_date, total_days = result

        # Start trading 365 days after min(date) to have enough historical data
        # (generate_signal needs lookback_days + 30 = 282 days before trade_date)
        trading_start = oldest_date + timedelta(days=365)
        trading_end = newest_date

        print("=" * 60)
        print("CONTINUOUS BACKTEST WITH MONTHLY TUNING")
        print("=" * 60)
        print()
        print(f"Price History Range: {oldest_date} to {newest_date}")
        print(f"Trading Period: {trading_start} to {trading_end}")
        print(f"  (Starting 365 days after min(date) to have enough historical data)")
        print()

        # Create initial config - use oldest_date so config is valid for all trading dates
        create_initial_config(oldest_date)

        # Generate list of months to process
        current_date = trading_start
        months_to_process = []

        while current_date <= trading_end:
            months_to_process.append((current_date.year, current_date.month))
            # Move to next month
            if current_date.month == 12:
                current_date = date(current_date.year + 1, 1, 1)
            else:
                current_date = date(current_date.year, current_date.month + 1, 1)

        print(f"Processing {len(months_to_process)} months...")
        print()

        tuning_count = 0

        # Process month by month
        for i, (year, month) in enumerate(months_to_process, 1):
            # Get month boundaries
            month_start = date(year, month, 1)

            if month == 12:
                next_month_start = date(year + 1, 1, 1)
            else:
                next_month_start = date(year, month + 1, 1)

            # Find actual trading days in this month
            cursor.execute("""
                SELECT MIN(date), MAX(date)
                FROM price_history
                WHERE date >= %s AND date < %s
            """, (month_start, min(next_month_start, trading_end + timedelta(days=1))))

            result = cursor.fetchone()
            if not result or not result[0]:
                print(f"[{i}/{len(months_to_process)}] {year}-{month:02d}: No trading days, skipping")
                continue

            month_start_actual, month_end_actual = result

            print(f"[{i}/{len(months_to_process)}] Processing {year}-{month:02d} ({month_start_actual} to {month_end_actual})")

            # Run backtest for this month
            print(f"  Running backtest...")
            backtest_cmd = [
                sys.executable,
                "backtest.py",
                "--start-date", str(month_start_actual),
                "--end-date", str(month_end_actual)
            ]

            # Preserve portfolio from month 2 onwards
            if i > 1:
                backtest_cmd.append("--preserve-portfolio")

            result = subprocess.run(
                backtest_cmd,
                cwd=str(Path(__file__).parent.parent)
            )

            if result.returncode != 0:
                print(f"  ❌ Backtest failed!")
                sys.exit(1)

            # Check how much data was generated
            cursor.execute("""
                SELECT COUNT(*) FROM performance_metrics
                WHERE date >= %s AND date <= %s
            """, (month_start_actual, month_end_actual))
            metrics_count = cursor.fetchone()[0]

            if metrics_count > 0:
                print(f"  ✓ Generated {metrics_count} days of metrics")
            else:
                print(f"  ⚠️  No metrics generated")

            # Run monthly tuning (skip first 3 months)
            if i > 1:
                if run_monthly_tuning(month_end_actual, i):
                    tuning_count += 1

        conn.close()

        print()
        print("=" * 60)
        print("BACKTEST COMPLETED")
        print("=" * 60)
        print(f"✓ Processed {len(months_to_process)} months")
        print(f"✓ Applied {tuning_count} tuning updates")
        print()

        return trading_start, trading_end

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def generate_prod_config(start_date, end_date):
    """Generate production config from final tuned parameters"""
    settings = get_settings()
    conn = psycopg2.connect(settings.database_url)
    cursor = conn.cursor()

    try:
        # Get the most recent (active) config
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
            print("ERROR: No active config found!")
            sys.exit(1)

        # Extract params
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

        notes = f"Trained via continuous backtest ({start_date} to {end_date})"
        output_file = Path(__file__).parent.parent / "alembic" / "seed_data" / "trading_config_initial.sql"

        with open(output_file, 'w') as f:
            f.write("-- Trading configuration trained via continuous backtest with monthly tuning\n")
            f.write(f"-- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"-- Training period: {start_date} to {end_date}\n\n")

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
            f.write(f"  '{start_date}', NULL,\n")
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
            f.write(f"  'prod', '{notes}'\n")
            f.write(")\n")
            f.write("ON CONFLICT DO NOTHING;\n")

        print()
        print("=" * 60)
        print("PRODUCTION CONFIG GENERATED")
        print("=" * 60)
        print(f"✓ File: {output_file}")
        print(f"✓ Training period: {start_date} to {end_date}")
        print()
        print("Key parameters:")
        print(f"  - allocation_low_risk: {allocation_low_risk}")
        print(f"  - allocation_neutral: {allocation_neutral}")
        print(f"  - min_confidence_threshold: {min_confidence_threshold}")
        print(f"  - regime_bullish_threshold: {regime_bullish_threshold}")
        print()

    except Exception as e:
        print(f"\nERROR generating config: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    """Main training workflow"""
    print()
    print("=" * 60)
    print("TRAINING: Continuous Backtest with Monthly Tuning")
    print("=" * 60)
    print()
    print("This will:")
    print("  1. Start trading from min(date) in price_history")
    print("  2. Run continuously to max(date)")
    print("  3. Apply monthly tuning (skip first 3 months)")
    print("  4. Generate final config for production")
    print()

    # Run backtest with tuning
    start_date, end_date = run_continuous_backtest_with_tuning()

    # Generate production config
    generate_prod_config(start_date, end_date)

    print()
    print("=" * 60)
    print("✅ TRAINING COMPLETE")
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()
