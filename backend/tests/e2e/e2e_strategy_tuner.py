"""
E2E Strategy Tuner - Trains trading config parameters using test tables.
This is an adapted version of strategy_tuning.py that works with test tables.
"""
import os
import sys
import json
import math
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Dict, List, Tuple
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
        DATABASE_URL = "postgresql://test:test@localhost/allocator_db"


class E2EStrategyTuner:
    """Strategy tuner that works with test tables for E2E testing"""

    def __init__(self, train_start: date, train_end: date, report_dir: str = None):
        """
        Initialize strategy tuner for E2E testing

        Args:
            train_start: Start date of training period
            train_end: End date of training period
            report_dir: Directory for saving tuning reports
        """
        self.conn = psycopg2.connect(DATABASE_URL)
        self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        self.train_start = train_start
        self.train_end = train_end

        # Set report directory
        if report_dir is None:
            report_dir = Path(__file__).parent.parent.parent.parent / 'data' / 'test-reports' / 'tuning'
        self.report_dir = Path(report_dir)
        self.report_dir.mkdir(parents=True, exist_ok=True)

        # Load current test trading config
        self.current_params = self._load_current_config()

    def close(self):
        """Close database connection"""
        self.cursor.close()
        self.conn.close()

    def _load_current_config(self) -> Dict:
        """Load current test trading config"""
        self.cursor.execute("""
            SELECT * FROM test_trading_config
            ORDER BY start_date DESC
            LIMIT 1
        """)
        row = self.cursor.fetchone()
        if row:
            return dict(row)
        else:
            return self._get_default_config()

    def _get_default_config(self) -> Dict:
        """Get default configuration parameters"""
        return {
            'daily_capital': 1000.0,
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
            'max_drawdown_tolerance': 15.0,
            'min_sharpe_target': 1.0,
            'rsi_oversold_threshold': 30.0,
            'rsi_overbought_threshold': 70.0,
            'bollinger_std_multiplier': 2.0,
            'mean_reversion_allocation': 0.4,
            'volatility_adjustment_factor': 0.4,
            'base_volatility': 0.01,
            'min_confidence_threshold': 0.3,
            'confidence_scaling_factor': 0.5,
            'intramonth_drawdown_limit': 0.10,
            'circuit_breaker_reduction': 0.5
        }

    def analyze_price_patterns(self) -> Dict:
        """
        Analyze price patterns in training period to tune initial parameters

        Returns:
            Dict with pattern analysis results
        """
        # Get price history for training period
        self.cursor.execute("""
            SELECT date, symbol, open_price, high_price, low_price, close_price, volume
            FROM test_price_history
            WHERE date >= %s AND date <= %s
            ORDER BY date, symbol
        """, (self.train_start, self.train_end))

        rows = self.cursor.fetchall()
        if not rows:
            return {'error': 'No price data in training period'}

        # Organize data by symbol
        prices_by_symbol = {}
        for row in rows:
            symbol = row['symbol']
            if symbol not in prices_by_symbol:
                prices_by_symbol[symbol] = []
            prices_by_symbol[symbol].append({
                'date': row['date'],
                'open': float(row['open_price']),
                'high': float(row['high_price']),
                'low': float(row['low_price']),
                'close': float(row['close_price']),
                'volume': int(row['volume'])
            })

        analysis = {
            'symbols': list(prices_by_symbol.keys()),
            'trading_days': len(prices_by_symbol.get('SPY', [])),
            'volatility': {},
            'momentum': {},
            'drawdowns': {},
            'rsi_patterns': {}
        }

        for symbol, prices in prices_by_symbol.items():
            if len(prices) < 20:
                continue

            closes = np.array([p['close'] for p in prices])
            returns = np.diff(closes) / closes[:-1]

            # Volatility analysis
            daily_vol = np.std(returns)
            analysis['volatility'][symbol] = {
                'daily': daily_vol,
                'annualized': daily_vol * np.sqrt(252)
            }

            # Momentum analysis
            if len(closes) >= 60:
                returns_20d = (closes[-1] / closes[-20] - 1)
                returns_60d = (closes[-1] / closes[-60] - 1) if len(closes) >= 60 else 0
            else:
                returns_20d = 0
                returns_60d = 0
            analysis['momentum'][symbol] = {
                'returns_20d': returns_20d,
                'returns_60d': returns_60d
            }

            # Max drawdown analysis
            peak = closes[0]
            max_dd = 0
            for close in closes:
                if close > peak:
                    peak = close
                dd = (peak - close) / peak
                if dd > max_dd:
                    max_dd = dd
            analysis['drawdowns'][symbol] = max_dd

            # RSI patterns - how often are we oversold/overbought?
            if len(closes) >= 15:
                rsi_values = self._calculate_rsi_series(closes)
                oversold_count = sum(1 for r in rsi_values if r < 30)
                overbought_count = sum(1 for r in rsi_values if r > 70)
                analysis['rsi_patterns'][symbol] = {
                    'oversold_pct': oversold_count / len(rsi_values) * 100,
                    'overbought_pct': overbought_count / len(rsi_values) * 100,
                    'avg_rsi': np.mean(rsi_values)
                }

        return analysis

    def _calculate_rsi_series(self, closes: np.ndarray, period: int = 14) -> List[float]:
        """Calculate RSI for a series of closing prices"""
        rsi_values = []
        deltas = np.diff(closes)

        for i in range(period, len(closes)):
            gains = deltas[i - period:i]
            ups = np.where(gains > 0, gains, 0)
            downs = np.where(gains < 0, -gains, 0)
            avg_gain = np.mean(ups)
            avg_loss = np.mean(downs)

            if avg_loss == 0:
                rsi = 100.0
            else:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
            rsi_values.append(rsi)

        return rsi_values

    def tune_initial_parameters(self) -> Dict:
        """
        Tune initial parameters based on training period analysis

        Returns:
            Dict with tuned parameters
        """
        analysis = self.analyze_price_patterns()

        if 'error' in analysis:
            print(f"   WARNING: {analysis['error']}, using defaults")
            return self._get_default_config()

        # Start with current/default params
        tuned = self._get_default_config()

        # 1. Tune volatility parameters based on observed volatility
        vol_values = [v['daily'] for v in analysis['volatility'].values() if v['daily'] > 0]
        if vol_values:
            avg_volatility = np.mean(vol_values)
            if np.isnan(avg_volatility) or avg_volatility == 0:
                avg_volatility = 0.01  # Default 1% daily vol
        else:
            avg_volatility = 0.01  # Default
        tuned['base_volatility'] = avg_volatility

        # If volatility is high, be more conservative
        if avg_volatility > 0.015:  # More than 1.5% daily vol
            tuned['allocation_low_risk'] = 0.7
            tuned['allocation_medium_risk'] = 0.4
            tuned['allocation_high_risk'] = 0.25
            tuned['volatility_adjustment_factor'] = 0.5
        elif avg_volatility < 0.008:  # Low volatility
            tuned['allocation_low_risk'] = 0.9
            tuned['allocation_medium_risk'] = 0.6
            tuned['allocation_high_risk'] = 0.4

        # 2. Tune regime thresholds based on momentum patterns
        avg_momentum = np.mean([
            m['returns_20d'] for m in analysis['momentum'].values()
        ])

        # If market tends to trend, use tighter thresholds
        if abs(avg_momentum) > 0.05:  # Strong trend
            tuned['regime_bullish_threshold'] = 0.25
            tuned['regime_bearish_threshold'] = -0.25
        else:  # Choppy market
            tuned['regime_bullish_threshold'] = 0.35
            tuned['regime_bearish_threshold'] = -0.35

        # 3. Tune drawdown tolerance based on observed drawdowns
        avg_drawdown = np.mean(list(analysis['drawdowns'].values()))
        tuned['max_drawdown_tolerance'] = max(10.0, min(20.0, avg_drawdown * 100 * 1.5))
        tuned['intramonth_drawdown_limit'] = tuned['max_drawdown_tolerance'] / 100 / 2

        # 4. Tune RSI thresholds based on patterns
        if analysis['rsi_patterns']:
            avg_oversold_pct = np.mean([
                r['oversold_pct'] for r in analysis['rsi_patterns'].values()
            ])
            avg_overbought_pct = np.mean([
                r['overbought_pct'] for r in analysis['rsi_patterns'].values()
            ])

            # If oversold signals are rare, they might be more significant
            if avg_oversold_pct < 5:
                tuned['rsi_oversold_threshold'] = 25
                tuned['mean_reversion_allocation'] = 0.5  # More aggressive on rare signals
            elif avg_oversold_pct > 15:
                tuned['rsi_oversold_threshold'] = 35
                tuned['mean_reversion_allocation'] = 0.3

            if avg_overbought_pct > 15:
                tuned['rsi_overbought_threshold'] = 65

        # 5. Tune confidence parameters
        # If market is volatile, require higher confidence
        if avg_volatility > 0.012:
            tuned['min_confidence_threshold'] = 0.4
            tuned['confidence_scaling_factor'] = 0.6
        else:
            tuned['min_confidence_threshold'] = 0.25
            tuned['confidence_scaling_factor'] = 0.4

        return tuned

    def save_tuned_config(self, params: Dict, effective_date: date):
        """
        Save tuned configuration to test_trading_config table

        Args:
            params: Dictionary of tuned parameters
            effective_date: Date from which this config becomes effective
        """
        # Convert numpy types to Python native types
        def convert_to_native(val):
            if isinstance(val, (np.integer, np.int64, np.int32)):
                return int(val)
            elif isinstance(val, (np.floating, np.float64, np.float32)):
                return float(val)
            return val

        params = {k: convert_to_native(v) for k, v in params.items()}

        # Close out previous config
        self.cursor.execute("""
            UPDATE test_trading_config
            SET end_date = %s
            WHERE end_date IS NULL
        """, (effective_date - timedelta(days=1),))

        # Insert new config
        self.cursor.execute("""
            INSERT INTO test_trading_config (
                start_date,
                end_date,
                daily_capital,
                assets,
                lookback_days,
                regime_bullish_threshold,
                regime_bearish_threshold,
                risk_high_threshold,
                risk_medium_threshold,
                allocation_low_risk,
                allocation_medium_risk,
                allocation_high_risk,
                allocation_neutral,
                sell_percentage,
                momentum_weight,
                price_momentum_weight,
                max_drawdown_tolerance,
                min_sharpe_target,
                rsi_oversold_threshold,
                rsi_overbought_threshold,
                bollinger_std_multiplier,
                mean_reversion_allocation,
                volatility_adjustment_factor,
                base_volatility,
                min_confidence_threshold,
                confidence_scaling_factor,
                intramonth_drawdown_limit,
                circuit_breaker_reduction,
                created_by,
                notes
            ) VALUES (
                %s, NULL, %s, %s, %s,
                %s, %s,
                %s, %s,
                %s, %s, %s,
                %s, %s,
                %s, %s,
                %s, %s,
                %s, %s, %s, %s,
                %s, %s,
                %s, %s,
                %s, %s,
                %s, %s
            )
        """, (
            effective_date,
            params.get('daily_capital', 1000.0),
            '["SPY", "QQQ", "DIA"]',
            params.get('lookback_days', 252),
            params.get('regime_bullish_threshold', 0.3),
            params.get('regime_bearish_threshold', -0.3),
            params.get('risk_high_threshold', 70.0),
            params.get('risk_medium_threshold', 40.0),
            params.get('allocation_low_risk', 0.8),
            params.get('allocation_medium_risk', 0.5),
            params.get('allocation_high_risk', 0.3),
            params.get('allocation_neutral', 0.2),
            params.get('sell_percentage', 0.7),
            params.get('momentum_weight', 0.6),
            params.get('price_momentum_weight', 0.4),
            params.get('max_drawdown_tolerance', 15.0),
            params.get('min_sharpe_target', 1.0),
            params.get('rsi_oversold_threshold', 30.0),
            params.get('rsi_overbought_threshold', 70.0),
            params.get('bollinger_std_multiplier', 2.0),
            params.get('mean_reversion_allocation', 0.4),
            params.get('volatility_adjustment_factor', 0.4),
            params.get('base_volatility', 0.01),
            params.get('min_confidence_threshold', 0.3),
            params.get('confidence_scaling_factor', 0.5),
            params.get('intramonth_drawdown_limit', 0.10),
            params.get('circuit_breaker_reduction', 0.5),
            'e2e_strategy_tuner',
            f'Tuned from {self.train_start} to {self.train_end}'
        ))

        self.conn.commit()

    def generate_tuning_report(self, analysis: Dict, tuned_params: Dict) -> str:
        """
        Generate a report of the tuning process

        Returns:
            Path to saved report
        """
        report_lines = []

        report_lines.append(f"\n{'='*60}")
        report_lines.append(f"E2E STRATEGY TUNING REPORT")
        report_lines.append(f"{'='*60}\n")
        report_lines.append(f"Training Period: {self.train_start} to {self.train_end}")
        report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("")

        # Analysis results
        report_lines.append("MARKET ANALYSIS:")
        report_lines.append(f"  Trading Days: {analysis.get('trading_days', 0)}")

        if 'volatility' in analysis:
            report_lines.append("\nVOLATILITY:")
            for symbol, vol in analysis['volatility'].items():
                report_lines.append(f"  {symbol}: {vol['daily']*100:.2f}% daily, {vol['annualized']*100:.1f}% annualized")

        if 'momentum' in analysis:
            report_lines.append("\nMOMENTUM:")
            for symbol, mom in analysis['momentum'].items():
                report_lines.append(f"  {symbol}: 20d={mom['returns_20d']*100:+.2f}%, 60d={mom['returns_60d']*100:+.2f}%")

        if 'drawdowns' in analysis:
            report_lines.append("\nMAX DRAWDOWNS:")
            for symbol, dd in analysis['drawdowns'].items():
                report_lines.append(f"  {symbol}: {dd*100:.2f}%")

        # Tuned parameters
        report_lines.append(f"\n{'='*60}")
        report_lines.append("TUNED PARAMETERS:")
        report_lines.append(f"{'='*60}\n")

        for key, value in sorted(tuned_params.items()):
            if isinstance(value, float):
                report_lines.append(f"  {key}: {value:.4f}")
            else:
                report_lines.append(f"  {key}: {value}")

        report_lines.append(f"\n{'='*60}\n")

        # Save report
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"e2e_tuning_{self.train_start}_to_{self.train_end}_{timestamp}.txt"
        filepath = self.report_dir / filename

        with open(filepath, 'w') as f:
            f.write('\n'.join(report_lines))

        return str(filepath)

    def run(self, effective_date: date) -> Dict:
        """
        Run the tuning process

        Args:
            effective_date: Date from which tuned config becomes effective

        Returns:
            Dict with tuning results
        """
        print(f"   Training period: {self.train_start} to {self.train_end}")

        # Analyze patterns
        analysis = self.analyze_price_patterns()

        if 'error' not in analysis:
            print(f"   Analyzed {analysis['trading_days']} trading days")
            print(f"   Average volatility: {np.mean([v['daily'] for v in analysis['volatility'].values()])*100:.2f}%")
        else:
            print(f"   WARNING: {analysis['error']}")

        # Tune parameters
        tuned_params = self.tune_initial_parameters()

        # Save to database
        self.save_tuned_config(tuned_params, effective_date)

        # Generate report
        report_file = self.generate_tuning_report(analysis, tuned_params)

        return {
            'analysis': analysis,
            'tuned_params': tuned_params,
            'effective_date': effective_date,
            'report_file': report_file
        }
