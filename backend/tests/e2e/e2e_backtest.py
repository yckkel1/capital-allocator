"""
E2E Backtest module that uses test tables instead of production tables.
This is a modified version of backtest.py for E2E testing.
"""
import os
import sys
from datetime import datetime, date
from decimal import Decimal
from typing import List, Dict
from pathlib import Path

import psycopg2
from psycopg2.extras import RealDictCursor

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
    """E2E Backtest that uses test tables"""

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

        # Load daily budget from TEST trading config
        self.cursor.execute("""
            SELECT daily_capital FROM test_trading_config
            WHERE start_date <= %s
            AND (end_date IS NULL OR end_date >= %s)
            ORDER BY start_date DESC
            LIMIT 1
        """, (start_date, start_date))
        row = self.cursor.fetchone()
        if row:
            self.daily_budget = Decimal(str(row['daily_capital']))
        else:
            self.daily_budget = Decimal("1000.0")

    def close(self):
        self.cursor.close()
        self.conn.close()

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
        """Generate signal for a specific date using test tables"""
        # Get price data from test tables
        self.cursor.execute("""
            SELECT symbol, close_price
            FROM test_price_history
            WHERE date = %s
        """, (trade_date,))

        prices = {row['symbol']: Decimal(str(row['close_price'])) for row in self.cursor.fetchall()}

        if not prices:
            return False

        # Simple allocation logic for testing: equal split
        allocations = {}
        symbols = ['SPY', 'QQQ', 'DIA']
        allocation_per_asset = float(self.daily_budget) / len(symbols)

        for symbol in symbols:
            if symbol in prices:
                allocations[symbol] = allocation_per_asset
            else:
                allocations[symbol] = 0.0

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
            str(allocations).replace("'", '"'),  # JSON format
            'e2e_test_momentum',
            0.75,
            '{}'
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
