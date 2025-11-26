"""
Reporting Module
Functions for generating reports and saving parameters
"""
import os
import json
from datetime import datetime, date, timedelta
from typing import List, Dict
from config_loader import TradingConfig, ConfigLoader
from .data_models import TradeEvaluation
from .constants import REPORT_SEPARATOR_WIDTH, TOP_N_WORST_TRADES


def save_parameters(config_loader: ConfigLoader, params: TradingConfig, 
                   report_path: str, start_date: date):
    """Save parameters to database as a new version"""
    config_id = config_loader.create_new_version(
        params,
        start_date=start_date,
        created_by='strategy_tuning',
        notes=f'Monthly tuning - report: {os.path.basename(report_path)}',
        close_previous=True
    )

    print(f"\n💾 Parameters saved to database:")
    print(f"   Config ID: {config_id}")
    print(f"   Start Date: {start_date}")
    print(f"   Previous config end date set to: {start_date - timedelta(days=1)}")

    # Also save JSON version for reference
    json_path = os.path.join(os.path.dirname(report_path), 'tuned_parameters.json')
    with open(json_path, 'w') as f:
        json.dump(params.to_dict(), f, indent=2, default=str)

    print(f"💾 JSON backup saved to: {json_path}")


def generate_report(config, old_params: TradingConfig, new_params: TradingConfig,
                   evaluations: List[TradeEvaluation], condition_analysis: Dict,
                   overall_metrics: Dict, start_date: date, end_date: date,
                   confidence_analysis: Dict = None,
                   signal_type_analysis: Dict = None,
                   validation_result: Dict = None) -> str:
    """Generate comprehensive tuning report"""
    report_lines = []

    def add(text=""):
        print(text)
        report_lines.append(text)

    add(f"\n{'='*REPORT_SEPARATOR_WIDTH}")
    add(f"📊 MONTHLY STRATEGY TUNING REPORT")
    add(f"{'='*REPORT_SEPARATOR_WIDTH}\n")
    add(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    add(f"Analysis Period: {start_date} to {end_date}")
    add(f"Total Trading Days: {overall_metrics.get('total_days', 0)}\n")

    # Overall Performance
    add(f"{'='*REPORT_SEPARATOR_WIDTH}")
    add(f"📈 OVERALL PERFORMANCE METRICS")
    add(f"{'='*REPORT_SEPARATOR_WIDTH}\n")
    add(f"Total Return: {overall_metrics.get('total_return', 0):+.2f}%")
    add(f"Sharpe Ratio: {overall_metrics.get('sharpe_ratio', 0):.3f}")
    add(f"Max Drawdown: {overall_metrics.get('max_drawdown', 0):.2f}%\n")

    # Trade Evaluations Summary
    add(f"{'='*REPORT_SEPARATOR_WIDTH}")
    add(f"🔍 TRADE EVALUATION SUMMARY")
    add(f"{'='*REPORT_SEPARATOR_WIDTH}\n")

    bad_trades = [e for e in evaluations if e.should_have_avoided]
    good_trades = [e for e in evaluations if e.score > config.good_trade_score_threshold]

    add(f"Total Trades Analyzed: {len(evaluations)}")
    add(f"Good Trades (score > {config.good_trade_score_threshold}): {len(good_trades)} ({len(good_trades)/len(evaluations)*100:.1f}%)")
    add(f"Trades That Should Have Been Avoided: {len(bad_trades)} ({len(bad_trades)/len(evaluations)*100:.1f}%)\n")

    # Performance by Market Condition
    add(f"{'='*REPORT_SEPARATOR_WIDTH}")
    add(f"🌍 PERFORMANCE BY MARKET CONDITION")
    add(f"{'='*REPORT_SEPARATOR_WIDTH}\n")

    for condition in ['momentum', 'choppy', 'overall']:
        perf = condition_analysis[condition]
        add(f"{condition.upper()}:")
        add(f"  Trades: {perf['count']}")
        if perf['count'] > 0:
            add(f"  Win Rate: {perf['win_rate']:.1f}%")
            add(f"  Avg Score: {perf['avg_score']:+.3f}")
            add(f"  Total P&L: ${perf['total_pnl']:+,.2f}")
        add()

    # Parameter Changes
    add(f"{'='*REPORT_SEPARATOR_WIDTH}")
    add(f"🔧 PARAMETER ADJUSTMENTS")
    add(f"{'='*REPORT_SEPARATOR_WIDTH}\n")

    changes_made = False
    old_dict = old_params.to_dict()
    new_dict = new_params.to_dict()

    for key in sorted(old_dict.keys()):
        old_val = old_dict[key]
        new_val = new_dict[key]

        if isinstance(old_val, (int, float)) and isinstance(new_val, (int, float)):
            if abs(old_val - new_val) > 0.001:
                change = new_val - old_val
                marker = "📈" if change > 0 else "📉"
                add(f"{marker} {key}: {old_val:.3f} → {new_val:.3f} ({change:+.3f})")
                changes_made = True

    if not changes_made:
        add("✅ No parameter changes recommended - current strategy is performing well!\n")

    # Save report
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"strategy_tuning_report_{start_date}_to_{end_date}_{timestamp}.txt"
    
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    report_dir = os.path.join(backend_dir, '..', 'data', 'strategy-tuning')
    
    os.makedirs(report_dir, exist_ok=True)
    filepath = os.path.join(report_dir, filename)

    with open(filepath, 'w') as f:
        f.write('\n'.join(report_lines))

    print(f"💾 Report saved to: {filepath}\n")

    return filepath
