"""
Train initial trading configuration using historical data.

This script:
1. Loads 10 years of historical price data
2. Uses first 5 years to establish baseline parameters
3. Simulates trading in latter 5 years with monthly tuning
4. Generates SQL INSERT for the final optimized configuration
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

def generate_default_config_sql(output_file: str):
    """
    Generate SQL INSERT for default trading configuration.

    This creates a reasonable starting configuration without requiring
    full backtesting/tuning, which would need actual price data.
    """
    # Default configuration based on the model defaults
    config = {
        'start_date': '2015-01-01',  # Start from 10 years ago
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
        'notes': 'Default configuration for initial deployment'
    }

    with open(output_file, 'w') as f:
        f.write("-- Initial trading configuration\n")
        f.write("-- Generated on: {}\n".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        f.write("-- This is a default configuration; tune via monthly_tuning.py after deployment\n\n")

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

    This would:
    1. Load 10 years of price data
    2. Train on first 5 years
    3. Simulate trading on latter 5 years with monthly tuning
    4. Generate optimized config

    NOTE: This requires the monthly_tuning.py and backtesting infrastructure
    to be set up and price data to be available.
    """
    print("Full tuning process not yet implemented.")
    print("For initial deployment, using default configuration.")
    print("After deployment, run monthly_tuning.py to optimize parameters.")


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
        generate_default_config_sql(str(output_file))

    print(f"\nThis file will be used by the seed data migration on first deployment.")
    print(f"\nAfter deployment with historical data, you can run monthly tuning to optimize.")


if __name__ == "__main__":
    main()
