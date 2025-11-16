"""
E2E Backtest module that uses test tables instead of production tables.
This is a modified version of backtest.py for E2E testing.
Uses actual trading strategy logic with regime detection, RSI, and Bollinger Bands.
"""
import os
import sys
import json
import math
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import List, Dict, Optional
from pathlib import Path

import psycopg2
from psycopg2.extras import RealDictCursor
import numpy as np

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Get DATABASE_URL from environment or config
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    try:
        from config import get_settings
        settings = get_settings()
        DATABASE_URL = settings.database_url
    except ImportError:
        # If config module can't be imported (e.g., missing pydantic_settings in test env)
        DATABASE_URL = "postgresql://test:test@localhost/allocator_db"


class E2EBacktest:
    """E2E Backtest that uses test tables with actual trading strategy logic"""

    def __init__(self, start_date: date, end_date: date, report_dir: str = None):
        self.conn = psycopg2.connect(DATABASE_URL)
        self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        self.start_date = start_date
        self.end_date = end_date
        self.trading_days = []

        # Set report directory for test outputs
        if report_dir is None:
            report_dir = Path(__file__).parent.parent.parent.parent / 'data' / 'test-reports' / 'backtest'
        self.report_dir = Path(report_dir)
        self.report_dir.mkdir(parents=True, exist_ok=True)

        # Load trading config from TEST trading config table
        self.config = self._load_trading_config(start_date)
        self.daily_budget = Decimal(str(self.config.get('daily_capital', 1000.0)))
        assets_config = self.config.get('assets', '["SPY", "QQQ", "DIA"]')
        # Handle both string and list types
        if isinstance(assets_config, str):
            self.assets = json.loads(assets_config)
        else:
            self.assets = assets_config

    def _load_trading_config(self, reference_date: date) -> Dict:
        """Load trading config for a specific date from test tables"""
        self.cursor.execute("""
            SELECT * FROM test_trading_config
            WHERE start_date <= %s
            AND (end_date IS NULL OR end_date >= %s)
            ORDER BY start_date DESC
            LIMIT 1
        """, (reference_date, reference_date))
        row = self.cursor.fetchone()
        if row:
            return dict(row)
        else:
            # Return defaults if no config found
            return {
                'daily_capital': 1000.0,
                'assets': '["SPY", "QQQ", "DIA"]',
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
                'rsi_oversold_threshold': 30.0,
                'rsi_overbought_threshold': 70.0,
                'bollinger_std_multiplier': 2.0,
                'mean_reversion_allocation': 0.4,
                'volatility_adjustment_factor': 0.4,
                'base_volatility': 0.01,
                'min_confidence_threshold': 0.3,
                'confidence_scaling_factor': 0.5
            }

    def close(self):
        self.cursor.close()
        self.conn.close()

    def _calculate_rsi(self, closes: List[float], period: int = 14) -> float:
        """Calculate Relative Strength Index"""
        if len(closes) < period + 1:
            return 50.0

        deltas = np.diff(closes)
        gains = np.where(deltas > 0, deltas, 0.0)
        losses = np.where(deltas < 0, -deltas, 0.0)

        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return float(rsi)

    def _calculate_bollinger_position(self, closes: List[float], period: int = 20, num_std: float = 2.0) -> float:
        """Calculate position within Bollinger Bands (-1 to +1)"""
        if len(closes) < period:
            return 0.0

        recent = closes[-period:]
        sma = np.mean(recent)
        std = np.std(recent)

        if std == 0:
            return 0.0

        upper_band = sma + (std * num_std)
        lower_band = sma - (std * num_std)
        current_price = closes[-1]

        band_width = upper_band - lower_band
        if band_width > 0:
            position = (current_price - sma) / (band_width / 2)
            position = max(-1.0, min(1.0, position))
        else:
            position = 0.0

        return float(position)

    def _calculate_features(self, trade_date: date) -> Dict:
        """Calculate multi-timeframe features for all assets"""
        features_by_asset = {}

        # Get lookback period
        lookback_days = int(self.config.get('lookback_days', 252))
        lookback_start = trade_date - timedelta(days=lookback_days + 30)

        for symbol in self.assets:
            self.cursor.execute("""
                SELECT date, close_price
                FROM test_price_history
                WHERE symbol = %s AND date < %s AND date >= %s
                ORDER BY date ASC
            """, (symbol, trade_date, lookback_start))

            rows = self.cursor.fetchall()
            # Reduced minimum requirement to allow trading with less data
            if len(rows) < 10:
                continue

            closes = [float(row['close_price']) for row in rows]

            # Calculate returns with fallbacks for limited data
            returns_5d = (closes[-1] / closes[-5] - 1) if len(closes) >= 5 else 0
            returns_20d = (closes[-1] / closes[-20] - 1) if len(closes) >= 20 else returns_5d
            returns_60d = (closes[-1] / closes[-60] - 1) if len(closes) >= 60 else returns_20d

            # Volatility - use available data
            daily_returns = np.diff(closes) / closes[:-1]
            if len(daily_returns) >= 20:
                volatility = np.std(daily_returns[-20:])
            elif len(daily_returns) >= 5:
                volatility = np.std(daily_returns[-5:])
            else:
                volatility = 0.01  # Default 1% daily vol

            # SMAs - use available data
            if len(closes) >= 20:
                sma_20 = np.mean(closes[-20:])
            elif len(closes) >= 5:
                sma_20 = np.mean(closes[-5:])
            else:
                sma_20 = closes[-1]

            if len(closes) >= 50:
                sma_50 = np.mean(closes[-50:])
            else:
                sma_50 = sma_20

            price_vs_sma20 = (closes[-1] / sma_20 - 1)
            price_vs_sma50 = (closes[-1] / sma_50 - 1)

            # RSI
            rsi = self._calculate_rsi(closes)

            # Bollinger Bands position
            bb_multiplier = float(self.config.get('bollinger_std_multiplier', 2.0))
            bollinger_position = self._calculate_bollinger_position(closes, num_std=bb_multiplier)

            features_by_asset[symbol] = {
                'returns_5d': returns_5d,
                'returns_20d': returns_20d,
                'returns_60d': returns_60d,
                'volatility': volatility,
                'price_vs_sma20': price_vs_sma20,
                'price_vs_sma50': price_vs_sma50,
                'current_price': closes[-1],
                'rsi': rsi,
                'bollinger_position': bollinger_position
            }

        return features_by_asset

    def _calculate_regime_score(self, features_by_asset: Dict) -> float:
        """Calculate market regime score (-1 to +1, positive = bullish)"""
        regime_scores = []

        for symbol, features in features_by_asset.items():
            momentum_avg = (
                features['returns_5d'] +
                features['returns_20d'] +
                features['returns_60d']
            ) / 3

            asset_regime = (
                momentum_avg * 0.5 +
                features['price_vs_sma20'] * 0.3 +
                features['price_vs_sma50'] * 0.2
            )
            regime_scores.append(asset_regime)

        return sum(regime_scores) / len(regime_scores) if regime_scores else 0

    def _calculate_risk_score(self, features_by_asset: Dict) -> float:
        """Calculate risk score (0-100, higher = riskier)"""
        volatilities = [f['volatility'] for f in features_by_asset.values()]
        avg_vol = sum(volatilities) / len(volatilities) if volatilities else 0

        vol_score = min(100, (avg_vol / 0.02) * 100)

        momentums = [f['returns_60d'] for f in features_by_asset.values()]
        momentum_std = np.std(momentums) if momentums else 0
        correlation_risk = max(0, 30 - momentum_std * 100)

        risk_score = vol_score * 0.7 + correlation_risk * 0.3
        return min(100, max(0, risk_score))

    def _rank_assets(self, features_by_asset: Dict) -> Dict:
        """Rank assets by composite score"""
        scores = {}
        momentum_weight = float(self.config.get('momentum_weight', 0.6))
        price_momentum_weight = float(self.config.get('price_momentum_weight', 0.4))
        rsi_oversold = float(self.config.get('rsi_oversold_threshold', 30.0))
        rsi_overbought = float(self.config.get('rsi_overbought_threshold', 70.0))

        for symbol, features in features_by_asset.items():
            momentum_score = features['returns_60d'] / max(features['volatility'], 0.001)

            # Trend consistency
            all_positive = all(m > 0 for m in [
                features['returns_5d'], features['returns_20d'], features['returns_60d']
            ])
            all_negative = all(m < 0 for m in [
                features['returns_5d'], features['returns_20d'], features['returns_60d']
            ])
            trend_consistency = 1.5 if (all_positive or all_negative) else 1.0

            price_momentum = (features['price_vs_sma20'] + features['price_vs_sma50']) / 2

            # Mean reversion bonus
            rsi = features['rsi']
            bb_position = features['bollinger_position']
            mean_reversion_bonus = 0

            if rsi < rsi_oversold and bb_position < -0.5:
                mean_reversion_bonus = 0.3
            elif rsi < 40 and bb_position < 0:
                mean_reversion_bonus = 0.1
            elif rsi > rsi_overbought and bb_position > 0.5:
                mean_reversion_bonus = -0.2

            composite = (
                momentum_score * momentum_weight * trend_consistency +
                price_momentum * price_momentum_weight +
                mean_reversion_bonus
            )
            scores[symbol] = composite

        return scores

    def _decide_action(self, regime_score: float, risk_score: float, has_holdings: bool) -> tuple:
        """Decide action: BUY, SELL, or HOLD"""
        bullish_threshold = float(self.config.get('regime_bullish_threshold', 0.3))
        bearish_threshold = float(self.config.get('regime_bearish_threshold', -0.3))
        risk_high = float(self.config.get('risk_high_threshold', 70.0))
        risk_medium = float(self.config.get('risk_medium_threshold', 40.0))

        if regime_score < bearish_threshold:
            if has_holdings:
                sell_pct = min(0.7, abs(regime_score) * 0.8)
                return ("SELL", sell_pct, "bearish_regime")
            else:
                return ("HOLD", 0.0, "bearish_no_holdings")
        elif regime_score <= bullish_threshold:
            allocation_neutral = float(self.config.get('allocation_neutral', 0.2))
            if risk_score > 60:
                return ("HOLD", 0.0, "neutral_high_risk")
            else:
                return ("BUY", allocation_neutral, "neutral_cautious")
        else:
            if risk_score > risk_high:
                allocation_pct = float(self.config.get('allocation_high_risk', 0.3))
            elif risk_score > risk_medium:
                allocation_pct = float(self.config.get('allocation_medium_risk', 0.5))
            else:
                allocation_pct = float(self.config.get('allocation_low_risk', 0.8))
            return ("BUY", allocation_pct, "bullish_momentum")

    def _allocate_diversified(self, asset_scores: Dict, total_amount: float) -> Dict:
        """Allocate capital across assets proportionally"""
        positive_scores = {s: max(0, score) for s, score in asset_scores.items()}

        if sum(positive_scores.values()) == 0:
            return {s: 0.0 for s in asset_scores.keys()}

        sorted_assets = sorted(positive_scores.items(), key=lambda x: x[1], reverse=True)
        allocations = {}

        if len(sorted_assets) >= 3 and all(score > 0 for _, score in sorted_assets[:3]):
            total_score = sum(score for _, score in sorted_assets)
            weights = [score / total_score for _, score in sorted_assets]

            allocations[sorted_assets[0][0]] = total_amount * min(0.50, max(0.40, weights[0]))
            allocations[sorted_assets[1][0]] = total_amount * min(0.35, max(0.30, weights[1]))
            allocations[sorted_assets[2][0]] = total_amount * min(0.25, max(0.15, weights[2]))

            total_allocated = sum(allocations.values())
            for symbol in allocations:
                allocations[symbol] = allocations[symbol] * (total_amount / total_allocated)
        elif len(sorted_assets) >= 2 and sorted_assets[1][1] > 0:
            allocations[sorted_assets[0][0]] = total_amount * 0.65
            allocations[sorted_assets[1][0]] = total_amount * 0.35
            if len(sorted_assets) > 2:
                allocations[sorted_assets[2][0]] = 0.0
        else:
            allocations[sorted_assets[0][0]] = total_amount
            for symbol, _ in sorted_assets[1:]:
                allocations[symbol] = 0.0

        return allocations

    def _calculate_confidence(self, regime_score: float, risk_score: float) -> float:
        """Calculate signal confidence (0 to 1)"""
        # Base confidence from regime strength - but use softer scaling
        # With limited data, regime scores are small, so we need to be more lenient
        regime_confidence = min(1.0, abs(regime_score) / 0.3)  # Reduced from 0.5

        # Risk penalty
        risk_penalty = max(0, (risk_score - 40) / 60)

        # Base confidence floor - ensures we can trade even with neutral regimes
        base_confidence = 0.3  # Start with 30% base confidence

        confidence = base_confidence + (regime_confidence * 0.5) - (risk_penalty * 0.3)
        return max(0, min(1.0, confidence))

    def get_trading_days(self) -> List[date]:
        """Get all trading days from TEST price history"""
        self.cursor.execute("""
            SELECT DISTINCT date
            FROM test_price_history
            WHERE date >= %s AND date <= %s
            AND symbol = 'SPY'
            ORDER BY date
        """, (self.start_date, self.end_date))

        days = [row['date'] for row in self.cursor.fetchall()]

        if not days:
            raise Exception(f"No test data found for {self.start_date} to {self.end_date}")

        return days

    def clear_backtest_data(self):
        """Clear existing test data for this date range"""
        # Clear test signals
        self.cursor.execute("""
            DELETE FROM test_daily_signals
            WHERE trade_date >= %s AND trade_date <= %s
        """, (self.start_date, self.end_date))

        # Clear test trades
        self.cursor.execute("""
            DELETE FROM test_trades
            WHERE trade_date >= %s AND trade_date <= %s
        """, (self.start_date, self.end_date))

        # Clear test portfolio
        self.cursor.execute("DELETE FROM test_portfolio")

        # Clear test performance metrics
        self.cursor.execute("""
            DELETE FROM test_performance_metrics
            WHERE date >= %s AND date <= %s
        """, (self.start_date, self.end_date))

        self.conn.commit()

    def generate_signal(self, trade_date: date) -> bool:
        """Generate signal for a specific date using actual trading strategy logic"""
        # Reload config for this date (in case it was tuned)
        self.config = self._load_trading_config(trade_date)

        # Calculate features for all assets
        features_by_asset = self._calculate_features(trade_date)

        if not features_by_asset:
            # Not enough data - skip this day
            return False

        # Calculate regime and risk scores
        regime_score = self._calculate_regime_score(features_by_asset)
        risk_score = self._calculate_risk_score(features_by_asset)

        # Rank assets
        asset_scores = self._rank_assets(features_by_asset)

        # Check current holdings
        self.cursor.execute("SELECT COUNT(*) as cnt FROM test_portfolio WHERE quantity > 0")
        has_holdings = self.cursor.fetchone()['cnt'] > 0

        # Decide action
        action, allocation_pct, signal_type = self._decide_action(regime_score, risk_score, has_holdings)

        # Calculate confidence
        confidence = self._calculate_confidence(regime_score, risk_score)

        # Apply confidence-based position sizing
        min_confidence = float(self.config.get('min_confidence_threshold', 0.3))
        confidence_scaling = float(self.config.get('confidence_scaling_factor', 0.5))

        if action == "BUY" and confidence >= min_confidence:
            # Scale position by confidence
            scaling = 1.0 - confidence_scaling + (confidence_scaling * confidence)
            adjusted_allocation = allocation_pct * scaling
        elif action == "BUY" and confidence < min_confidence:
            # Skip trade due to low confidence
            action = "HOLD"
            signal_type = "low_confidence_skip"
            adjusted_allocation = 0.0
        else:
            adjusted_allocation = allocation_pct

        # Generate allocations
        allocations = {}

        if action == "BUY":
            buy_amount = float(self.daily_budget) * adjusted_allocation
            allocations = self._allocate_diversified(asset_scores, buy_amount)
        elif action == "SELL":
            # Mark negative allocation for sell
            for symbol in self.assets:
                allocations[symbol] = -adjusted_allocation
        else:  # HOLD
            for symbol in self.assets:
                allocations[symbol] = 0.0

        # Prepare features for storage
        features_used = {
            "regime": float(regime_score),
            "risk": float(risk_score),
            "action": action,
            "signal_type": signal_type,
            "allocation_pct": float(adjusted_allocation),
            "confidence_bucket": "high" if confidence >= 0.7 else "medium" if confidence >= 0.5 else "low",
            "assets": {
                symbol: {
                    "returns_5d": float(f["returns_5d"]),
                    "returns_20d": float(f["returns_20d"]),
                    "returns_60d": float(f["returns_60d"]),
                    "volatility": float(f["volatility"]),
                    "score": float(asset_scores.get(symbol, 0)),
                    "rsi": float(f["rsi"]),
                    "bollinger_position": float(f["bollinger_position"])
                }
                for symbol, f in features_by_asset.items()
            }
        }

        # Insert signal into test table
        self.cursor.execute("""
            INSERT INTO test_daily_signals
            (trade_date, allocations, model_type, confidence_score, features_used)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (trade_date) DO UPDATE SET
                allocations = EXCLUDED.allocations,
                model_type = EXCLUDED.model_type,
                confidence_score = EXCLUDED.confidence_score,
                features_used = EXCLUDED.features_used
        """, (
            trade_date,
            json.dumps(allocations),
            'enhanced_regime_based',
            float(confidence),
            json.dumps(features_used)
        ))

        self.conn.commit()
        return True

    def execute_trades(self, trade_date: date) -> bool:
        """Execute trades for a specific date using test tables"""
        # Get signal
        self.cursor.execute("""
            SELECT id, allocations FROM test_daily_signals
            WHERE trade_date = %s
        """, (trade_date,))

        signal = self.cursor.fetchone()
        if not signal:
            return False

        signal_id = signal['id']
        allocations = signal['allocations']

        # Get prices
        self.cursor.execute("""
            SELECT symbol, open_price FROM test_price_history
            WHERE date = %s
        """, (trade_date,))
        prices = {row['symbol']: Decimal(str(row['open_price'])) for row in self.cursor.fetchall()}

        # Execute trades based on allocations
        for symbol, amount in allocations.items():
            if amount > 0 and symbol in prices:
                price = prices[symbol]
                quantity = Decimal(str(amount)) / price

                # Insert trade
                self.cursor.execute("""
                    INSERT INTO test_trades
                    (trade_date, symbol, action, quantity, price, amount, signal_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (trade_date, symbol, 'BUY', float(quantity), float(price), float(amount), signal_id))

                # Update portfolio
                self.cursor.execute("""
                    INSERT INTO test_portfolio (symbol, quantity, avg_cost)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (symbol) DO UPDATE SET
                        quantity = test_portfolio.quantity + EXCLUDED.quantity,
                        avg_cost = (test_portfolio.avg_cost * test_portfolio.quantity +
                                    EXCLUDED.avg_cost * EXCLUDED.quantity) /
                                   (test_portfolio.quantity + EXCLUDED.quantity),
                        last_updated = CURRENT_TIMESTAMP
                """, (symbol, float(quantity), float(price)))

        self.conn.commit()
        return True

    def calculate_daily_metrics(self, trade_date: date) -> Dict:
        """Calculate performance metrics using test tables"""
        # Get current portfolio
        self.cursor.execute("SELECT symbol, quantity, avg_cost FROM test_portfolio")
        positions = self.cursor.fetchall()

        # Get closing prices
        self.cursor.execute("""
            SELECT symbol, close_price
            FROM test_price_history
            WHERE date = %s
        """, (trade_date,))
        prices = {row['symbol']: Decimal(str(row['close_price'])) for row in self.cursor.fetchall()}

        # Calculate portfolio value
        portfolio_value = Decimal(0)
        for pos in positions:
            symbol = pos['symbol']
            qty = Decimal(str(pos['quantity']))
            current_price = prices.get(symbol, Decimal(0))
            portfolio_value += qty * current_price

        # Get total injected capital
        self.cursor.execute("""
            SELECT COALESCE(SUM(amount), 0) as total_injected
            FROM test_trades
            WHERE trade_date >= %s AND trade_date <= %s AND action = 'BUY'
        """, (self.start_date, trade_date))
        result = self.cursor.fetchone()
        cash_injected = Decimal(str(result['total_injected']))

        # Cash from sells
        self.cursor.execute("""
            SELECT COALESCE(SUM(amount), 0) as total_proceeds
            FROM test_trades
            WHERE trade_date >= %s AND trade_date <= %s AND action = 'SELL'
        """, (self.start_date, trade_date))
        result = self.cursor.fetchone()
        cash_from_sells = Decimal(str(result['total_proceeds']))

        total_value = portfolio_value + cash_from_sells

        # Daily return
        self.cursor.execute("""
            SELECT total_value
            FROM test_performance_metrics
            WHERE date >= %s AND date < %s
            ORDER BY date DESC
            LIMIT 1
        """, (self.start_date, trade_date))
        prev_result = self.cursor.fetchone()

        if prev_result:
            prev_value = Decimal(str(prev_result['total_value']))
            daily_return = ((total_value - prev_value) / prev_value * 100) if prev_value > 0 else Decimal(0)
        else:
            daily_return = Decimal(0)

        cumulative_return = ((total_value - cash_injected) / cash_injected * 100) if cash_injected > 0 else Decimal(0)

        return {
            'date': trade_date,
            'portfolio_value': portfolio_value,
            'cash_balance': cash_from_sells,
            'total_value': total_value,
            'daily_return': daily_return,
            'cumulative_return': cumulative_return
        }

    def save_daily_metrics(self, metrics: Dict):
        """Save daily metrics to test_performance_metrics table"""
        self.cursor.execute("""
            INSERT INTO test_performance_metrics
            (date, portfolio_value, cash_balance, total_value, daily_return, cumulative_return)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (date) DO UPDATE SET
                portfolio_value = EXCLUDED.portfolio_value,
                cash_balance = EXCLUDED.cash_balance,
                total_value = EXCLUDED.total_value,
                daily_return = EXCLUDED.daily_return,
                cumulative_return = EXCLUDED.cumulative_return
        """, (
            metrics['date'],
            metrics['portfolio_value'],
            metrics['cash_balance'],
            metrics['total_value'],
            metrics['daily_return'],
            metrics['cumulative_return']
        ))
        self.conn.commit()

    def generate_report(self) -> str:
        """Generate and save report, return filepath"""
        report_lines = []

        report_lines.append(f"\n{'='*60}")
        report_lines.append(f"E2E BACKTEST REPORT: {self.start_date} to {self.end_date}")
        report_lines.append(f"{'='*60}\n")

        # Get metrics
        self.cursor.execute("""
            SELECT * FROM test_performance_metrics
            WHERE date >= %s AND date <= %s
            ORDER BY date
        """, (self.start_date, self.end_date))
        metrics = self.cursor.fetchall()

        if not metrics:
            report_lines.append("No performance data generated")
            return self._save_report(report_lines)

        total_days = len(metrics)
        final_value = Decimal(str(metrics[-1]['total_value']))

        self.cursor.execute("""
            SELECT SUM(amount) as total_injected
            FROM test_trades
            WHERE trade_date >= %s AND trade_date <= %s AND action = 'BUY'
        """, (self.start_date, self.end_date))
        result = self.cursor.fetchone()
        total_injected = Decimal(str(result['total_injected'])) if result['total_injected'] else Decimal(0)

        total_return = final_value - total_injected
        total_return_pct = (total_return / total_injected * 100) if total_injected > 0 else Decimal(0)

        report_lines.append(f"Trading Days: {total_days}")
        report_lines.append(f"Capital Injected: ${total_injected:,.2f}")
        report_lines.append(f"Final Portfolio Value: ${final_value:,.2f}")
        report_lines.append(f"Total Return: ${total_return:,.2f} ({total_return_pct:+.2f}%)")
        report_lines.append(f"\n{'='*60}\n")

        return self._save_report(report_lines)

    def _save_report(self, report_lines: list) -> str:
        """Save report to file"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"e2e_backtest_{self.start_date}_to_{self.end_date}_{timestamp}.txt"
        filepath = self.report_dir / filename

        with open(filepath, 'w') as f:
            f.write('\n'.join(report_lines))

        return str(filepath)

    def run(self) -> Dict:
        """Run complete backtest, return summary"""
        self.trading_days = self.get_trading_days()
        self.clear_backtest_data()

        for trade_date in self.trading_days:
            if not self.generate_signal(trade_date):
                continue
            if not self.execute_trades(trade_date):
                continue
            metrics = self.calculate_daily_metrics(trade_date)
            self.save_daily_metrics(metrics)

        report_file = self.generate_report()

        return {
            'start_date': self.start_date,
            'end_date': self.end_date,
            'trading_days': len(self.trading_days),
            'report_file': report_file
        }
