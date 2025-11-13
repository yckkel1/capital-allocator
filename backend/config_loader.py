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
from psycopg2.extras import RealDictCursor
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
        """Create from database row"""
        return cls(
            id=row['id'],
            start_date=row['start_date'],
            end_date=row['end_date'],
            daily_capital=float(row['daily_capital']),
            assets=row['assets'],
            lookback_days=int(row['lookback_days']),
            regime_bullish_threshold=float(row['regime_bullish_threshold']),
            regime_bearish_threshold=float(row['regime_bearish_threshold']),
            risk_high_threshold=float(row['risk_high_threshold']),
            risk_medium_threshold=float(row['risk_medium_threshold']),
            allocation_low_risk=float(row['allocation_low_risk']),
            allocation_medium_risk=float(row['allocation_medium_risk']),
            allocation_high_risk=float(row['allocation_high_risk']),
            allocation_neutral=float(row['allocation_neutral']),
            sell_percentage=float(row['sell_percentage']),
            momentum_weight=float(row['momentum_weight']),
            price_momentum_weight=float(row['price_momentum_weight']),
            max_drawdown_tolerance=float(row['max_drawdown_tolerance']),
            min_sharpe_target=float(row['min_sharpe_target']),
            created_by=row.get('created_by'),
            notes=row.get('notes')
        )


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
                      AND start_date < %s
                """, (previous_end_date, start_date))

            # Insert new configuration
            cursor.execute("""
                INSERT INTO trading_config (
                    start_date, end_date,
                    daily_capital, assets, lookback_days,
                    regime_bullish_threshold, regime_bearish_threshold,
                    risk_high_threshold, risk_medium_threshold,
                    allocation_low_risk, allocation_medium_risk, allocation_high_risk,
                    allocation_neutral, sell_percentage,
                    momentum_weight, price_momentum_weight,
                    max_drawdown_tolerance, min_sharpe_target,
                    created_by, notes
                ) VALUES (
                    %s, NULL,
                    %s, %s, %s,
                    %s, %s,
                    %s, %s,
                    %s, %s, %s,
                    %s, %s,
                    %s, %s,
                    %s, %s,
                    %s, %s
                )
                RETURNING id
            """, (
                start_date,
                config.daily_capital, config.assets, config.lookback_days,
                config.regime_bullish_threshold, config.regime_bearish_threshold,
                config.risk_high_threshold, config.risk_medium_threshold,
                config.allocation_low_risk, config.allocation_medium_risk, config.allocation_high_risk,
                config.allocation_neutral, config.sell_percentage,
                config.momentum_weight, config.price_momentum_weight,
                config.max_drawdown_tolerance, config.min_sharpe_target,
                created_by, notes
            ))

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
