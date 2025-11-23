"""add_lifetime_metrics_to_performance_metrics

Revision ID: 7124263ee77f
Revises: 27c553c12df9
Create Date: 2025-11-23 00:22:49.505191

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7124263ee77f'
down_revision: Union[str, None] = '27c553c12df9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns for lifetime P&L tracking
    op.add_column('performance_metrics', sa.Column('total_grants', sa.Float(), nullable=True))
    op.add_column('performance_metrics', sa.Column('lifetime_return', sa.Float(), nullable=True))
    op.add_column('performance_metrics', sa.Column('lifetime_return_pct', sa.Float(), nullable=True))


def downgrade() -> None:
    # Remove the lifetime P&L columns
    op.drop_column('performance_metrics', 'lifetime_return_pct')
    op.drop_column('performance_metrics', 'lifetime_return')
    op.drop_column('performance_metrics', 'total_grants')
