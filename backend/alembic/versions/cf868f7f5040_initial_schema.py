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
        sa.Column('total_grants', sa.Float(), nullable=True),
        sa.Column('lifetime_return', sa.Float(), nullable=True),
        sa.Column('lifetime_return_pct', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('date')
    )
    op.create_index(op.f('ix_performance_metrics_id'), 'performance_metrics', ['id'], unique=False)
    op.create_index(op.f('ix_performance_metrics_date'), 'performance_metrics', ['date'], unique=True)

    # Create strategy_constraints table
    op.create_table(
        'strategy_constraints',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('min_holding_threshold', sa.Float(), nullable=False),
        sa.Column('capital_scale_tier1_threshold', sa.Float(), nullable=False),
        sa.Column('capital_scale_tier1_factor', sa.Float(), nullable=False),
        sa.Column('capital_scale_tier2_threshold', sa.Float(), nullable=False),
        sa.Column('capital_scale_tier2_factor', sa.Float(), nullable=False),
        sa.Column('capital_scale_tier3_threshold', sa.Float(), nullable=False),
        sa.Column('capital_scale_tier3_factor', sa.Float(), nullable=False),
        sa.Column('capital_scale_max_reduction', sa.Float(), nullable=False),
        sa.Column('min_trades_for_kelly', sa.Integer(), nullable=False),
        sa.Column('kelly_confidence_threshold', sa.Float(), nullable=False),
        sa.Column('min_data_days', sa.Integer(), nullable=False),
        sa.Column('pnl_horizon_short', sa.Integer(), nullable=False),
        sa.Column('pnl_horizon_medium', sa.Integer(), nullable=False),
        sa.Column('pnl_horizon_long', sa.Integer(), nullable=False),
        sa.Column('risk_free_rate', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('created_by', sa.String(length=100), nullable=True),
        sa.Column('notes', sa.String(length=500), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_strategy_constraints_id'), 'strategy_constraints', ['id'], unique=False)
    op.create_index(op.f('ix_strategy_constraints_start_date'), 'strategy_constraints', ['start_date'], unique=False)
    op.create_index(op.f('ix_strategy_constraints_end_date'), 'strategy_constraints', ['end_date'], unique=False)

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
        # Regime Transition Detection
        sa.Column('regime_transition_threshold', sa.Float(), nullable=False),
        sa.Column('momentum_loss_threshold', sa.Float(), nullable=False),
        sa.Column('momentum_gain_threshold', sa.Float(), nullable=False),
        sa.Column('strong_trend_threshold', sa.Float(), nullable=False),
        # Confidence Scoring
        sa.Column('regime_confidence_divisor', sa.Float(), nullable=False),
        sa.Column('risk_penalty_min', sa.Float(), nullable=False),
        sa.Column('risk_penalty_max', sa.Float(), nullable=False),
        sa.Column('trend_consistency_threshold', sa.Float(), nullable=False),
        sa.Column('mean_reversion_base_confidence', sa.Float(), nullable=False),
        sa.Column('consistency_bonus', sa.Float(), nullable=False),
        sa.Column('risk_penalty_multiplier', sa.Float(), nullable=False),
        sa.Column('confidence_bucket_high_threshold', sa.Float(), nullable=False),
        sa.Column('confidence_bucket_medium_threshold', sa.Float(), nullable=False),
        # Mean Reversion Signals
        sa.Column('bb_oversold_threshold', sa.Float(), nullable=False),
        sa.Column('bb_overbought_threshold', sa.Float(), nullable=False),
        sa.Column('oversold_strong_bonus', sa.Float(), nullable=False),
        sa.Column('oversold_mild_bonus', sa.Float(), nullable=False),
        sa.Column('rsi_mild_oversold', sa.Float(), nullable=False),
        sa.Column('bb_mild_oversold', sa.Float(), nullable=False),
        sa.Column('overbought_penalty', sa.Float(), nullable=False),
        # Downward Pressure Detection
        sa.Column('price_vs_sma_threshold', sa.Float(), nullable=False),
        sa.Column('high_volatility_threshold', sa.Float(), nullable=False),
        sa.Column('negative_return_threshold', sa.Float(), nullable=False),
        sa.Column('severe_pressure_threshold', sa.Float(), nullable=False),
        sa.Column('moderate_pressure_threshold', sa.Float(), nullable=False),
        sa.Column('severe_pressure_risk', sa.Float(), nullable=False),
        sa.Column('moderate_pressure_risk', sa.Float(), nullable=False),
        # Dynamic Selling Behavior
        sa.Column('defensive_cash_threshold', sa.Float(), nullable=False),
        sa.Column('sell_defensive_multiplier', sa.Float(), nullable=False),
        sa.Column('sell_aggressive_multiplier', sa.Float(), nullable=False),
        sa.Column('sell_moderate_pressure_multiplier', sa.Float(), nullable=False),
        sa.Column('sell_bullish_risk_multiplier', sa.Float(), nullable=False),
        # Risk-Based Thresholds
        sa.Column('mean_reversion_max_risk', sa.Float(), nullable=False),
        sa.Column('neutral_deleverage_risk', sa.Float(), nullable=False),
        sa.Column('neutral_hold_risk', sa.Float(), nullable=False),
        sa.Column('bullish_excessive_risk', sa.Float(), nullable=False),
        sa.Column('extreme_risk_threshold', sa.Float(), nullable=False),
        # Asset Diversification
        sa.Column('diversify_top_asset_max', sa.Float(), nullable=False),
        sa.Column('diversify_top_asset_min', sa.Float(), nullable=False),
        sa.Column('diversify_second_asset_max', sa.Float(), nullable=False),
        sa.Column('diversify_second_asset_min', sa.Float(), nullable=False),
        sa.Column('diversify_third_asset_max', sa.Float(), nullable=False),
        sa.Column('diversify_third_asset_min', sa.Float(), nullable=False),
        sa.Column('two_asset_top', sa.Float(), nullable=False),
        sa.Column('two_asset_second', sa.Float(), nullable=False),
        # Volatility & Normalization
        sa.Column('volatility_normalization_factor', sa.Float(), nullable=False),
        sa.Column('stability_threshold', sa.Float(), nullable=False),
        sa.Column('stability_discount_factor', sa.Float(), nullable=False),
        sa.Column('correlation_risk_base', sa.Float(), nullable=False),
        sa.Column('correlation_risk_multiplier', sa.Float(), nullable=False),
        # Risk Score Calculation Weights
        sa.Column('risk_volatility_weight', sa.Float(), nullable=False),
        sa.Column('risk_correlation_weight', sa.Float(), nullable=False),
        # Indicator Periods
        sa.Column('rsi_period', sa.Integer(), nullable=False),
        sa.Column('bollinger_period', sa.Integer(), nullable=False),
        # Trend Consistency
        sa.Column('trend_aligned_multiplier', sa.Float(), nullable=False),
        sa.Column('trend_mixed_multiplier', sa.Float(), nullable=False),
        # Metadata
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

    op.drop_index(op.f('ix_strategy_constraints_end_date'), table_name='strategy_constraints')
    op.drop_index(op.f('ix_strategy_constraints_start_date'), table_name='strategy_constraints')
    op.drop_index(op.f('ix_strategy_constraints_id'), table_name='strategy_constraints')
    op.drop_table('strategy_constraints')

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
