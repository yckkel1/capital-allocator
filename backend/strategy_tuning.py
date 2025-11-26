"""
Monthly Strategy Tuning Script
Analyzes past performance and adjusts strategy parameters based on trade evaluation

This script should be run on the 1st trading day of each month to:
1. Evaluate past trades retroactively
2. Detect market conditions (momentum vs choppy)
3. Adjust parameters to improve future performance
4. Generate a detailed report of changes

REFACTORED: Business logic now in strategy-tuning/ modules
"""
import os
import sys
from datetime import date, timedelta
from typing import Dict, List, Tuple

import psycopg2
from psycopg2.extras import RealDictCursor

# Import configuration
from config import get_settings
from config_loader import TradingConfig, ConfigLoader

# Import from refactored modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'strategy-tuning'))

from constants import MONTH_DAYS_APPROX
from data_models import TradeEvaluation
from market_analysis import detect_market_condition
from trade_evaluation import calculate_drawdown_contribution, evaluate_trades
from performance_metrics import calculate_overall_metrics
from performance_analysis import (
    analyze_performance_by_condition,
    analyze_confidence_buckets,
    analyze_signal_types
)
from parameter_tuning import tune_parameters
from validation import perform_out_of_sample_validation
from reporting import generate_report, save_parameters

settings = get_settings()
DATABASE_URL = settings.database_url


class StrategyTuner:
    def __init__(self, lookback_months: int = 3):
        """Initialize strategy tuner"""
        self.conn = psycopg2.connect(DATABASE_URL)
        self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        self.lookback_months = lookback_months
        self.config_loader = ConfigLoader(DATABASE_URL)
        self.current_params = self.config_loader.get_active_config()
        self.config = self.current_params

    def close(self):
        self.cursor.close()
        self.conn.close()

    def get_analysis_period(self) -> Tuple[date, date]:
        """Get the date range for analysis (last N months)"""
        end_date = date.today() - timedelta(days=1)
        start_date = end_date - timedelta(days=self.lookback_months * MONTH_DAYS_APPROX)

        self.cursor.execute("""
            SELECT MIN(date) as start, MAX(date) as end
            FROM performance_metrics
            WHERE date >= %s AND date <= %s
        """, (start_date, end_date))

        result = self.cursor.fetchone()
        if result and result['start'] and result['end']:
            return result['start'], result['end']
        else:
            raise Exception(f"No performance data found for the last {self.lookback_months} months")

    def run_monthly_tuning(self) -> str:
        """Execute the complete monthly tuning process"""
        print("\n" + "="*80)
        print("🔧 MONTHLY STRATEGY TUNING")
        print("="*80 + "\n")

        # 1. Get analysis period
        start_date, end_date = self.get_analysis_period()
        print(f"Analysis Period: {start_date} to {end_date}")
        print(f"Lookback: {self.lookback_months} months\n")

        # 2. Evaluate trades
        print("📊 Evaluating trades...")
        evaluations = evaluate_trades(self.cursor, self.config, start_date, end_date)
        print(f"  Analyzed {len(evaluations)} trades\n")

        # 3. Analyze performance by different dimensions
        print("📈 Analyzing performance...")
        condition_analysis = analyze_performance_by_condition(evaluations, self.config)
        confidence_analysis = analyze_confidence_buckets(evaluations)
        signal_type_analysis = analyze_signal_types(evaluations)
        overall_metrics = calculate_overall_metrics(self.cursor, start_date, end_date)

        # 4. Tune parameters
        print("\n🎯 Tuning parameters...")
        old_params = self.current_params
        new_params = tune_parameters(
            self.current_params,
            self.config,
            evaluations,
            condition_analysis,
            overall_metrics,
            confidence_analysis,
            signal_type_analysis
        )

        # 5. Validate (optional - split data into train/test)
        validation_result = None
        if len(evaluations) > 30:
            days_in_period = (end_date - start_date).days
            if days_in_period > 60:
                train_end = start_date + timedelta(days=int(days_in_period * 0.7))
                test_start = train_end + timedelta(days=1)
                
                print("\n🧪 Performing out-of-sample validation...")
                validation_result = perform_out_of_sample_validation(
                    self.cursor,
                    self.config,
                    new_params,
                    (start_date, train_end),
                    (test_start, end_date)
                )
                print(f"  Validation score: {validation_result['validation_score']:.2f}")
                print(f"  Passes: {validation_result['passes_validation']}")

        # 6. Generate report
        print("\n📄 Generating report...")
        report_path = generate_report(
            self.config,
            old_params,
            new_params,
            evaluations,
            condition_analysis,
            overall_metrics,
            start_date,
            end_date,
            confidence_analysis,
            signal_type_analysis,
            validation_result
        )

        # 7. Save parameters
        next_month = date.today().replace(day=1)
        save_parameters(self.config_loader, new_params, report_path, next_month)

        print("\n✅ Monthly tuning complete!")
        print(f"Report saved: {report_path}\n")
        
        return report_path


def main():
    """Main entry point for monthly tuning"""
    tuner = StrategyTuner(lookback_months=3)
    try:
        report_path = tuner.run_monthly_tuning()
        print(f"\n✅ Tuning complete. Report: {report_path}")
    finally:
        tuner.close()


if __name__ == "__main__":
    main()
