"""
Enhanced Daily Signal Generation Script
Run this early AM (6:00 AM ET) to generate today's allocation

REFACTORED: Business logic now in generate-signal/ modules
See backend/generate-signal/BREAKDOWN.md for module documentation
"""

import pandas as pd
from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models import PriceHistory, DailySignal, Portfolio, PerformanceMetrics
from config import get_settings, get_trading_config
from constraints_loader import get_active_strategy_constraints

# Import from refactored modules
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(backend_dir, 'generate-signal'))

from technical_indicators import calculate_rsi, calculate_bollinger_bands
from regime_detection import calculate_regime, detect_regime_transition, calculate_adaptive_threshold
from risk_assessment import calculate_risk_score, calculate_confidence_score
from feature_engineering import calculate_multi_timeframe_features
from asset_ranking import rank_assets
from mean_reversion import detect_mean_reversion_opportunity, detect_downward_pressure
from portfolio_allocation import allocate_diversified
from position_sizing import calculate_position_size, capital_scaling_adjustment, calculate_half_kelly
from circuit_breaker import check_circuit_breaker
from signal_logic import decide_action

settings = get_settings()
trading_config = get_trading_config()
constraints = get_active_strategy_constraints()


def generate_signal(trade_date: date = None):
    """Generate trading signal for the given date"""
    if trade_date is None:
        trade_date = date.today()

    db = SessionLocal()
    
    try:
        # Check if signal already exists
        existing_signal = db.query(DailySignal).filter(
            DailySignal.trade_date == trade_date
        ).first()

        if existing_signal:
            print(f"Signal for {trade_date} already exists. Skipping.")
            return

        print(f"\n{'='*80}")
        print(f"📊 GENERATING SIGNAL FOR {trade_date}")
        print(f"{'='*80}\n")

        # 1. Fetch price data for all assets
        features_by_asset = {}
        
        for symbol in trading_config.assets:
            df = pd.read_sql_query(
                f"""
                SELECT * FROM price_history
                WHERE symbol = '{symbol}'
                AND date <= '{trade_date}'
                ORDER BY date DESC
                LIMIT {trading_config.lookback_days}
                """,
                db.bind
            )

            if df.empty or len(df) < 60:
                print(f"⚠️  Insufficient data for {symbol}")
                continue

            df = df.sort_values('date')
            features_by_asset[symbol] = calculate_multi_timeframe_features(df, trading_config)

        if not features_by_asset:
            print("❌ No data available for signal generation")
            return

        # 2. Calculate regime and risk
        regime_score = calculate_regime(features_by_asset, trading_config)
        risk_score = calculate_risk_score(features_by_asset, trading_config)

        # Get previous regime for transition detection
        prev_signal = db.query(DailySignal).filter(
            DailySignal.trade_date < trade_date
        ).order_by(DailySignal.trade_date.desc()).first()

        prev_regime_score = prev_signal.features_used.get('regime', 0) if prev_signal else None
        transition = detect_regime_transition(regime_score, prev_regime_score, trading_config)

        # 3. Adaptive thresholds
        avg_vol = sum(f['volatility'] for f in features_by_asset.values()) / len(features_by_asset)
        adaptive_bullish = calculate_adaptive_threshold(
            trading_config.regime_bullish_threshold,
            avg_vol,
            trading_config.base_volatility,
            trading_config.volatility_adjustment_factor,
            trading_config
        )
        adaptive_bearish = calculate_adaptive_threshold(
            trading_config.regime_bearish_threshold,
            avg_vol,
            trading_config.base_volatility,
            trading_config.volatility_adjustment_factor,
            trading_config
        )

        # 4. Mean reversion opportunity detection
        mr_opportunity = detect_mean_reversion_opportunity(features_by_asset, regime_score, trading_config)

        # 5. Check circuit breaker
        cb_triggered, current_dd = check_circuit_breaker(db, trade_date, trading_config.intramonth_drawdown_limit)

        # 6. Get current holdings
        portfolio = db.query(Portfolio).filter(Portfolio.date == trade_date).all()
        has_holdings = len(portfolio) > 0 and sum(p.quantity for p in portfolio) > 0
        
        # Calculate cash percentage
        perf = db.query(PerformanceMetrics).filter(PerformanceMetrics.date == trade_date).first()
        cash_pct = (perf.cash_balance / perf.total_value) if perf and perf.total_value > 0 else 0.0

        # 7. Decide action
        action, allocation_pct, signal_type = decide_action(
            regime_score,
            risk_score,
            has_holdings,
            mr_opportunity,
            adaptive_bullish,
            adaptive_bearish,
            current_dd,
            features_by_asset,
            trading_config,
            cash_pct
        )

        # 8. Calculate confidence and position size
        trend_consistency = 1.0  # Calculate from features if needed
        is_mr_signal = 'mean_reversion' in signal_type
        
        confidence = calculate_confidence_score(
            regime_score,
            risk_score,
            trend_consistency,
            is_mr_signal,
            trading_config
        )

        # Determine confidence bucket
        if confidence >= trading_config.confidence_high_threshold:
            confidence_bucket = 'high'
        elif confidence >= trading_config.confidence_medium_threshold:
            confidence_bucket = 'medium'
        else:
            confidence_bucket = 'low'

        # Apply confidence scaling to allocation
        if action == "BUY":
            allocation_pct = calculate_position_size(
                allocation_pct,
                confidence,
                trading_config.confidence_scaling_factor
            )

            # Apply capital scaling
            capital = trading_config.daily_capital
            capital_scale = capital_scaling_adjustment(capital, constraints)
            allocation_pct *= capital_scale

        # 9. Rank assets and allocate
        asset_allocations = {}
        if action == "BUY":
            asset_scores = rank_assets(features_by_asset, trading_config)
            total_amount = trading_config.daily_capital * allocation_pct
            asset_allocations = allocate_diversified(asset_scores, total_amount, trading_config)

        # 10. Save signal
        signal = DailySignal(
            trade_date=trade_date,
            action=action,
            allocation_percentage=allocation_pct if action == "BUY" else 0.0,
            features_used={
                'regime': regime_score,
                'risk': risk_score,
                'confidence_score': confidence,
                'confidence_bucket': confidence_bucket,
                'signal_type': signal_type,
                'transition': transition,
                'asset_allocations': asset_allocations,
                'circuit_breaker_triggered': cb_triggered,
                'mean_reversion_opportunity': mr_opportunity[0] if mr_opportunity else False
            }
        )

        db.add(signal)
        db.commit()

        print(f"\n✅ Signal Generated:")
        print(f"   Action: {action}")
        print(f"   Allocation: {allocation_pct*100:.1f}%")
        print(f"   Signal Type: {signal_type}")
        print(f"   Confidence: {confidence:.2f} ({confidence_bucket})")
        print(f"   Regime: {regime_score:+.3f}")
        print(f"   Risk: {risk_score:.1f}")
        print(f"   Transition: {transition}")
        
    finally:
        db.close()


def main():
    """Main entry point"""
    generate_signal()
    print("\n✅ Signal generation complete\n")


if __name__ == "__main__":
    main()
