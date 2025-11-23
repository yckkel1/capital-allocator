"""
Strategy Constraints Loader
Loads non-tunable system constraints from database
"""
import os
from datetime import date
from typing import Optional, Dict
from dataclasses import dataclass
from functools import lru_cache

import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class StrategyConstraints:
    """Non-tunable system constraints"""

    # Position Management
    min_holding_threshold: float = 10.0

    # Capital Scaling Breakpoints
    capital_scale_tier1_threshold: float = 10000.0
    capital_scale_tier1_factor: float = 1.0
    capital_scale_tier2_threshold: float = 50000.0
    capital_scale_tier2_factor: float = 0.75
    capital_scale_tier3_threshold: float = 200000.0
    capital_scale_tier3_factor: float = 0.50
    capital_scale_max_reduction: float = 0.35

    # Kelly Criterion
    min_trades_for_kelly: int = 10
    kelly_confidence_threshold: float = 0.6

    # Data Requirements
    min_data_days: int = 60

    # Time Horizons
    pnl_horizon_short: int = 10
    pnl_horizon_medium: int = 20
    pnl_horizon_long: int = 30

    # Risk-Free Rate
    risk_free_rate: float = 0.05

    # Metadata
    id: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    created_by: Optional[str] = None
    notes: Optional[str] = None

    @classmethod
    def from_db_row(cls, row: Dict) -> 'StrategyConstraints':
        """Create from database row with automatic field mapping"""
        # Get all fields from the dataclass
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
                else:
                    kwargs[field_name] = value

        return cls(**kwargs)


class ConstraintsLoader:
    """Loads strategy constraints from database"""

    def __init__(self, database_url: Optional[str] = None):
        """
        Initialize constraints loader

        Args:
            database_url: Database connection URL. If not provided, reads from DATABASE_URL env var
        """
        self.database_url = database_url or os.getenv("DATABASE_URL")
        if not self.database_url:
            raise ValueError("DATABASE_URL not found in environment variables")

    def get_active_constraints(self, as_of_date: Optional[date] = None) -> StrategyConstraints:
        """
        Get the active strategy constraints for a specific date

        Args:
            as_of_date: Date to get constraints for. Defaults to today.

        Returns:
            StrategyConstraints instance

        Raises:
            ValueError: If no active constraints found
        """
        if as_of_date is None:
            as_of_date = date.today()

        conn = psycopg2.connect(self.database_url)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        try:
            # Query for active constraints
            cursor.execute("""
                SELECT * FROM strategy_constraints
                WHERE start_date <= %s
                  AND (end_date IS NULL OR end_date >= %s)
                ORDER BY start_date DESC
                LIMIT 1
            """, (as_of_date, as_of_date))

            row = cursor.fetchone()

            if not row:
                raise ValueError(f"No active strategy constraints found for date {as_of_date}")

            return StrategyConstraints.from_db_row(row)

        finally:
            cursor.close()
            conn.close()


# Cached instance for performance
@lru_cache()
def get_constraints_loader() -> ConstraintsLoader:
    """Get cached constraints loader instance"""
    return ConstraintsLoader()


def get_active_strategy_constraints(as_of_date: Optional[date] = None) -> StrategyConstraints:
    """
    Convenience function to get active strategy constraints

    Args:
        as_of_date: Date to get constraints for. Defaults to today.

    Returns:
        StrategyConstraints instance
    """
    loader = get_constraints_loader()
    return loader.get_active_constraints(as_of_date)
