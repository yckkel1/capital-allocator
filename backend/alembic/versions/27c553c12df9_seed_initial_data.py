"""seed_initial_data

Revision ID: 27c553c12df9
Revises: cf868f7f5040
Create Date: 2025-11-22 20:40:49.643248

This migration loads initial seed data for first deployment:
1. 10 years of historical price data (price_history)
2. Initial trading configuration

The migration is idempotent - it only loads data if tables are empty.
"""
from typing import Sequence, Union
from pathlib import Path

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = '27c553c12df9'
down_revision: Union[str, None] = 'cf868f7f5040'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Load seed data for initial deployment."""
    conn = op.get_bind()

    # Check if price_history table is empty
    result = conn.execute(text("SELECT COUNT(*) FROM price_history")).fetchone()
    price_history_count = result[0] if result else 0

    if price_history_count == 0:
        print("Loading historical price data...")

        # Load price history data if file exists
        seed_data_dir = Path(__file__).parent.parent / "seed_data"
        price_history_file = seed_data_dir / "price_history_10y.sql"

        if price_history_file.exists():
            print(f"  Loading from {price_history_file}")
            sql_content = price_history_file.read_text()

            # Execute SQL in chunks to avoid memory issues
            statements = sql_content.split(';')
            for statement in statements:
                statement = statement.strip()
                if statement and not statement.startswith('--'):
                    conn.execute(text(statement))

            # Verify loaded data
            result = conn.execute(text("SELECT COUNT(*) FROM price_history")).fetchone()
            count = result[0] if result else 0
            print(f"  ✓ Loaded {count} price history records")
        else:
            print(f"  ⚠ Seed data file not found: {price_history_file}")
            print(f"  Run scripts/export_historical_data.py to generate it")
    else:
        print(f"Price history already has {price_history_count} records, skipping seed data")

    # Check if trading_config table is empty
    result = conn.execute(text("SELECT COUNT(*) FROM trading_config")).fetchone()
    config_count = result[0] if result else 0

    if config_count == 0:
        print("Loading initial trading configuration...")

        # Load trading config if file exists
        seed_data_dir = Path(__file__).parent.parent / "seed_data"
        config_file = seed_data_dir / "trading_config_initial.sql"

        if config_file.exists():
            print(f"  Loading from {config_file}")
            sql_content = config_file.read_text()

            # Execute SQL
            statements = sql_content.split(';')
            for statement in statements:
                statement = statement.strip()
                if statement and not statement.startswith('--'):
                    conn.execute(text(statement))

            print(f"  ✓ Loaded initial trading configuration")
        else:
            print(f"  ⚠ Seed data file not found: {config_file}")
            print(f"  Run scripts/train_initial_config.py to generate it")
    else:
        print(f"Trading config already has {config_count} records, skipping seed data")

    # Check if strategy_constraints table is empty
    result = conn.execute(text("SELECT COUNT(*) FROM strategy_constraints")).fetchone()
    constraints_count = result[0] if result else 0

    if constraints_count == 0:
        print("Loading initial strategy constraints...")

        # Load strategy constraints if file exists
        seed_data_dir = Path(__file__).parent.parent / "seed_data"
        constraints_file = seed_data_dir / "strategy_constraints_initial.sql"

        if constraints_file.exists():
            print(f"  Loading from {constraints_file}")
            sql_content = constraints_file.read_text()

            # Execute SQL
            statements = sql_content.split(';')
            for statement in statements:
                statement = statement.strip()
                if statement and not statement.startswith('--'):
                    conn.execute(text(statement))

            print(f"  ✓ Loaded initial strategy constraints")
        else:
            print(f"  ⚠ Seed data file not found: {constraints_file}")
    else:
        print(f"Strategy constraints already has {constraints_count} records, skipping seed data")


def downgrade() -> None:
    """
    Downgrade is intentionally not implemented.

    Seed data should not be automatically removed during downgrade
    as it represents historical records that may be referenced elsewhere.
    If you need to remove seed data, do it manually.
    """
    print("Downgrade: Seed data is not automatically removed")
    print("If you need to clear data, run: DELETE FROM price_history; DELETE FROM trading_config; DELETE FROM strategy_constraints;")
