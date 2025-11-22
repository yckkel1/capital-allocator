"""initial_schema

Revision ID: cf868f7f5040
Revises:
Create Date: 2025-11-22 20:38:42.188617

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'cf868f7f5040'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create ActionType enum
    action_type = postgresql.ENUM('BUY', 'SELL', 'HOLD', name='actiontype', create_type=False)
    action_type.create(op.get_bind(), checkfirst=True)

    # Create price_history table
    op.create_table(
        'price_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('symbol', sa.String(length=10), nullable=False),
        sa.Column('open_price', sa.Float(), nullable=False),
        sa.Column('high_price', sa.Float(), nullable=False),
        sa.Column('low_price', sa.Float(), nullable=False),
        sa.Column('close_price', sa.Float(), nullable=False),
        sa.Column('volume', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_price_history_id'), 'price_history', ['id'], unique=False)
    op.create_index(op.f('ix_price_history_date'), 'price_history', ['date'], unique=False)
    op.create_index(op.f('ix_price_history_symbol'), 'price_history', ['symbol'], unique=False)

    # Create daily_signals table
    op.create_table(
        'daily_signals',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('trade_date', sa.Date(), nullable=False),
        sa.Column('generated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('allocations', sa.JSON(), nullable=False),
        sa.Column('model_type', sa.String(length=50), nullable=False),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('features_used', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('trade_date')
    )
    op.create_index(op.f('ix_daily_signals_id'), 'daily_signals', ['id'], unique=False)
    op.create_index(op.f('ix_daily_signals_trade_date'), 'daily_signals', ['trade_date'], unique=True)

    # Create trades table
    op.create_table(
        'trades',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('trade_date', sa.Date(), nullable=False),
        sa.Column('executed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('symbol', sa.String(length=10), nullable=False),
        sa.Column('action', action_type, nullable=False),
        sa.Column('quantity', sa.Float(), nullable=False),
        sa.Column('price', sa.Float(), nullable=False),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('signal_id', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_trades_id'), 'trades', ['id'], unique=False)
    op.create_index(op.f('ix_trades_trade_date'), 'trades', ['trade_date'], unique=False)

    # Create portfolio table
    op.create_table(
        'portfolio',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.String(length=10), nullable=False),
        sa.Column('quantity', sa.Float(), nullable=False),
        sa.Column('avg_cost', sa.Float(), nullable=False),
        sa.Column('last_updated', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('symbol')
    )
    op.create_index(op.f('ix_portfolio_id'), 'portfolio', ['id'], unique=False)

    # Create performance_metrics table
    op.create_table(
        'performance_metrics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('portfolio_value', sa.Float(), nullable=False),
        sa.Column('cash_balance', sa.Float(), nullable=False),
        sa.Column('total_value', sa.Float(), nullable=False),
        sa.Column('daily_return', sa.Float(), nullable=True),
        sa.Column('cumulative_return', sa.Float(), nullable=True),
        sa.Column('sharpe_ratio', sa.Float(), nullable=True),
        sa.Column('max_drawdown', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('date')
    )
    op.create_index(op.f('ix_performance_metrics_id'), 'performance_metrics', ['id'], unique=False)
    op.create_index(op.f('ix_performance_metrics_date'), 'performance_metrics', ['date'], unique=True)

    # Create trading_config table
    op.create_table(
        'trading_config',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('daily_capital', sa.Float(), nullable=False),
        sa.Column('assets', sa.JSON(), nullable=False),
        sa.Column('lookback_days', sa.Integer(), nullable=False),
        sa.Column('regime_bullish_threshold', sa.Float(), nullable=False),
        sa.Column('regime_bearish_threshold', sa.Float(), nullable=False),
        sa.Column('risk_high_threshold', sa.Float(), nullable=False),
        sa.Column('risk_medium_threshold', sa.Float(), nullable=False),
        sa.Column('allocation_low_risk', sa.Float(), nullable=False),
        sa.Column('allocation_medium_risk', sa.Float(), nullable=False),
        sa.Column('allocation_high_risk', sa.Float(), nullable=False),
        sa.Column('allocation_neutral', sa.Float(), nullable=False),
        sa.Column('sell_percentage', sa.Float(), nullable=False),
        sa.Column('momentum_weight', sa.Float(), nullable=False),
        sa.Column('price_momentum_weight', sa.Float(), nullable=False),
        sa.Column('max_drawdown_tolerance', sa.Float(), nullable=False),
        sa.Column('min_sharpe_target', sa.Float(), nullable=False),
        sa.Column('rsi_oversold_threshold', sa.Float(), nullable=False),
        sa.Column('rsi_overbought_threshold', sa.Float(), nullable=False),
        sa.Column('bollinger_std_multiplier', sa.Float(), nullable=False),
        sa.Column('mean_reversion_allocation', sa.Float(), nullable=False),
        sa.Column('volatility_adjustment_factor', sa.Float(), nullable=False),
        sa.Column('base_volatility', sa.Float(), nullable=False),
        sa.Column('min_confidence_threshold', sa.Float(), nullable=False),
        sa.Column('confidence_scaling_factor', sa.Float(), nullable=False),
        sa.Column('intramonth_drawdown_limit', sa.Float(), nullable=False),
        sa.Column('circuit_breaker_reduction', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('created_by', sa.String(length=100), nullable=True),
        sa.Column('notes', sa.String(length=500), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_trading_config_id'), 'trading_config', ['id'], unique=False)
    op.create_index(op.f('ix_trading_config_start_date'), 'trading_config', ['start_date'], unique=False)
    op.create_index(op.f('ix_trading_config_end_date'), 'trading_config', ['end_date'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_index(op.f('ix_trading_config_end_date'), table_name='trading_config')
    op.drop_index(op.f('ix_trading_config_start_date'), table_name='trading_config')
    op.drop_index(op.f('ix_trading_config_id'), table_name='trading_config')
    op.drop_table('trading_config')

    op.drop_index(op.f('ix_performance_metrics_date'), table_name='performance_metrics')
    op.drop_index(op.f('ix_performance_metrics_id'), table_name='performance_metrics')
    op.drop_table('performance_metrics')

    op.drop_index(op.f('ix_portfolio_id'), table_name='portfolio')
    op.drop_table('portfolio')

    op.drop_index(op.f('ix_trades_trade_date'), table_name='trades')
    op.drop_index(op.f('ix_trades_id'), table_name='trades')
    op.drop_table('trades')

    op.drop_index(op.f('ix_daily_signals_trade_date'), table_name='daily_signals')
    op.drop_index(op.f('ix_daily_signals_id'), table_name='daily_signals')
    op.drop_table('daily_signals')

    op.drop_index(op.f('ix_price_history_symbol'), table_name='price_history')
    op.drop_index(op.f('ix_price_history_date'), table_name='price_history')
    op.drop_index(op.f('ix_price_history_id'), table_name='price_history')
    op.drop_table('price_history')

    # Drop enum type
    sa.Enum(name='actiontype').drop(op.get_bind(), checkfirst=True)
