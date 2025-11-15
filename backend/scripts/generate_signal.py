"""
Daily signal generation script
Run this early AM (6:00 AM ET) to generate today's allocation
"""

import pandas as pd
import numpy as np
from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models import PriceHistory, DailySignal, Portfolio
from config import get_settings, get_trading_config

settings = get_settings()
trading_config = get_trading_config()  # Load trading parameters from database


def calculate_regime(features_by_asset: dict) -> float:
    """
    Detect market regime: bullish, neutral, or bearish
    
    Returns:
        float: Regime score (-1 to +1, positive = bullish)
    """
    regime_scores = []
    
    for symbol, features in features_by_asset.items():
        # Multi-timeframe momentum
        short_momentum = features.get('returns_5d', 0)
        medium_momentum = features.get('returns_20d', 0)
        long_momentum = features['returns_60d']
        
        # Trend consistency (all pointing same direction = stronger signal)
        momentum_avg = (short_momentum + medium_momentum + long_momentum) / 3
        
        # Price vs moving averages
        price_vs_sma20 = features['price_vs_sma20']
        price_vs_sma50 = features['price_vs_sma50']
        
        # Combine signals
        asset_regime = (
            momentum_avg * 0.5 +
            price_vs_sma20 * 0.3 +
            price_vs_sma50 * 0.2
        )
        
        regime_scores.append(asset_regime)
    
    # Average across all assets
    overall_regime = sum(regime_scores) / len(regime_scores)
    
    return overall_regime


def calculate_risk_score(features_by_asset: dict) -> float:
    """
    Calculate overall market risk level
    
    Returns:
        float: Risk score (0-100, higher = riskier)
    """
    volatilities = [f['volatility'] for f in features_by_asset.values()]
    avg_vol = sum(volatilities) / len(volatilities)
    
    # Normalize volatility to 0-100 scale (assume typical vol ~0.5% to 2%)
    # Higher vol = higher risk
    vol_score = min(100, (avg_vol / 0.02) * 100)
    
    # Check if volatility is rising (compare current to recent average)
    # This would require historical vol tracking - simplified for now
    
    # Correlation risk: When all assets move together = systemic risk
    # Simplified: Check if all have similar momentum
    momentums = [f['returns_60d'] for f in features_by_asset.values()]
    momentum_std = np.std(momentums)
    correlation_risk = max(0, 30 - momentum_std * 100)  # Low diversity = higher risk
    
    # Combined risk score
    risk_score = vol_score * 0.7 + correlation_risk * 0.3
    
    return min(100, max(0, risk_score))


def rank_assets(features_by_asset: dict) -> dict:
    """
    Rank assets using multiple factors
    
    Returns:
        dict: {symbol: composite_score}
    """
    scores = {}
    
    for symbol, features in features_by_asset.items():
        # Risk-adjusted momentum (primary factor)
        momentum_score = features['returns_60d'] / max(features['volatility'], 0.001)
        
        # Trend consistency: Are all timeframes aligned?
        short_momentum = features.get('returns_5d', 0)
        medium_momentum = features.get('returns_20d', 0)
        long_momentum = features['returns_60d']
        
        # Check if all positive or all negative
        all_positive = all(m > 0 for m in [short_momentum, medium_momentum, long_momentum])
        all_negative = all(m < 0 for m in [short_momentum, medium_momentum, long_momentum])
        trend_consistency = 1.5 if (all_positive or all_negative) else 1.0
        
        # Price momentum relative to moving averages
        price_momentum = (features['price_vs_sma20'] + features['price_vs_sma50']) / 2
        
        # Composite score
        composite = (
            momentum_score * 0.6 * trend_consistency +
            price_momentum * 0.4
        )
        
        scores[symbol] = composite
    
    return scores


def decide_action(regime_score: float, risk_score: float, has_holdings: bool) -> tuple:
    """
    Decide whether to BUY, SELL, or HOLD
    
    Returns:
        tuple: (action: str, allocation_pct: float)
        action: "BUY", "SELL", "HOLD"
        allocation_pct: How much of $1000 to use (0.0 to 1.0)
    """
    # Bearish regime
    if regime_score < -0.3:
        if has_holdings:
            # Sell weakest positions
            sell_pct = min(0.7, abs(regime_score) * 0.8)  # Sell 30-70%
            return ("SELL", sell_pct)
        else:
            return ("HOLD", 0.0)
    
    # Neutral regime
    elif -0.3 <= regime_score <= 0.3:
        if risk_score > 60:
            return ("HOLD", 0.0)
        else:
            # Small cautious buy
            return ("BUY", 0.2)
    
    # Bullish regime
    else:
        if risk_score > 70:
            # High risk = cautious
            allocation_pct = 0.3
        elif risk_score > 40:
            # Medium risk = moderate
            allocation_pct = 0.5
        else:
            # Low risk = aggressive
            allocation_pct = 0.8
        
        return ("BUY", allocation_pct)


def allocate_diversified(asset_scores: dict, total_amount: float) -> dict:
    """
    Allocate capital across assets proportionally (not winner-take-all)
    
    Args:
        asset_scores: {symbol: score}
        total_amount: Total $ to allocate
    
    Returns:
        dict: {symbol: allocation_amount}
    """
    # Only allocate to assets with positive scores
    positive_scores = {s: max(0, score) for s, score in asset_scores.items()}
    
    if sum(positive_scores.values()) == 0:
        return {s: 0.0 for s in asset_scores.keys()}
    
    # Sort by score
    sorted_assets = sorted(positive_scores.items(), key=lambda x: x[1], reverse=True)
    
    # Proportional allocation with concentration limits
    # Top asset: 40-50%, Second: 30-35%, Third: 15-25%
    allocations = {}
    
    if len(sorted_assets) >= 3 and all(score > 0 for _, score in sorted_assets[:3]):
        # All three are positive - diversify
        total_score = sum(score for _, score in sorted_assets)
        
        # Normalize scores
        weights = [score / total_score for _, score in sorted_assets]
        
        # Apply concentration limits
        allocations[sorted_assets[0][0]] = total_amount * min(0.50, max(0.40, weights[0]))
        allocations[sorted_assets[1][0]] = total_amount * min(0.35, max(0.30, weights[1]))
        allocations[sorted_assets[2][0]] = total_amount * min(0.25, max(0.15, weights[2]))
        
        # Normalize to exactly total_amount
        total_allocated = sum(allocations.values())
        for symbol in allocations:
            allocations[symbol] = allocations[symbol] * (total_amount / total_allocated)
    
    elif len(sorted_assets) >= 2 and sorted_assets[1][1] > 0:
        # Only top 2 are positive
        allocations[sorted_assets[0][0]] = total_amount * 0.65
        allocations[sorted_assets[1][0]] = total_amount * 0.35
        allocations[sorted_assets[2][0]] = 0.0
    
    else:
        # Only top 1 is positive
        allocations[sorted_assets[0][0]] = total_amount
        for symbol, _ in sorted_assets[1:]:
            allocations[symbol] = 0.0
    
    return allocations


def calculate_multi_timeframe_features(df: pd.DataFrame) -> dict:
    """
    Calculate features with multiple timeframes
    
    Returns:
        dict with feature values including 5d, 20d, 60d returns
    """
    # Calculate returns over different periods
    returns_5d = (df['close'].iloc[-1] / df['close'].iloc[-5] - 1) if len(df) >= 5 else 0
    returns_20d = (df['close'].iloc[-1] / df['close'].iloc[-20] - 1) if len(df) >= 20 else 0
    returns_60d = (df['close'].iloc[-1] / df['close'].iloc[-60] - 1) if len(df) >= 60 else 0
    
    # Volatility (20-day rolling std of daily returns)
    daily_returns = df['close'].pct_change()
    volatility = daily_returns.tail(20).std() if len(df) >= 20 else 0
    
    # Simple moving averages
    sma_20 = df['close'].tail(20).mean() if len(df) >= 20 else df['close'].iloc[-1]
    sma_50 = df['close'].tail(50).mean() if len(df) >= 50 else df['close'].iloc[-1]
    
    # Current price vs SMAs
    price_vs_sma20 = (df['close'].iloc[-1] / sma_20 - 1) if sma_20 > 0 else 0
    price_vs_sma50 = (df['close'].iloc[-1] / sma_50 - 1) if sma_50 > 0 else 0
    
    return {
        "returns_5d": returns_5d,
        "returns_20d": returns_20d,
        "returns_60d": returns_60d,
        "volatility": volatility,
        "price_vs_sma20": price_vs_sma20,
        "price_vs_sma50": price_vs_sma50,
        "current_price": df['close'].iloc[-1]
    }


def generate_signal(trade_date: date = None):
    """
    Generate allocation signal for the given trade date using multi-factor regime-based model
    
    Args:
        trade_date: Date to generate signal for (defaults to today)
    """
    if trade_date is None:
        trade_date = date.today()
    
    db = SessionLocal()
    
    try:
        print(f"Generating signal for {trade_date}...\n")
        
        # Check if signal already exists
        existing = db.query(DailySignal).filter(
            DailySignal.trade_date == trade_date
        ).first()
        
        if existing:
            print(f"Signal already exists for {trade_date}")
            return
        
        # Fetch historical data for each asset
        lookback_start = trade_date - timedelta(days=trading_config.lookback_days + 30)

        features_by_asset = {}

        for symbol in trading_config.assets:
            prices = db.query(PriceHistory).filter(
                PriceHistory.symbol == symbol,
                PriceHistory.date < trade_date,
                PriceHistory.date >= lookback_start
            ).order_by(PriceHistory.date.asc()).all()
            
            if len(prices) < 60:
                print(f"WARNING: Insufficient data for {symbol} ({len(prices)} days)")
                continue
            
            # Convert to DataFrame
            df = pd.DataFrame([
                {
                    'date': p.date,
                    'close': p.close_price,
                    'open': p.open_price,
                    'high': p.high_price,
                    'low': p.low_price,
                    'volume': p.volume
                }
                for p in prices
            ])
            
            # Calculate features with multiple timeframes
            features = calculate_multi_timeframe_features(df)
            features_by_asset[symbol] = features
            
            print(f"{symbol}:")
            print(f"  Price: ${features['current_price']:.2f}")
            print(f"  5d: {features['returns_5d']*100:+.2f}% | 20d: {features['returns_20d']*100:+.2f}% | 60d: {features['returns_60d']*100:+.2f}%")
            print(f"  Volatility: {features['volatility']*100:.2f}%")
        
        if not features_by_asset:
            print("ERROR: No data available for any assets")
            return
        
        # Step 1: Detect market regime
        regime_score = calculate_regime(features_by_asset)
        regime_label = "BULLISH" if regime_score > 0.3 else "BEARISH" if regime_score < -0.3 else "NEUTRAL"
        print(f"\nMarket Regime: {regime_label} (score: {regime_score:.3f})")
        
        # Step 2: Calculate risk level
        risk_score = calculate_risk_score(features_by_asset)
        risk_label = "HIGH" if risk_score > 70 else "MEDIUM" if risk_score > 40 else "LOW"
        print(f"Risk Level: {risk_label} ({risk_score:.1f}/100)")
        
        # Step 3: Rank assets
        asset_scores = rank_assets(features_by_asset)
        print(f"\nAsset Rankings:")
        for symbol, score in sorted(asset_scores.items(), key=lambda x: x[1], reverse=True):
            print(f"  {symbol}: {score:.4f}")
        
        # Step 4: Check current holdings
        holdings = db.query(Portfolio).filter(Portfolio.quantity > 0).all()
        has_holdings = len(holdings) > 0
        print(f"\nCurrent Holdings: {len(holdings)} positions")
        
        # Step 5: Decide action
        action, allocation_pct = decide_action(regime_score, risk_score, has_holdings)
        print(f"\nDecision: {action} (allocation: {allocation_pct*100:.0f}%)")
        
        # Step 6: Generate allocations based on action
        allocations = {}
        action_type = action
        
        if action == "BUY":
            # Diversified allocation
            buy_amount = trading_config.daily_capital * allocation_pct
            allocations = allocate_diversified(asset_scores, buy_amount)
            
            print(f"\nBuy Allocations (Total: ${buy_amount:.2f}):")
            for symbol, amount in sorted(allocations.items(), key=lambda x: x[1], reverse=True):
                if amount > 0:
                    print(f"  {symbol}: ${amount:.2f} ({amount/buy_amount*100:.1f}%)")
            
            cash_kept = trading_config.daily_capital - buy_amount
            if cash_kept > 0:
                print(f"  CASH: ${cash_kept:.2f}")
        
        elif action == "SELL":
            # Determine which positions to sell (weakest performers)
            if has_holdings:
                # Rank holdings by their asset scores
                holding_scores = {h.symbol: asset_scores.get(h.symbol, -999) for h in holdings}
                sorted_holdings = sorted(holding_scores.items(), key=lambda x: x[1])
                
                # Sell from weakest positions
                print(f"\nSell Signals (sell {allocation_pct*100:.0f}% of weakest):")
                for symbol, score in sorted_holdings:
                    # Mark for selling with negative allocation
                    allocations[symbol] = -allocation_pct  # Percentage to sell
                    print(f"  SELL {allocation_pct*100:.0f}% of {symbol} (score: {score:.4f})")
            else:
                allocations = {s: 0.0 for s in trading_config.assets}

        else:  # HOLD
            allocations = {s: 0.0 for s in trading_config.assets}
            print(f"\nHolding cash: ${trading_config.daily_capital:.2f}")
        
        # Store signal
        signal = DailySignal(
            trade_date=trade_date,
            allocations=allocations,
            model_type="regime_based",
            confidence_score=float(abs(regime_score)),
            features_used={
                "regime": float(regime_score),
                "risk": float(risk_score),
                "action": action_type,
                "allocation_pct": float(allocation_pct),
                "assets": {
                    symbol: {
                        "returns_5d": float(f["returns_5d"]),
                        "returns_20d": float(f["returns_20d"]),
                        "returns_60d": float(f["returns_60d"]),
                        "volatility": float(f["volatility"]),
                        "score": float(asset_scores.get(symbol, 0))
                    }
                    for symbol, f in features_by_asset.items()
                }
            }
        )
        
        db.add(signal)
        db.commit()
        
        print(f"\n✓ Signal generated and stored for {trade_date}")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate allocation signal")
    parser.add_argument("--date", type=str, help="Date to generate signal for (YYYY-MM-DD)")
    
    args = parser.parse_args()
    
    if args.date:
        target = datetime.strptime(args.date, "%Y-%m-%d").date()
        generate_signal(target)
    else:
        generate_signal()