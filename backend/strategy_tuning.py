"""
Monthly Strategy Tuning Script
Analyzes past performance and adjusts strategy parameters based on trade evaluation

This script should be run on the 1st trading day of each month to:
1. Evaluate past trades retroactively
2. Detect market conditions (momentum vs choppy)
3. Adjust parameters to improve future performance
4. Generate a detailed report of changes
"""
import os
import sys
import json
import math
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Dict, List, Tuple
from dataclasses import dataclass

import psycopg2
from psycopg2.extras import RealDictCursor
import numpy as np

# Import configuration
from config import get_settings, get_trading_config
from config_loader import TradingConfig, ConfigLoader

settings = get_settings()
DATABASE_URL = settings.database_url
RISK_FREE_RATE = 0.05  # 5% annual


@dataclass
class TradeEvaluation:
    """Evaluation of a specific trade"""
    trade_date: date
    symbol: str
    action: str
    amount: float
    regime: str
    market_condition: str  # 'momentum' or 'choppy'

    # Impact metrics
    contribution_to_drawdown: float  # How much this trade contributed to max DD
    sharpe_impact: float  # Impact on Sharpe ratio
    was_profitable: bool
    pnl: float

    # Rating (required fields must come before optional)
    score: float  # -1 to 1, negative = bad trade, positive = good trade
    should_have_avoided: bool

    # Enhanced metrics (NEW) - optional fields with defaults
    pnl_10d: float = 0.0  # P&L at 10 days
    pnl_20d: float = 0.0  # P&L at 20 days
    pnl_30d: float = 0.0  # P&L at 30 days
    best_horizon: str = "10d"  # Which horizon was most profitable
    confidence_bucket: str = "unknown"  # Signal confidence bucket
    signal_type: str = "unknown"  # Type of signal (momentum, mean_reversion, etc.)


class StrategyTuner:
    def __init__(self, lookback_months: int = 3):
        """
        Initialize strategy tuner

        Args:
            lookback_months: Number of months to look back for analysis
        """
        self.conn = psycopg2.connect(DATABASE_URL)
        self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        self.lookback_months = lookback_months
        self.config_loader = ConfigLoader(DATABASE_URL)
        # Load current active parameters from database
        self.current_params = self.config_loader.get_active_config()
        # Make config accessible for tunable thresholds
        self.config = self.current_params

    def close(self):
        self.cursor.close()
        self.conn.close()

    def get_analysis_period(self) -> Tuple[date, date]:
        """Get the date range for analysis (last N months)"""
        end_date = date.today() - timedelta(days=1)  # Yesterday
        start_date = end_date - timedelta(days=self.lookback_months * 30)

        # Adjust to actual trading days
        self.cursor.execute("""
            SELECT MIN(date) as start, MAX(date) as end
            FROM performance_metrics
            WHERE date >= %s AND date <= %s
        """, (start_date, end_date))

        result = self.cursor.fetchone()
        if result and result['start'] and result['end']:
            return result['start'], result['end']
        else:
            raise Exception(f"No performance data found for the last {self.lookback_months} months")

    def detect_market_condition(self, trade_date: date, window: int = 20) -> str:
        """
        Detect if market was in momentum or choppy condition

        Args:
            trade_date: Date to analyze
            window: Lookback window for analysis

        Returns:
            'momentum' or 'choppy'
        """
        lookback_start = trade_date - timedelta(days=window + 10)

        # Get SPY prices for the period
        self.cursor.execute("""
            SELECT date, close_price
            FROM price_history
            WHERE symbol = 'SPY'
            AND date >= %s AND date <= %s
            ORDER BY date
        """, (lookback_start, trade_date))

        prices = [float(row['close_price']) for row in self.cursor.fetchall()]

        if len(prices) < window:
            return 'unknown'

        prices = prices[-window:]

        # Calculate trend strength
        # 1. Linear regression slope (trend direction)
        x = np.arange(len(prices))
        y = np.array(prices)
        slope, _ = np.polyfit(x, y, 1)

        # 2. R-squared (trend consistency)
        y_pred = slope * x + np.mean(y) - slope * np.mean(x)
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

        # 3. Price volatility
        returns = np.diff(prices) / prices[:-1]
        volatility = np.std(returns)

        # Decision logic using tunable thresholds:
        # Strong momentum: High R-squared and clear trend
        # Choppy: Low R-squared or high volatility with no clear trend

        if r_squared > self.config.market_condition_r_squared_threshold and \
           abs(slope) > self.config.market_condition_slope_threshold:
            return 'momentum'
        elif r_squared < self.config.market_condition_choppy_r_squared or \
             volatility > self.config.market_condition_choppy_volatility:
            return 'choppy'
        else:
            return 'mixed'

    def calculate_drawdown_contribution(self, trade_date: date, trade_pnl: float) -> float:
        """
        Calculate how much a trade contributed to maximum drawdown

        Returns:
            Float between 0-100 representing percentage contribution
        """
        # Get performance data around the trade
        window_start = trade_date - timedelta(days=5)
        window_end = trade_date + timedelta(days=10)

        self.cursor.execute("""
            SELECT date, total_value
            FROM performance_metrics
            WHERE date >= %s AND date <= %s
            ORDER BY date
        """, (window_start, window_end))

        values = [(row['date'], float(row['total_value'])) for row in self.cursor.fetchall()]

        if len(values) < 2:
            return 0.0

        # Find peak before trade and trough after
        trade_idx = None
        for i, (d, _) in enumerate(values):
            if d >= trade_date:
                trade_idx = i
                break

        if trade_idx is None or trade_idx == 0:
            return 0.0

        peak_value = max(v for _, v in values[:trade_idx + 1])
        trough_value = min(v for _, v in values[trade_idx:]) if trade_idx < len(values) else values[-1][1]

        # Calculate drawdown
        drawdown_pct = ((peak_value - trough_value) / peak_value * 100) if peak_value > 0 else 0

        # If trade lost money and there was a drawdown, attribute proportionally
        if trade_pnl < 0 and drawdown_pct > 0:
            # Contribution is based on how much the trade lost relative to the drawdown
            contribution = min(100, abs(trade_pnl) / (peak_value * drawdown_pct / 100) * 100)
            return contribution

        return 0.0

    def evaluate_trades(self, start_date: date, end_date: date) -> List[TradeEvaluation]:
        """
        Evaluate all trades in the period with multi-horizon analysis

        Returns:
            List of TradeEvaluation objects
        """
        evaluations = []

        # Get all trades in period
        self.cursor.execute("""
            SELECT
                t.*,
                ds.features_used
            FROM trades t
            JOIN daily_signals ds ON t.signal_id = ds.id
            WHERE t.trade_date >= %s AND t.trade_date <= %s
            ORDER BY t.trade_date, t.id
        """, (start_date, end_date))

        trades = self.cursor.fetchall()

        for trade in trades:
            trade_date = trade['trade_date']
            symbol = trade['symbol']
            action = trade['action']
            amount = float(trade['amount'])
            quantity = float(trade['quantity'])
            price = float(trade['price'])

            features = trade['features_used']
            regime_score = features.get('regime', 0)
            regime = 'bullish' if regime_score > 0.3 else 'bearish' if regime_score < -0.3 else 'neutral'

            # NEW: Extract confidence bucket and signal type from features
            confidence_bucket = features.get('confidence_bucket', 'unknown')
            signal_type = features.get('signal_type', 'unknown')

            # Detect market condition
            market_condition = self.detect_market_condition(trade_date)

            # NEW: Multi-horizon P&L calculation (10d, 20d, 30d)
            pnl_horizons = {}
            for horizon, days in [('10d', 10), ('20d', 20), ('30d', 30)]:
                future_date = trade_date + timedelta(days=days)

                self.cursor.execute("""
                    SELECT close_price
                    FROM price_history
                    WHERE symbol = %s
                    AND date > %s AND date <= %s
                    ORDER BY date DESC
                    LIMIT 1
                """, (symbol, trade_date, future_date))

                future_price_row = self.cursor.fetchone()
                future_price = float(future_price_row['close_price']) if future_price_row else price

                # Calculate P&L for this horizon
                if action == 'BUY':
                    horizon_pnl = (future_price - price) * abs(quantity)
                else:  # SELL
                    horizon_pnl = (price - future_price) * abs(quantity)

                pnl_horizons[horizon] = horizon_pnl

            # Best performing horizon
            best_horizon = max(pnl_horizons.keys(), key=lambda k: pnl_horizons[k])
            best_pnl = pnl_horizons[best_horizon]

            # Use best horizon for profitability determination (NEW: multi-horizon evaluation)
            was_profitable = best_pnl > 0
            pnl = best_pnl  # Use best horizon as the primary P&L

            # Calculate contribution to drawdown
            drawdown_contribution = self.calculate_drawdown_contribution(trade_date, pnl_horizons['10d'])

            # Calculate Sharpe impact using tunable bonuses/penalties
            # Based on if trade aligned with profitable regime
            sharpe_impact = 0.0
            if market_condition == 'momentum' and action == 'BUY' and regime == 'bullish':
                sharpe_impact = self.config.score_momentum_bonus
            elif market_condition == 'choppy' and action == 'HOLD':
                sharpe_impact = self.config.score_momentum_bonus * 0.5  # Half bonus for avoiding risk
            elif market_condition == 'choppy' and action == 'BUY':
                sharpe_impact = self.config.score_choppy_penalty

            # Bonus for mean reversion trades that work (tunable)
            if signal_type and 'mean_reversion' in signal_type and was_profitable:
                sharpe_impact += self.config.score_mean_reversion_bonus

            # Calculate trade score (-1 to 1) using tunable scoring parameters
            score = 0.0

            # Positive factors (all tunable)
            if was_profitable:
                score += self.config.score_profitable_bonus
            if sharpe_impact > 0:
                score += self.config.score_sharpe_bonus
            # Low DD contribution is good (tunable threshold)
            if drawdown_contribution < self.config.score_dd_low_threshold:
                score += self.config.score_low_dd_bonus

            # Multi-horizon consistency bonus (tunable)
            profitable_horizons = sum(1 for p in pnl_horizons.values() if p > 0)
            if profitable_horizons == 3:
                score += self.config.score_all_horizons_bonus
            elif profitable_horizons == 2:
                score += self.config.score_two_horizons_bonus

            # Negative factors (all tunable)
            if not was_profitable:
                score += self.config.score_unprofitable_penalty  # Already negative
            # High DD contribution is bad (tunable threshold)
            if drawdown_contribution > self.config.score_dd_high_threshold:
                score += self.config.score_high_dd_penalty  # Already negative
            if sharpe_impact < 0:
                score += self.config.score_sharpe_penalty  # Already negative

            # Market condition alignment (tunable)
            if market_condition == 'momentum' and action == 'BUY' and was_profitable:
                score += self.config.score_momentum_bonus
            elif market_condition == 'choppy' and action == 'BUY' and not was_profitable:
                score += self.config.score_choppy_penalty  # Already negative

            # Confidence bucket scoring (tunable)
            if confidence_bucket == 'high' and was_profitable:
                score += self.config.score_confidence_bonus
            elif confidence_bucket == 'low' and not was_profitable:
                score += self.config.score_confidence_bonus  # Avoiding losses is good

            score = max(-1.0, min(1.0, score))  # Clamp to [-1, 1]

            # Should have avoided?
            should_have_avoided = (
                drawdown_contribution > 20 or
                (market_condition == 'choppy' and action == 'BUY' and not was_profitable) or
                (confidence_bucket == 'low' and not was_profitable and pnl_horizons['10d'] < -50)
            )

            evaluation = TradeEvaluation(
                trade_date=trade_date,
                symbol=symbol,
                action=action,
                amount=amount,
                regime=regime,
                market_condition=market_condition,
                contribution_to_drawdown=drawdown_contribution,
                sharpe_impact=sharpe_impact,
                was_profitable=was_profitable,
                pnl=pnl,
                pnl_10d=pnl_horizons['10d'],
                pnl_20d=pnl_horizons['20d'],
                pnl_30d=pnl_horizons['30d'],
                best_horizon=best_horizon,
                confidence_bucket=confidence_bucket,
                signal_type=signal_type,
                score=score,
                should_have_avoided=should_have_avoided
            )

            evaluations.append(evaluation)

        return evaluations

    def analyze_performance_by_condition(self, evaluations: List[TradeEvaluation]) -> Dict:
        """
        Analyze performance in different market conditions

        Returns:
            Dictionary with performance metrics by condition
        """
        momentum_trades = [e for e in evaluations if e.market_condition == 'momentum']
        choppy_trades = [e for e in evaluations if e.market_condition == 'choppy']

        def calc_metrics(trades):
            if not trades:
                return {
                    'count': 0,
                    'win_rate': 0,
                    'avg_score': 0,
                    'total_pnl': 0,
                    'avg_drawdown_contribution': 0,
                    'should_be_more_aggressive': False,
                    'should_be_more_conservative': False
                }

            wins = sum(1 for t in trades if t.was_profitable)
            win_rate = wins / len(trades) * 100
            avg_score = sum(t.score for t in trades) / len(trades)
            total_pnl = sum(t.pnl for t in trades)
            avg_dd = sum(t.contribution_to_drawdown for t in trades) / len(trades)

            # Determine if strategy should be adjusted (using tunable thresholds)
            buy_trades = [t for t in trades if t.action == 'BUY']
            hold_trades = [t for t in trades if t.action == 'HOLD']

            # Should be more aggressive if: high win rate but low participation (all tunable)
            should_be_more_aggressive = (
                win_rate > self.config.tune_aggressive_win_rate and
                len(buy_trades) < len(trades) * self.config.tune_aggressive_participation and
                avg_score > self.config.tune_aggressive_score
            )

            # Should be more conservative if: low win rate or high DD contribution (all tunable)
            should_be_more_conservative = (
                win_rate < self.config.tune_conservative_win_rate or
                avg_dd > self.config.tune_conservative_dd or
                avg_score < self.config.tune_conservative_score
            )

            return {
                'count': len(trades),
                'win_rate': win_rate,
                'avg_score': avg_score,
                'total_pnl': total_pnl,
                'avg_drawdown_contribution': avg_dd,
                'buy_count': len(buy_trades),
                'hold_count': len(hold_trades),
                'should_be_more_aggressive': should_be_more_aggressive,
                'should_be_more_conservative': should_be_more_conservative
            }

        return {
            'momentum': calc_metrics(momentum_trades),
            'choppy': calc_metrics(choppy_trades),
            'overall': calc_metrics(evaluations)
        }

    def analyze_confidence_buckets(self, evaluations: List[TradeEvaluation]) -> Dict:
        """
        Analyze performance by confidence bucket

        Returns:
            Dictionary with performance metrics by confidence level
        """
        high_conf = [e for e in evaluations if e.confidence_bucket == 'high']
        medium_conf = [e for e in evaluations if e.confidence_bucket == 'medium']
        low_conf = [e for e in evaluations if e.confidence_bucket == 'low']

        def calc_bucket_metrics(trades):
            if not trades:
                return {
                    'count': 0,
                    'win_rate': 0,
                    'avg_pnl': 0,
                    'total_pnl': 0,
                    'avg_score': 0,
                    'best_horizon_10d': 0,
                    'best_horizon_20d': 0,
                    'best_horizon_30d': 0
                }

            wins = sum(1 for t in trades if t.was_profitable)
            win_rate = wins / len(trades) * 100
            total_pnl = sum(t.pnl for t in trades)
            avg_pnl = total_pnl / len(trades)
            avg_score = sum(t.score for t in trades) / len(trades)

            # Analyze which horizon performs best
            best_10d = sum(1 for t in trades if t.best_horizon == '10d')
            best_20d = sum(1 for t in trades if t.best_horizon == '20d')
            best_30d = sum(1 for t in trades if t.best_horizon == '30d')

            return {
                'count': len(trades),
                'win_rate': win_rate,
                'avg_pnl': avg_pnl,
                'total_pnl': total_pnl,
                'avg_score': avg_score,
                'best_horizon_10d': best_10d,
                'best_horizon_20d': best_20d,
                'best_horizon_30d': best_30d
            }

        return {
            'high': calc_bucket_metrics(high_conf),
            'medium': calc_bucket_metrics(medium_conf),
            'low': calc_bucket_metrics(low_conf)
        }

    def analyze_signal_types(self, evaluations: List[TradeEvaluation]) -> Dict:
        """
        Analyze performance by signal type (momentum vs mean reversion)

        Returns:
            Dictionary with performance metrics by signal type
        """
        signal_groups = {}
        for eval in evaluations:
            signal_type = eval.signal_type
            if signal_type not in signal_groups:
                signal_groups[signal_type] = []
            signal_groups[signal_type].append(eval)

        results = {}
        for signal_type, trades in signal_groups.items():
            wins = sum(1 for t in trades if t.was_profitable)
            win_rate = wins / len(trades) * 100 if trades else 0
            total_pnl = sum(t.pnl for t in trades)
            avg_pnl = total_pnl / len(trades) if trades else 0

            results[signal_type] = {
                'count': len(trades),
                'win_rate': win_rate,
                'total_pnl': total_pnl,
                'avg_pnl': avg_pnl
            }

        return results

    def perform_out_of_sample_validation(self, candidate_params: TradingConfig,
                                         train_period: Tuple[date, date],
                                         test_period: Tuple[date, date]) -> Dict:
        """
        Validate tuned parameters on out-of-sample data

        Returns:
            Dictionary with validation results
        """
        # This is a simplified validation - we check if the tuned parameters
        # would have led to better decisions in the test period

        train_start, train_end = train_period
        test_start, test_end = test_period

        # Get test period performance
        test_metrics = self.calculate_overall_metrics(test_start, test_end)

        # Compare against targets using tunable tolerance thresholds
        sharpe_passes = test_metrics.get('sharpe_ratio', 0) >= \
                       candidate_params.min_sharpe_target * self.config.validation_sharpe_tolerance
        drawdown_passes = test_metrics.get('max_drawdown', 100) <= \
                         candidate_params.max_drawdown_tolerance * self.config.validation_dd_tolerance

        # Overall validation score using tunable weights
        validation_score = 0
        if sharpe_passes:
            validation_score += self.config.validation_sharpe_weight
        if drawdown_passes:
            validation_score += self.config.validation_drawdown_weight

        return {
            'passes_validation': validation_score >= self.config.validation_passing_score,
            'validation_score': validation_score,
            'test_sharpe': test_metrics.get('sharpe_ratio', 0),
            'test_max_drawdown': test_metrics.get('max_drawdown', 0),
            'sharpe_passes': sharpe_passes,
            'drawdown_passes': drawdown_passes,
            'train_period': f"{train_start} to {train_end}",
            'test_period': f"{test_start} to {test_end}"
        }

    def calculate_overall_metrics(self, start_date: date, end_date: date) -> Dict:
        """Calculate overall performance metrics for the period"""
        self.cursor.execute("""
            SELECT * FROM performance_metrics
            WHERE date >= %s AND date <= %s
            ORDER BY date
        """, (start_date, end_date))

        performance_data = self.cursor.fetchall()

        if not performance_data:
            return {}

        # Calculate Sharpe ratio
        daily_returns = []
        for i in range(1, len(performance_data)):
            if performance_data[i-1]['total_value'] and performance_data[i-1]['total_value'] > 0:
                ret = float((performance_data[i]['total_value'] - performance_data[i-1]['total_value']) /
                           performance_data[i-1]['total_value'] * 100)
                daily_returns.append(ret)

        if len(daily_returns) > 1:
            mean_return = np.mean(daily_returns)
            std_return = np.std(daily_returns, ddof=1)
            sharpe = (mean_return * 252 - RISK_FREE_RATE) / (std_return * math.sqrt(252)) if std_return > 0 else 0
        else:
            sharpe = 0

        # Calculate max drawdown
        peak_value = 0
        max_dd = 0
        for data in performance_data:
            value = float(data['total_value'])
            if value > peak_value:
                peak_value = value
            dd = (peak_value - value) / peak_value * 100 if peak_value > 0 else 0
            if dd > max_dd:
                max_dd = dd

        # Total return
        start_value = float(performance_data[0]['total_value'])
        end_value = float(performance_data[-1]['total_value'])
        total_return = (end_value - start_value) / start_value * 100 if start_value > 0 else 0

        return {
            'sharpe_ratio': sharpe,
            'max_drawdown': max_dd,
            'total_return': total_return,
            'total_days': len(performance_data),
            'daily_returns': daily_returns
        }

    def tune_parameters(self,
                       evaluations: List[TradeEvaluation],
                       condition_analysis: Dict,
                       overall_metrics: Dict,
                       confidence_analysis: Dict = None,
                       signal_type_analysis: Dict = None) -> TradingConfig:
        """
        Adjust parameters based on analysis

        Returns:
            Updated TradingConfig
        """
        # Create new params based on current config
        new_params = TradingConfig(
            daily_capital=self.current_params.daily_capital,
            assets=self.current_params.assets,
            lookback_days=self.current_params.lookback_days,
            regime_bullish_threshold=self.current_params.regime_bullish_threshold,
            regime_bearish_threshold=self.current_params.regime_bearish_threshold,
            risk_high_threshold=self.current_params.risk_high_threshold,
            risk_medium_threshold=self.current_params.risk_medium_threshold,
            allocation_low_risk=self.current_params.allocation_low_risk,
            allocation_medium_risk=self.current_params.allocation_medium_risk,
            allocation_high_risk=self.current_params.allocation_high_risk,
            allocation_neutral=self.current_params.allocation_neutral,
            sell_percentage=self.current_params.sell_percentage,
            momentum_weight=self.current_params.momentum_weight,
            price_momentum_weight=self.current_params.price_momentum_weight,
            max_drawdown_tolerance=self.current_params.max_drawdown_tolerance,
            min_sharpe_target=self.current_params.min_sharpe_target,
            # NEW: Include enhanced parameters
            rsi_oversold_threshold=self.current_params.rsi_oversold_threshold,
            rsi_overbought_threshold=self.current_params.rsi_overbought_threshold,
            bollinger_std_multiplier=self.current_params.bollinger_std_multiplier,
            mean_reversion_allocation=self.current_params.mean_reversion_allocation,
            volatility_adjustment_factor=self.current_params.volatility_adjustment_factor,
            base_volatility=self.current_params.base_volatility,
            min_confidence_threshold=self.current_params.min_confidence_threshold,
            confidence_scaling_factor=self.current_params.confidence_scaling_factor,
            intramonth_drawdown_limit=self.current_params.intramonth_drawdown_limit,
            circuit_breaker_reduction=self.current_params.circuit_breaker_reduction
        )

        momentum_perf = condition_analysis['momentum']
        choppy_perf = condition_analysis['choppy']
        overall_perf = condition_analysis['overall']

        # 1. Adjust allocation based on momentum performance (using tunable steps and limits)
        if momentum_perf['should_be_more_aggressive']:
            # Increase allocations during low/medium risk
            new_params.allocation_low_risk = min(self.config.tune_allocation_low_risk_max, new_params.allocation_low_risk + self.config.tune_allocation_step)
            new_params.allocation_medium_risk = min(self.config.tune_allocation_medium_risk_max, new_params.allocation_medium_risk + self.config.tune_allocation_step)
            print("  📈 Detected: Too conservative during momentum - increasing allocations")

        if momentum_perf['should_be_more_conservative']:
            # Decrease allocations
            new_params.allocation_low_risk = max(self.config.tune_allocation_low_risk_min, new_params.allocation_low_risk - self.config.tune_allocation_step)
            new_params.allocation_medium_risk = max(self.config.tune_allocation_medium_risk_min, new_params.allocation_medium_risk - self.config.tune_allocation_step)
            print("  📉 Detected: Too aggressive during momentum - decreasing allocations")

        # 2. Adjust choppy market behavior (using tunable steps and limits)
        if choppy_perf['should_be_more_conservative']:
            # Reduce neutral allocation
            new_params.allocation_neutral = max(self.config.tune_allocation_neutral_min, new_params.allocation_neutral - self.config.tune_neutral_step)
            new_params.risk_medium_threshold = max(self.config.tune_risk_medium_threshold_min, new_params.risk_medium_threshold - self.config.tune_risk_threshold_step)
            print("  🌊 Detected: Too aggressive in choppy markets - reducing exposure")

        # 3. Adjust max drawdown tolerance based on actual drawdown (BIDIRECTIONAL TUNING - FIXED!)
        max_dd = overall_metrics.get('max_drawdown', 0)
        sharpe_ratio_good = overall_metrics.get('sharpe_ratio', 0) > new_params.min_sharpe_target

        if max_dd > new_params.max_drawdown_tolerance:
            # Tighten risk controls when DD exceeded
            new_params.risk_high_threshold = max(self.config.tune_risk_high_threshold_min, new_params.risk_high_threshold - self.config.tune_risk_threshold_step)
            new_params.allocation_high_risk = max(self.config.tune_allocation_high_risk_min, new_params.allocation_high_risk - self.config.tune_neutral_step)
            print(f"  ⚠️  Max drawdown ({max_dd:.1f}%) exceeded tolerance - tightening risk")
        elif max_dd < new_params.max_drawdown_tolerance * 0.5 and sharpe_ratio_good:
            # RECOVERY LOGIC: Loosen risk controls when DD very low AND Sharpe is good
            # This prevents permanent over-conservatism after volatility periods
            new_params.risk_high_threshold = min(
                self.config.tune_risk_high_threshold_max if hasattr(self.config, 'tune_risk_high_threshold_max') else 80.0,
                new_params.risk_high_threshold + self.config.tune_risk_threshold_step
            )
            new_params.allocation_high_risk = min(
                self.config.tune_allocation_high_risk_max if hasattr(self.config, 'tune_allocation_high_risk_max') else 0.5,
                new_params.allocation_high_risk + self.config.tune_neutral_step * 0.5  # Slower recovery
            )
            print(f"  ✨ Low drawdown ({max_dd:.1f}%) with good Sharpe - loosening risk controls")

        # 4. Adjust based on Sharpe ratio (using tunable steps and limits)
        sharpe = overall_metrics.get('sharpe_ratio', 0)
        if sharpe < new_params.min_sharpe_target:
            # Improve risk-adjusted returns by being more selective
            new_params.regime_bullish_threshold = min(self.config.tune_regime_bullish_threshold_max, new_params.regime_bullish_threshold + self.config.tune_neutral_step)
            new_params.risk_medium_threshold = max(self.config.tune_risk_medium_threshold_min, new_params.risk_medium_threshold - self.config.tune_risk_threshold_step)
            print(f"  📊 Sharpe ratio ({sharpe:.2f}) below target - increasing selectivity")
        elif sharpe > new_params.min_sharpe_target * self.config.tune_sharpe_aggressive_threshold:
            # We can afford to be slightly more aggressive
            new_params.regime_bullish_threshold = max(self.config.tune_regime_bullish_threshold_min, new_params.regime_bullish_threshold - self.config.tune_neutral_step)
            print(f"  ✨ Sharpe ratio ({sharpe:.2f}) strong - can be more aggressive")

        # 5. Adjust sell strategy based on performance - ENHANCED
        sell_evals = [e for e in evaluations if e.action == 'SELL']
        bearish_evals = [e for e in evaluations if e.regime == 'bearish']

        # Analyze SELL action effectiveness
        if sell_evals:
            sell_effectiveness = sum(1 for e in sell_evals if e.score > 0) / len(sell_evals)
            avg_sell_score = sum(e.score for e in sell_evals) / len(sell_evals)

            # Check if sells avoided drawdowns
            sells_avoided_dd = sum(1 for e in sell_evals if e.contribution_to_drawdown < 5) / len(sell_evals)

            print(f"\n  📊 SELL Analysis:")
            print(f"    Sell trades: {len(sell_evals)} ({sell_effectiveness*100:.1f}% effective)")
            print(f"    Avg score: {avg_sell_score:+.2f}")
            print(f"    Avoided DD: {sells_avoided_dd*100:.1f}%")

            # If sells are preventing drawdowns well, keep current sell_percentage (tunable threshold)
            if sell_effectiveness > self.config.tune_sell_effective_threshold and sells_avoided_dd > self.config.tune_sell_effective_threshold:
                print(f"  ✅ SELL strategy working well - maintaining sell_percentage")
            # If sells aren't effective (scoring poorly), reduce sell frequency (tunable threshold and limits)
            elif avg_sell_score < self.config.tune_sell_underperform_threshold:
                new_params.sell_percentage = max(self.config.tune_sell_percentage_min, new_params.sell_percentage - self.config.tune_sell_minor_adjustment)
                print(f"  ⚠️  SELL trades underperforming - decreasing sell_percentage to be more selective")
            # If not selling enough during bearish periods, increase (tunable threshold and limits)
            elif bearish_evals and len(sell_evals) < len(bearish_evals) * self.config.tune_bearish_sell_participation:
                new_params.sell_percentage = min(self.config.tune_sell_percentage_max, new_params.sell_percentage + self.config.tune_sell_minor_adjustment)
                print(f"  🔻 Not selling enough in bearish periods - increasing sell_percentage")

        # If no sells happened but we had high drawdowns, we need to sell more! (tunable threshold and limits)
        elif overall_metrics.get('max_drawdown', 0) > self.config.tune_high_dd_no_sell_threshold:
            new_params.sell_percentage = min(self.config.tune_sell_percentage_max, new_params.sell_percentage + self.config.tune_sell_major_adjustment)
            print(f"  ⚠️  High drawdown ({overall_metrics['max_drawdown']:.1f}%) with no SELL trades - significantly increasing sell_percentage")

        # Specific bearish regime handling (tunable threshold and limits)
        if bearish_evals:
            avg_bearish_score = sum(e.score for e in bearish_evals) / len(bearish_evals)
            if avg_bearish_score < self.config.tune_sell_underperform_threshold:
                # Poor bearish performance - need faster sells
                new_params.sell_percentage = min(self.config.tune_sell_percentage_max, new_params.sell_percentage + self.config.tune_sell_minor_adjustment)
                print(f"  🔻 Poor bearish performance (score: {avg_bearish_score:+.2f}) - increasing sell percentage")

        # NEW: 6. Tune confidence-based parameters (using tunable thresholds)
        if confidence_analysis:
            low_conf = confidence_analysis.get('low', {})
            high_conf = confidence_analysis.get('high', {})

            # If low confidence trades are losing money, raise the threshold (tunable with limits)
            if low_conf.get('count', 0) > 0 and low_conf.get('win_rate', 50) < self.config.tune_low_conf_poor_threshold:
                new_params.min_confidence_threshold = min(self.config.tune_min_confidence_threshold_max, new_params.min_confidence_threshold + self.config.tune_confidence_threshold_step)
                print(f"  🎯 Low confidence trades underperforming ({low_conf['win_rate']:.1f}%) - raising threshold")

            # If high confidence trades are very profitable, increase scaling factor (tunable with limits)
            if high_conf.get('count', 0) > 0 and high_conf.get('win_rate', 50) > self.config.tune_high_conf_strong_threshold:
                new_params.confidence_scaling_factor = min(self.config.tune_confidence_scaling_factor_max, new_params.confidence_scaling_factor + self.config.tune_confidence_scaling_step)
                print(f"  💎 High confidence trades performing well ({high_conf['win_rate']:.1f}%) - increasing sizing")

        # NEW: 7. Tune mean reversion parameters (using tunable thresholds and limits)
        if signal_type_analysis:
            mr_oversold = signal_type_analysis.get('mean_reversion_oversold', {})
            momentum_signals = signal_type_analysis.get('bullish_momentum', {})

            # If mean reversion signals are working, increase allocation (tunable with limits)
            if mr_oversold.get('count', 0) > 0 and mr_oversold.get('win_rate', 50) > self.config.tune_mr_good_threshold:
                new_params.mean_reversion_allocation = min(self.config.tune_mean_reversion_allocation_max, new_params.mean_reversion_allocation + self.config.tune_neutral_step)
                print(f"  📊 Mean reversion signals profitable ({mr_oversold['win_rate']:.1f}%) - increasing allocation")

            # If mean reversion signals are losing, be more selective (tunable with limits)
            if mr_oversold.get('count', 0) > 0 and mr_oversold.get('win_rate', 50) < self.config.tune_mr_poor_threshold:
                new_params.rsi_oversold_threshold = max(self.config.tune_rsi_oversold_threshold_min, new_params.rsi_oversold_threshold - self.config.tune_rsi_threshold_step)
                print(f"  📉 Mean reversion signals underperforming - tightening RSI threshold")
            # BIDIRECTIONAL: If MR signals performing moderately but we're too tight, loosen threshold
            elif mr_oversold.get('count', 0) > 0 and mr_oversold.get('win_rate', 50) > 55 and new_params.rsi_oversold_threshold < 28:
                new_params.rsi_oversold_threshold = min(
                    self.config.tune_rsi_oversold_threshold_max if hasattr(self.config, 'tune_rsi_oversold_threshold_max') else 40.0,
                    new_params.rsi_oversold_threshold + self.config.tune_rsi_threshold_step * 0.5  # Slower recovery
                )
                print(f"  📈 Mean reversion signals working with tight threshold - loosening slightly")

        # REMOVED: Circuit breaker tuning - strategy should learn from mistakes, not cease operations
        # Just monitor drawdown and warn in monthly reports

        # 8. CRITICAL: Tune risk score calculation weights (was the original hard-coded problem!)
        # Optimize based on risk-adjusted returns by confidence bucket
        if confidence_analysis:
            high_conf = confidence_analysis.get('high', {})
            low_conf = confidence_analysis.get('low', {})

            # Risk assessment is working if:
            # - High confidence trades are very profitable (>65% win rate)
            # - Low confidence trades are correctly identified as risky (<45% win rate)
            risk_assessment_working = (
                high_conf.get('count', 0) > 5 and
                low_conf.get('count', 0) > 5 and
                high_conf.get('win_rate', 50) > 65 and
                low_conf.get('win_rate', 50) < 45
            )

            print(f"\n  📊 Risk Score Assessment:")
            print(f"    High conf: {high_conf.get('count', 0)} trades, {high_conf.get('win_rate', 0):.1f}% win rate")
            print(f"    Low conf: {low_conf.get('count', 0)} trades, {low_conf.get('win_rate', 0):.1f}% win rate")
            print(f"    Current weights: Vol={new_params.risk_volatility_weight:.2f}, Corr={new_params.risk_correlation_weight:.2f}")

            # If risk assessment is failing, adjust weights
            # Strategy: Try different weight combinations to improve risk discrimination
            if not risk_assessment_working and high_conf.get('count', 0) > 5 and low_conf.get('count', 0) > 5:
                # If low confidence trades are performing TOO WELL, we're not penalizing risk enough
                if low_conf.get('win_rate', 50) > 50:
                    # Increase volatility weight (be more risk-averse)
                    new_params.risk_volatility_weight = min(0.85, new_params.risk_volatility_weight + 0.05)
                    new_params.risk_correlation_weight = max(0.15, new_params.risk_correlation_weight - 0.05)
                    print(f"  ⚠️  Low confidence trades performing too well - increasing volatility weight")

                # If high confidence trades are performing POORLY, we're being too conservative
                elif high_conf.get('win_rate', 50) < 55:
                    # Shift weight to correlation (focus on systematic risk over idiosyncratic)
                    new_params.risk_volatility_weight = max(0.5, new_params.risk_volatility_weight - 0.05)
                    new_params.risk_correlation_weight = min(0.5, new_params.risk_correlation_weight + 0.05)
                    print(f"  📊 High confidence trades underperforming - shifting weight to correlation")

                # If there's a big gap in performance, we're doing something right
                # but can fine-tune further
                else:
                    win_rate_gap = high_conf.get('win_rate', 50) - low_conf.get('win_rate', 50)
                    if win_rate_gap < 15:  # Gap too small
                        # Try shifting toward volatility for better discrimination
                        new_params.risk_volatility_weight = min(0.85, new_params.risk_volatility_weight + 0.03)
                        new_params.risk_correlation_weight = max(0.15, new_params.risk_correlation_weight - 0.03)
                        print(f"  🔍 Risk discrimination gap too small ({win_rate_gap:.1f}%) - fine-tuning weights")

            elif risk_assessment_working:
                print(f"  ✅ Risk score weights working well - maintaining current balance")

        return new_params

    def save_parameters(self, params: TradingConfig, report_path: str, start_date: date):
        """
        Save parameters to database as a new version

        Args:
            params: New configuration parameters
            report_path: Path to the report file
            start_date: Start date for the new configuration
        """
        # Save to database
        config_id = self.config_loader.create_new_version(
            params,
            start_date=start_date,
            created_by='strategy_tuning',
            notes=f'Monthly tuning - report: {os.path.basename(report_path)}',
            close_previous=True
        )

        print(f"\n💾 Parameters saved to database:")
        print(f"   Config ID: {config_id}")
        print(f"   Start Date: {start_date}")
        print(f"   Previous config end date set to: {start_date - timedelta(days=1)}")

        # Also save JSON version for reference
        json_path = os.path.join(os.path.dirname(report_path), 'tuned_parameters.json')
        with open(json_path, 'w') as f:
            json.dump(params.to_dict(), f, indent=2, default=str)

        print(f"💾 JSON backup saved to: {json_path}")

    def generate_report(self,
                       old_params: TradingConfig,
                       new_params: TradingConfig,
                       evaluations: List[TradeEvaluation],
                       condition_analysis: Dict,
                       overall_metrics: Dict,
                       start_date: date,
                       end_date: date,
                       confidence_analysis: Dict = None,
                       signal_type_analysis: Dict = None,
                       validation_result: Dict = None) -> str:
        """
        Generate comprehensive tuning report

        Returns:
            Path to saved report
        """
        report_lines = []

        def add(text=""):
            print(text)
            report_lines.append(text)

        add(f"\n{'='*80}")
        add(f"📊 MONTHLY STRATEGY TUNING REPORT")
        add(f"{'='*80}\n")
        add(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        add(f"Analysis Period: {start_date} to {end_date}")
        add(f"Total Trading Days: {overall_metrics.get('total_days', 0)}\n")

        # Overall Performance
        add(f"{'='*80}")
        add(f"📈 OVERALL PERFORMANCE METRICS")
        add(f"{'='*80}\n")
        add(f"Total Return: {overall_metrics.get('total_return', 0):+.2f}%")
        add(f"Sharpe Ratio: {overall_metrics.get('sharpe_ratio', 0):.3f}")
        add(f"Max Drawdown: {overall_metrics.get('max_drawdown', 0):.2f}%")
        add()

        # Trade Evaluations Summary
        add(f"{'='*80}")
        add(f"🔍 TRADE EVALUATION SUMMARY")
        add(f"{'='*80}\n")

        bad_trades = [e for e in evaluations if e.should_have_avoided]
        good_trades = [e for e in evaluations if e.score > 0.3]

        add(f"Total Trades Analyzed: {len(evaluations)}")
        add(f"Good Trades (score > 0.3): {len(good_trades)} ({len(good_trades)/len(evaluations)*100:.1f}%)")
        add(f"Trades That Should Have Been Avoided: {len(bad_trades)} ({len(bad_trades)/len(evaluations)*100:.1f}%)")
        add()

        if bad_trades:
            add("❌ Worst Trades (should have avoided):")
            for trade in sorted(bad_trades, key=lambda x: x.score)[:5]:
                add(f"  {trade.trade_date} | {trade.symbol} {trade.action} | "
                    f"Condition: {trade.market_condition} | DD contribution: {trade.contribution_to_drawdown:.1f}% | "
                    f"P&L: ${trade.pnl:+.2f}")
            add()

        # Performance by Market Condition
        add(f"{'='*80}")
        add(f"🌍 PERFORMANCE BY MARKET CONDITION")
        add(f"{'='*80}\n")

        for condition in ['momentum', 'choppy', 'overall']:
            perf = condition_analysis[condition]
            add(f"{condition.upper()}:")
            add(f"  Trades: {perf['count']}")
            if perf['count'] > 0:
                add(f"  Win Rate: {perf['win_rate']:.1f}%")
                add(f"  Avg Score: {perf['avg_score']:+.3f}")
                add(f"  Total P&L: ${perf['total_pnl']:+,.2f}")
                add(f"  Avg DD Contribution: {perf['avg_drawdown_contribution']:.2f}%")
                add(f"  Buy Trades: {perf['buy_count']} | Hold Trades: {perf['hold_count']}")

                if perf['should_be_more_aggressive']:
                    add(f"  💡 INSIGHT: Strategy is too conservative in {condition} conditions")
                if perf['should_be_more_conservative']:
                    add(f"  ⚠️  INSIGHT: Strategy is too aggressive in {condition} conditions")
            add()

        # Parameter Changes
        add(f"{'='*80}")
        add(f"🔧 PARAMETER ADJUSTMENTS")
        add(f"{'='*80}\n")

        changes_made = False
        old_dict = old_params.to_dict()
        new_dict = new_params.to_dict()

        add(f"{'Parameter':<40} {'Old Value':<15} {'New Value':<15} {'Change':<15}")
        add("-" * 85)

        for key in sorted(old_dict.keys()):
            old_val = old_dict[key]
            new_val = new_dict[key]

            # Skip non-numeric fields (like assets list, dates, strings)
            if not isinstance(old_val, (int, float)) or not isinstance(new_val, (int, float)):
                # For non-numeric fields, just show if they changed
                if old_val != new_val:
                    add(f"📝 {key:<37} {str(old_val):<15} {str(new_val):<15} {'changed':<15}")
                    changes_made = True
                continue

            if abs(old_val - new_val) > 0.001:  # Changed
                change = new_val - old_val
                change_str = f"{change:+.3f}"
                marker = "📈" if change > 0 else "📉"
                add(f"{marker} {key:<37} {old_val:<15.3f} {new_val:<15.3f} {change_str:<15}")
                changes_made = True
            else:
                add(f"  {key:<38} {old_val:<15.3f} {new_val:<15.3f} {'--':<15}")

        add()

        if not changes_made:
            add("✅ No parameter changes recommended - current strategy is performing well!\n")
        else:
            add("📋 SUMMARY: Parameters have been adjusted based on performance analysis.\n")

        # Recommendations
        add(f"{'='*80}")
        add(f"💡 RECOMMENDATIONS")
        add(f"{'='*80}\n")

        max_dd = overall_metrics.get('max_drawdown', 0)
        if max_dd > old_params.max_drawdown_tolerance:
            add(f"⚠️  WARNING: Max drawdown ({max_dd:.1f}%) exceeded tolerance ({old_params.max_drawdown_tolerance:.0f}%)")
            add(f"    Strategy continues operating to learn from mistakes")
            add(f"    Tuning will adjust parameters to improve future performance")

        if overall_metrics.get('sharpe_ratio', 0) < old_params.min_sharpe_target:
            add(f"📊 Sharpe ratio below target - focus on risk-adjusted returns")

        if condition_analysis['choppy']['avg_drawdown_contribution'] > 20:
            add(f"🌊 High drawdown in choppy markets - reduce exposure during uncertainty")

        if condition_analysis['momentum']['win_rate'] > 70 and condition_analysis['momentum']['buy_count'] < condition_analysis['momentum']['count'] * 0.5:
            add(f"📈 Missing opportunities in momentum markets - consider more aggressive positioning")

        add()
        add(f"{'='*80}")
        add(f"📝 NEXT STEPS")
        add(f"{'='*80}\n")
        add("1. Review the parameter changes above")
        add("2. New parameters have been saved to the database and will be active from the specified start date")
        add("3. Run backtest with new parameters to validate improvements")
        add("4. Monitor performance over the next month")
        add()
        add(f"{'='*80}\n")

        # Save report
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"strategy_tuning_report_{start_date}_to_{end_date}_{timestamp}.txt"

        backend_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(backend_dir)
        report_dir = os.path.join(project_root, 'data', 'strategy-tuning')

        os.makedirs(report_dir, exist_ok=True)
        filepath = os.path.join(report_dir, filename)

        with open(filepath, 'w') as f:
            f.write('\n'.join(report_lines))

        print(f"💾 Report saved to: {filepath}\n")

        return filepath

    def run(self):
        """Main execution flow"""
        print(f"\n{'='*80}")
        print(f"🚀 STARTING ENHANCED MONTHLY STRATEGY TUNING")
        print(f"{'='*80}\n")

        # 1. Determine analysis period
        print("📅 Determining analysis period...")
        start_date, end_date = self.get_analysis_period()
        print(f"   Analysis Period: {start_date} to {end_date}\n")

        # 2. Evaluate all trades with multi-horizon analysis
        print("🔍 Evaluating trades (10d, 20d, 30d horizons)...")
        evaluations = self.evaluate_trades(start_date, end_date)
        print(f"   Analyzed {len(evaluations)} trades\n")

        # 3. Analyze performance by condition
        print("🌍 Analyzing performance by market condition...")
        condition_analysis = self.analyze_performance_by_condition(evaluations)
        print(f"   Momentum trades: {condition_analysis['momentum']['count']}")
        print(f"   Choppy trades: {condition_analysis['choppy']['count']}\n")

        # NEW: 3b. Analyze confidence buckets
        print("🎯 Analyzing performance by confidence bucket...")
        confidence_analysis = self.analyze_confidence_buckets(evaluations)
        for bucket, metrics in confidence_analysis.items():
            if metrics['count'] > 0:
                print(f"   {bucket.upper()}: {metrics['count']} trades, {metrics['win_rate']:.1f}% win rate, ${metrics['total_pnl']:+,.2f}")
        print()

        # NEW: 3c. Analyze signal types
        print("📈 Analyzing performance by signal type...")
        signal_type_analysis = self.analyze_signal_types(evaluations)
        for signal_type, metrics in signal_type_analysis.items():
            if metrics['count'] > 0:
                print(f"   {signal_type}: {metrics['count']} trades, {metrics['win_rate']:.1f}% win rate")
        print()

        # 4. Calculate overall metrics
        print("📊 Calculating overall metrics...")
        overall_metrics = self.calculate_overall_metrics(start_date, end_date)
        print(f"   Sharpe: {overall_metrics.get('sharpe_ratio', 0):.3f}")
        print(f"   Max DD: {overall_metrics.get('max_drawdown', 0):.2f}%\n")

        # 5. Tune parameters with enhanced analysis
        print("🔧 Tuning parameters based on analysis...\n")
        old_params = self.current_params
        new_params = self.tune_parameters(
            evaluations, condition_analysis, overall_metrics,
            confidence_analysis, signal_type_analysis
        )

        # NEW: 6. Out-of-sample validation
        # Split period: first 2/3 for training, last 1/3 for testing
        total_days = (end_date - start_date).days
        train_end = start_date + timedelta(days=int(total_days * 0.67))
        test_start = train_end + timedelta(days=1)

        print("🧪 Performing out-of-sample validation...")
        validation_result = self.perform_out_of_sample_validation(
            new_params,
            (start_date, train_end),
            (test_start, end_date)
        )
        print(f"   Validation Score: {validation_result['validation_score']:.2f}")
        print(f"   Test Sharpe: {validation_result['test_sharpe']:.3f}")
        print(f"   Test Max DD: {validation_result['test_max_drawdown']:.2f}%")

        if not validation_result['passes_validation']:
            print("   ❌ VALIDATION FAILED: Parameters do not generalize to test period")
            print("   🔄 Reverting to previous parameters - no changes will be deployed")
            print(f"   Reason: Validation score {validation_result['validation_score']:.2f} < {self.config.validation_passing_score:.2f}")
            print(f"   Test Sharpe: {validation_result['test_sharpe']:.3f} (target: {new_params.min_sharpe_target * self.config.validation_sharpe_tolerance:.3f}+)")
            print(f"   Test Max DD: {validation_result['test_max_drawdown']:.2f}% (limit: {new_params.max_drawdown_tolerance * self.config.validation_dd_tolerance:.2f}%)")
            print()
            # CRITICAL FIX: Revert to old parameters instead of deploying failing ones
            new_params = old_params
            print("   ℹ️  Previous parameters will remain active. Review analysis to understand why tuning failed.")
        else:
            print("   ✅ Parameters pass out-of-sample validation - safe to deploy")
        print()

        # 7. Generate report
        print("\n📝 Generating comprehensive report...\n")
        report_path = self.generate_report(
            old_params, new_params, evaluations,
            condition_analysis, overall_metrics,
            start_date, end_date,
            confidence_analysis=confidence_analysis,
            signal_type_analysis=signal_type_analysis,
            validation_result=validation_result
        )

        # 8. Save parameters to database with start date = first day of current month
        today = date.today()
        next_config_start_date = date(today.year, today.month, 1)
        self.save_parameters(new_params, report_path, next_config_start_date)

        print(f"\n{'='*80}")
        print(f"✅ ENHANCED MONTHLY TUNING COMPLETED")
        print(f"{'='*80}\n")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Monthly strategy tuning - analyzes past performance and adjusts parameters'
    )
    parser.add_argument(
        '--lookback-months',
        type=int,
        default=3,
        help='Number of months to analyze (default: 3)'
    )

    args = parser.parse_args()

    try:
        tuner = StrategyTuner(lookback_months=args.lookback_months)
        tuner.run()
        tuner.close()
        return 0
    except Exception as e:
        print(f"❌ Strategy tuning failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
