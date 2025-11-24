"""
Configuration Loader
Loads trading configuration from database with version tracking support
"""
import os
from datetime import date
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict
from functools import lru_cache

import psycopg2
from psycopg2.extras import RealDictCursor, Json
from dotenv import load_dotenv

# Load environment variables (only DATABASE_URL and API keys)
load_dotenv()


@dataclass
class TradingConfig:
    """Trading configuration parameters"""
    # Basic Trading Parameters
    daily_capital: float
    assets: list[str]
    lookback_days: int

    # Regime Detection Thresholds
    regime_bullish_threshold: float
    regime_bearish_threshold: float

    # Risk Level Thresholds
    risk_high_threshold: float
    risk_medium_threshold: float

    # Allocation Percentages (Bullish Regime)
    allocation_low_risk: float
    allocation_medium_risk: float
    allocation_high_risk: float

    # Neutral Regime Allocation
    allocation_neutral: float

    # Sell Percentage (Bearish Regime)
    sell_percentage: float

    # Asset Ranking Weights
    momentum_weight: float
    price_momentum_weight: float

    # Risk Management Targets
    max_drawdown_tolerance: float
    min_sharpe_target: float

    # Mean Reversion Parameters (NEW)
    rsi_oversold_threshold: float = 30.0
    rsi_overbought_threshold: float = 70.0
    bollinger_std_multiplier: float = 2.0
    mean_reversion_allocation: float = 0.4

    # Adaptive Threshold Parameters (NEW)
    volatility_adjustment_factor: float = 0.4
    base_volatility: float = 0.01

    # Confidence-Based Position Sizing (NEW)
    min_confidence_threshold: float = 0.3
    confidence_scaling_factor: float = 0.5

    # Circuit Breaker Parameters (NEW)
    intramonth_drawdown_limit: float = 0.10
    circuit_breaker_reduction: float = 0.5

    # Regime Transition Detection
    regime_transition_threshold: float = 0.1
    momentum_loss_threshold: float = -0.15
    momentum_gain_threshold: float = 0.15
    strong_trend_threshold: float = 0.4

    # Confidence Scoring
    regime_confidence_divisor: float = 0.5
    risk_penalty_min: float = 40.0
    risk_penalty_max: float = 60.0
    trend_consistency_threshold: float = 1.2
    mean_reversion_base_confidence: float = 0.6
    consistency_bonus: float = 0.2
    risk_penalty_multiplier: float = 0.3
    confidence_bucket_high_threshold: float = 0.7
    confidence_bucket_medium_threshold: float = 0.5

    # Mean Reversion Signals
    bb_oversold_threshold: float = -0.5
    bb_overbought_threshold: float = 0.5
    oversold_strong_bonus: float = 0.3
    oversold_mild_bonus: float = 0.1
    rsi_mild_oversold: float = 40.0
    bb_mild_oversold: float = 0.0
    overbought_penalty: float = -0.2

    # Downward Pressure Detection
    price_vs_sma_threshold: float = -0.02
    high_volatility_threshold: float = 0.015
    negative_return_threshold: float = -0.03
    severe_pressure_threshold: float = 0.67
    moderate_pressure_threshold: float = 0.50
    severe_pressure_risk: float = 50.0
    moderate_pressure_risk: float = 45.0

    # Dynamic Selling Behavior
    defensive_cash_threshold: float = 70.0
    sell_defensive_multiplier: float = 0.5
    sell_aggressive_multiplier: float = 1.2
    sell_moderate_pressure_multiplier: float = 0.6
    sell_bullish_risk_multiplier: float = 0.3

    # Risk-Based Thresholds
    mean_reversion_max_risk: float = 60.0
    neutral_deleverage_risk: float = 55.0
    neutral_hold_risk: float = 50.0
    bullish_excessive_risk: float = 65.0
    extreme_risk_threshold: float = 70.0

    # Asset Diversification
    diversify_top_asset_max: float = 0.50
    diversify_top_asset_min: float = 0.40
    diversify_second_asset_max: float = 0.35
    diversify_second_asset_min: float = 0.30
    diversify_third_asset_max: float = 0.25
    diversify_third_asset_min: float = 0.15
    two_asset_top: float = 0.65
    two_asset_second: float = 0.35

    # Volatility & Normalization
    volatility_normalization_factor: float = 0.02
    stability_threshold: float = 0.05
    stability_discount_factor: float = 0.5
    correlation_risk_base: float = 30.0
    correlation_risk_multiplier: float = 100.0

    # Risk Score Calculation Weights
    risk_volatility_weight: float = 0.7
    risk_correlation_weight: float = 0.3

    # Indicator Periods
    rsi_period: int = 14
    bollinger_period: int = 20

    # Trend Consistency
    trend_aligned_multiplier: float = 1.5
    trend_mixed_multiplier: float = 1.0

    # Regime Calculation Weights
    regime_momentum_weight: float = 0.5
    regime_sma20_weight: float = 0.3
    regime_sma50_weight: float = 0.2

    # Adaptive Threshold Clamps
    adaptive_threshold_clamp_min: float = 0.7
    adaptive_threshold_clamp_max: float = 1.5

    # Risk Label Thresholds
    risk_label_high_threshold: float = 70.0
    risk_label_medium_threshold: float = 40.0

    # Strategy Tuning Parameters (for monthly tuning script)
    # Market Condition Detection
    market_condition_r_squared_threshold: float = 0.6
    market_condition_slope_threshold: float = 0.1
    market_condition_choppy_r_squared: float = 0.3
    market_condition_choppy_volatility: float = 0.02

    # Trade Evaluation Scoring
    score_profitable_bonus: float = 0.3
    score_sharpe_bonus: float = 0.2
    score_low_dd_bonus: float = 0.2
    score_all_horizons_bonus: float = 0.2
    score_two_horizons_bonus: float = 0.1
    score_unprofitable_penalty: float = -0.3
    score_high_dd_penalty: float = -0.4
    score_sharpe_penalty: float = -0.2
    score_momentum_bonus: float = 0.3
    score_choppy_penalty: float = -0.3
    score_confidence_bonus: float = 0.1
    score_mean_reversion_bonus: float = 0.15

    # Tuning Decision Thresholds
    tune_aggressive_win_rate: float = 65.0
    tune_aggressive_participation: float = 0.5
    tune_aggressive_score: float = 0.2
    tune_conservative_win_rate: float = 45.0
    tune_conservative_dd: float = 15.0
    tune_conservative_score: float = -0.1

    # Parameter Adjustment Amounts
    tune_allocation_step: float = 0.1
    tune_neutral_step: float = 0.05
    tune_risk_threshold_step: float = 5.0
    tune_sharpe_aggressive_threshold: float = 1.5

    # Sell Strategy Tuning
    tune_sell_effective_threshold: float = 0.7
    tune_sell_underperform_threshold: float = -0.2
    tune_bearish_sell_participation: float = 0.3
    tune_high_dd_no_sell_threshold: float = 15.0
    tune_sell_major_adjustment: float = 0.15
    tune_sell_minor_adjustment: float = 0.1

    # Confidence Tuning
    tune_low_conf_poor_threshold: float = 40.0
    tune_high_conf_strong_threshold: float = 70.0
    tune_confidence_threshold_step: float = 0.05
    tune_confidence_scaling_step: float = 0.1

    # Mean Reversion Tuning
    tune_mr_good_threshold: float = 60.0
    tune_mr_poor_threshold: float = 45.0
    tune_rsi_threshold_step: float = 5.0

    # Validation Thresholds
    validation_sharpe_tolerance: float = 0.8
    validation_dd_tolerance: float = 1.2
    validation_passing_score: float = 0.5

    # Metadata
    id: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    created_by: Optional[str] = None
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)

    @classmethod
    def from_db_row(cls, row: Dict) -> 'TradingConfig':
        """Create from database row with automatic field mapping and defaults"""
        import inspect

        # Get all fields from the dataclass with their defaults
        fields = {f.name: f for f in cls.__dataclass_fields__.values()}

        # Build kwargs from database row
        kwargs = {}
        for field_name, field_info in fields.items():
            if field_name in row and row[field_name] is not None:
                value = row[field_name]
                # Convert to appropriate type
                if field_info.type == int or field_info.type == 'int':
                    kwargs[field_name] = int(value)
                elif field_info.type == float or field_info.type == 'float':
                    kwargs[field_name] = float(value)
                elif field_info.type == 'list[str]' or str(field_info.type).startswith('list'):
                    kwargs[field_name] = value  # Already a list from JSON
                else:
                    kwargs[field_name] = value
            # If field not in row, use default from dataclass (if it exists)
            # Dataclass defaults are automatically applied during instantiation

        return cls(**kwargs)


class ConfigLoader:
    """Loads trading configuration from database"""

    def __init__(self, database_url: Optional[str] = None):
        """
        Initialize config loader

        Args:
            database_url: Database connection URL. If not provided, reads from DATABASE_URL env var
        """
        self.database_url = database_url or os.getenv("DATABASE_URL")
        if not self.database_url:
            raise ValueError("DATABASE_URL not found in environment variables")

    def get_active_config(self, as_of_date: Optional[date] = None) -> TradingConfig:
        """
        Get the active trading configuration for a specific date

        Args:
            as_of_date: Date to get config for. Defaults to today.

        Returns:
            TradingConfig instance

        Raises:
            ValueError: If no active configuration found
        """
        if as_of_date is None:
            as_of_date = date.today()

        conn = psycopg2.connect(self.database_url)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        try:
            # Query for active config (where start_date <= as_of_date and (end_date is NULL or end_date >= as_of_date))
            cursor.execute("""
                SELECT * FROM trading_config
                WHERE start_date <= %s
                  AND (end_date IS NULL OR end_date >= %s)
                ORDER BY start_date DESC
                LIMIT 1
            """, (as_of_date, as_of_date))

            row = cursor.fetchone()

            if not row:
                raise ValueError(f"No active trading configuration found for date {as_of_date}")

            return TradingConfig.from_db_row(row)

        finally:
            cursor.close()
            conn.close()

    def get_config_by_id(self, config_id: int) -> TradingConfig:
        """
        Get a specific configuration by ID

        Args:
            config_id: Configuration ID

        Returns:
            TradingConfig instance
        """
        conn = psycopg2.connect(self.database_url)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        try:
            cursor.execute("SELECT * FROM trading_config WHERE id = %s", (config_id,))
            row = cursor.fetchone()

            if not row:
                raise ValueError(f"Configuration with ID {config_id} not found")

            return TradingConfig.from_db_row(row)

        finally:
            cursor.close()
            conn.close()

    def create_new_version(
        self,
        config: TradingConfig,
        start_date: date,
        created_by: str = "manual",
        notes: Optional[str] = None,
        close_previous: bool = True
    ) -> int:
        """
        Create a new version of the configuration

        Args:
            config: New configuration
            start_date: Start date for new configuration
            created_by: Who is creating this version
            notes: Optional notes
            close_previous: If True, sets end_date of previous active config to (start_date - 1 day)

        Returns:
            ID of newly created configuration
        """
        conn = psycopg2.connect(self.database_url)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        try:
            # If close_previous, update the previous active config
            if close_previous:
                from datetime import timedelta
                previous_end_date = start_date - timedelta(days=1)

                cursor.execute("""
                    UPDATE trading_config
                    SET end_date = %s
                    WHERE end_date IS NULL
                """, (previous_end_date,))

            # Build INSERT statement dynamically from dataclass fields
            # Exclude metadata fields (id, start_date, end_date, created_by, notes)
            excluded_fields = {'id', 'start_date', 'end_date', 'created_by', 'notes'}
            fields = {f.name: f for f in TradingConfig.__dataclass_fields__.values()
                     if f.name not in excluded_fields}

            # Build column names and placeholders
            columns = ['start_date', 'end_date'] + list(fields.keys()) + ['created_by', 'notes']
            placeholders = ['%s'] * len(columns)

            # Build values list
            values = [start_date, None]  # start_date and end_date (NULL)
            for field_name in fields.keys():
                value = getattr(config, field_name)
                # Wrap list/dict in Json() for PostgreSQL JSONB
                if isinstance(value, (list, dict)):
                    values.append(Json(value))
                else:
                    values.append(value)
            values.extend([created_by, notes])

            # Execute dynamic INSERT
            sql = f"""
                INSERT INTO trading_config ({', '.join(columns)})
                VALUES ({', '.join(placeholders)})
                RETURNING id
            """
            cursor.execute(sql, tuple(values))

            new_id = cursor.fetchone()['id']
            conn.commit()

            return new_id

        except Exception as e:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()


# Cached instance for performance
@lru_cache()
def get_config_loader() -> ConfigLoader:
    """Get cached config loader instance"""
    return ConfigLoader()


def get_active_trading_config(as_of_date: Optional[date] = None) -> TradingConfig:
    """
    Convenience function to get active trading config

    Args:
        as_of_date: Date to get config for. Defaults to today.

    Returns:
        TradingConfig instance
    """
    loader = get_config_loader()
    return loader.get_active_config(as_of_date)
