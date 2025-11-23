"""
Backtest Script
Simulates trading strategy over a specified date range
"""
import os
import sys
import argparse
import subprocess
from datetime import datetime, date
from decimal import Decimal
from typing import List, Dict

import psycopg2
from psycopg2.extras import RealDictCursor

# Import configuration
from config import get_settings, get_trading_config

settings = get_settings()
DATABASE_URL = settings.database_url


class Backtest:
    def __init__(self, start_date: date, end_date: date):
        self.conn = psycopg2.connect(DATABASE_URL)
        self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        self.start_date = start_date
        self.end_date = end_date
        self.trading_days = []
        # Load daily budget from trading config
        trading_config = get_trading_config(start_date)
        self.daily_budget = Decimal(str(trading_config.daily_capital))
        
    def close(self):
        self.cursor.close()
        self.conn.close()
    
    def get_trading_days(self) -> List[date]:
        """Get all trading days in the specified date range"""
        self.cursor.execute("""
            SELECT DISTINCT date 
            FROM price_history 
            WHERE date >= %s AND date <= %s
            AND symbol = 'SPY'
            ORDER BY date
        """, (self.start_date, self.end_date))
        
        days = [row['date'] for row in self.cursor.fetchall()]
        
        if not days:
            raise Exception(f"No data found for {self.start_date} to {self.end_date}. Run fetch_prices.py first.")
        
        return days
    
    def clear_backtest_data(self, preserve_portfolio: bool = False):
        """
        Clear any existing backtest data for this date range

        Args:
            preserve_portfolio: If True, preserve portfolio state (for month-by-month backtesting)
        """
        print(f"🧹 Clearing existing data for {self.start_date} to {self.end_date}...")

        # Clear signals
        self.cursor.execute("""
            DELETE FROM daily_signals
            WHERE trade_date >= %s AND trade_date <= %s
        """, (self.start_date, self.end_date))

        # Clear trades
        self.cursor.execute("""
            DELETE FROM trades
            WHERE trade_date >= %s AND trade_date <= %s
        """, (self.start_date, self.end_date))

        # Clear portfolio ONLY if not preserving state
        if not preserve_portfolio:
            self.cursor.execute("DELETE FROM portfolio")
            print("   ✓ Cleared portfolio (starting fresh)")
        else:
            print("   ℹ️  Preserved portfolio state (continuing from previous period)")

        # Clear performance metrics
        self.cursor.execute("""
            DELETE FROM performance_metrics
            WHERE date >= %s AND date <= %s
        """, (self.start_date, self.end_date))

        self.conn.commit()
        print("   ✓ Cleared signals, trades, and performance metrics\n")
    
    def generate_signal(self, trade_date: date) -> bool:
        """Generate signal for a specific date"""
        try:
            result = subprocess.run(
                ["python", "scripts/generate_signal.py", "--date", str(trade_date)],
                cwd=os.path.dirname(os.path.abspath(__file__)),
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.returncode == 0
        except Exception as e:
            print(f"   ❌ Error generating signal: {e}")
            return False
    
    def execute_trades(self, trade_date: date) -> bool:
        """Execute trades for a specific date"""
        try:
            result = subprocess.run(
                ["python", "execute_trades.py", str(trade_date)],
                cwd=os.path.dirname(os.path.abspath(__file__)),
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.returncode == 0
        except Exception as e:
            print(f"   ❌ Error executing trades: {e}")
            return False
    
    def calculate_daily_metrics(self, trade_date: date, preserve_portfolio: bool = False) -> Dict:
        """
        Calculate performance metrics for a given day using portfolio table

        Portfolio table now includes CASH entry, so we simply read current state
        instead of reconstructing from trades history

        Args:
            trade_date: Date to calculate metrics for
            preserve_portfolio: Not used anymore (kept for compatibility)
        """
        # Get CASH balance directly from portfolio table
        self.cursor.execute("""
            SELECT quantity FROM portfolio WHERE symbol = 'CASH'
        """)
        cash_row = self.cursor.fetchone()
        cash_balance = Decimal(str(cash_row['quantity'])) if cash_row else Decimal(0)

        # Get all non-CASH positions
        self.cursor.execute("""
            SELECT symbol, quantity, avg_cost
            FROM portfolio
            WHERE symbol != 'CASH' AND quantity > 0
        """)
        positions = self.cursor.fetchall()

        # Get closing prices for the day
        self.cursor.execute("""
            SELECT symbol, close_price
            FROM price_history
            WHERE date = %s
        """, (trade_date,))
        prices = {row['symbol']: Decimal(str(row['close_price'])) for row in self.cursor.fetchall()}

        # Calculate portfolio value (holdings only, not cash)
        portfolio_value = Decimal(0)
        for pos in positions:
            symbol = pos['symbol']
            qty = Decimal(str(pos['quantity']))
            current_price = prices.get(symbol, Decimal(0))
            portfolio_value += qty * current_price

        # Total value = portfolio holdings + cash
        total_value = portfolio_value + cash_balance

        # Calculate LIFETIME total grants (all trading days up to now)
        self.cursor.execute("""
            SELECT COUNT(*) as total_days
            FROM performance_metrics
            WHERE date <= %s
        """, (trade_date,))
        days_result = self.cursor.fetchone()
        total_trading_days = days_result['total_days'] if days_result else 0
        total_grants = self.daily_budget * Decimal(str(total_trading_days))

        # LIFETIME P&L using simple formula: (total_portfolio - total_grants) / total_grants
        lifetime_return = total_value - total_grants
        lifetime_return_pct = (lifetime_return / total_grants * 100) if total_grants > 0 else Decimal(0)

        # Daily return (vs previous day)
        self.cursor.execute("""
            SELECT total_value
            FROM performance_metrics
            WHERE date < %s
            ORDER BY date DESC
            LIMIT 1
        """, (trade_date,))
        prev_result = self.cursor.fetchone()

        if prev_result:
            prev_value = Decimal(str(prev_result['total_value']))
            daily_return = ((total_value - prev_value) / prev_value * 100) if prev_value > 0 else Decimal(0)
        else:
            # First day ever - no previous value, assume 0% return
            daily_return = Decimal(0)

        return {
            'date': trade_date,
            'portfolio_value': portfolio_value,
            'cash_balance': cash_balance,
            'total_value': total_value,
            'total_grants': total_grants,
            'daily_return': daily_return,
            'cumulative_return': lifetime_return_pct,  # Use lifetime for backward compat
            'lifetime_return': lifetime_return,
            'lifetime_return_pct': lifetime_return_pct
        }
    
    def save_daily_metrics(self, metrics: Dict):
        """Save daily metrics to performance_metrics table"""
        self.cursor.execute("""
            INSERT INTO performance_metrics 
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
    
    def generate_report(self):
        """Generate final performance report"""
        # Prepare report output
        report_lines = []
        
        def print_and_save(text=""):
            """Print to console and save to report"""
            print(text)
            report_lines.append(text)
        
        print_and_save(f"\n{'='*60}")
        print_and_save(f"📊 BACKTEST REPORT: {self.start_date} to {self.end_date}")
        print_and_save(f"{'='*60}\n")
        
        # Get all metrics for date range
        self.cursor.execute("""
            SELECT * FROM performance_metrics
            WHERE date >= %s AND date <= %s
            ORDER BY date
        """, (self.start_date, self.end_date))
        metrics = self.cursor.fetchall()
        
        if not metrics:
            print_and_save("❌ No performance data found")
            return
        
        first_day = metrics[0]
        last_day = metrics[-1]
        
        # Calculate summary stats
        total_days = len(metrics)

        # Get LIFETIME totals from last day metrics
        final_value = Decimal(str(last_day['total_value']))
        final_cash = Decimal(str(last_day['cash_balance']))
        final_portfolio = Decimal(str(last_day['portfolio_value']))

        # Calculate LIFETIME total grants (all trading days EVER, not just this period)
        self.cursor.execute("""
            SELECT COUNT(*) as total_days_ever
            FROM performance_metrics
            WHERE date <= %s
        """, (last_day['date'],))
        days_result = self.cursor.fetchone()
        total_trading_days_ever = days_result['total_days_ever'] if days_result else 0
        total_grants = self.daily_budget * Decimal(str(total_trading_days_ever))

        # LIFETIME P&L using simple formula: (total_portfolio - total_grants) / total_grants
        lifetime_return = final_value - total_grants
        lifetime_return_pct = (lifetime_return / total_grants * 100) if total_grants > 0 else Decimal(0)

        # Calculate benchmark returns (100% invested in single asset daily)
        # Use LIFETIME calculation: buy $1000/day for ALL trading days EVER (same as strategy)
        benchmarks = {}
        for symbol in ['SPY', 'QQQ', 'DIA']:
            total_shares = Decimal(0)

            # Get ALL trading days up to last_day (same period as strategy)
            self.cursor.execute("""
                SELECT date FROM performance_metrics
                WHERE date <= %s
                ORDER BY date
            """, (last_day['date'],))
            all_trading_days = [row['date'] for row in self.cursor.fetchall()]

            # Simulate buying $1000 worth each trading day at opening price
            for trade_date in all_trading_days:
                self.cursor.execute("""
                    SELECT open_price FROM price_history
                    WHERE symbol = %s AND date = %s
                """, (symbol, trade_date))
                row = self.cursor.fetchone()

                if row:
                    open_price = Decimal(str(row['open_price']))
                    shares_bought = self.daily_budget / open_price
                    total_shares += shares_bought

            # Value all shares at last day's closing price
            self.cursor.execute("""
                SELECT close_price FROM price_history
                WHERE symbol = %s AND date = %s
            """, (symbol, last_day['date']))
            end_row = self.cursor.fetchone()

            if end_row:
                end_price = Decimal(str(end_row['close_price']))
                benchmark_value = total_shares * end_price

                # LIFETIME P&L using simple formula: (total_portfolio - total_grants) / total_grants
                benchmark_return = benchmark_value - total_grants
                benchmark_return_pct = (benchmark_return / total_grants * 100) if total_grants > 0 else Decimal(0)

                benchmarks[symbol] = {
                    'value': benchmark_value,
                    'return': benchmark_return,
                    'return_pct': benchmark_return_pct
                }
        
        # Best and worst days
        best_day = max(metrics, key=lambda x: x['daily_return'] if x['daily_return'] else Decimal('-inf'))
        worst_day = min(metrics, key=lambda x: x['daily_return'] if x['daily_return'] else Decimal('inf'))
        
        # Win rate
        winning_days = sum(1 for m in metrics if m['daily_return'] and m['daily_return'] > 0)
        win_rate = (winning_days / total_days * 100) if total_days > 0 else 0
        
        print_and_save(f"Trading Days (This Period): {total_days}")
        print_and_save(f"Trading Days (Lifetime): {total_trading_days_ever}")
        print_and_save(f"\n💼 LIFETIME ACCOUNT PERFORMANCE")
        print_and_save(f"Total Grants: ${total_grants:,.2f}")
        print_and_save(f"Current Portfolio: ${final_value:,.2f}")
        print_and_save(f"   Holdings: ${final_portfolio:,.2f}")
        print_and_save(f"   Cash: ${final_cash:,.2f}")
        print_and_save(f"P&L: ${lifetime_return:,.2f} ({lifetime_return_pct:+.2f}%)")
        
        print_and_save(f"\n📊 BENCHMARK COMPARISON (100% Daily Investment)")
        for symbol, bench in benchmarks.items():
            print_and_save(f"{symbol}: ${bench['value']:,.2f} | P&L: ${bench['return']:,.2f} ({bench['return_pct']:+.2f}%)")
        
        print_and_save(f"\n📈 DAILY STATISTICS")
        print_and_save(f"Best Day: {best_day['date']} ({best_day['daily_return']:+.2f}%)")
        print_and_save(f"Worst Day: {worst_day['date']} ({worst_day['daily_return']:+.2f}%)")
        print_and_save(f"Win Rate: {win_rate:.1f}% ({winning_days}/{total_days} days)")
        
        # Current holdings
        print_and_save(f"\n{'='*60}")
        print_and_save("📈 FINAL PORTFOLIO POSITIONS")
        print_and_save(f"{'='*60}\n")

        # Display CASH first
        self.cursor.execute("SELECT quantity FROM portfolio WHERE symbol = 'CASH'")
        cash_row = self.cursor.fetchone()
        if cash_row:
            cash_amount = Decimal(str(cash_row['quantity']))
            print_and_save(f"CASH: ${cash_amount:,.2f}\n")

        # Display asset positions
        self.cursor.execute("SELECT * FROM portfolio WHERE symbol != 'CASH' AND quantity > 0 ORDER BY symbol")
        positions = self.cursor.fetchall()

        if positions:
            for pos in positions:
                symbol = pos['symbol']
                qty = Decimal(str(pos['quantity']))
                avg_cost = Decimal(str(pos['avg_cost']))

                # Get final price
                self.cursor.execute("""
                    SELECT close_price FROM price_history
                    WHERE symbol = %s AND date = %s
                """, (symbol, last_day['date']))
                price_row = self.cursor.fetchone()
                current_price = Decimal(str(price_row['close_price'])) if price_row else Decimal(0)

                current_value = qty * current_price
                cost_basis = qty * avg_cost
                pnl = current_value - cost_basis
                pnl_pct = (pnl / cost_basis * 100) if cost_basis > 0 else Decimal(0)

                print_and_save(f"{symbol}: {qty:.4f} shares @ ${avg_cost:.2f} avg")
                print_and_save(f"   Current: ${current_value:,.2f} | P&L: ${pnl:+,.2f} ({pnl_pct:+.2f}%)\n")
        else:
            print_and_save("No asset positions")
        
        print_and_save(f"{'='*60}\n")
        
        # Save report to file in data/back-test folder
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"backtest_report_{self.start_date}_to_{self.end_date}_{timestamp}.txt"
        
        # Get project root (one level up from backend)
        backend_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(backend_dir)
        report_dir = os.path.join(project_root, 'data', 'back-test')
        
        # Create directory if it doesn't exist
        os.makedirs(report_dir, exist_ok=True)
        
        filepath = os.path.join(report_dir, filename)
        
        with open(filepath, 'w') as f:
            f.write('\n'.join(report_lines))
        
        print(f"💾 Report saved to: {filepath}\n")
    
    def run(self, preserve_portfolio: bool = False):
        """
        Run complete backtest

        Args:
            preserve_portfolio: If True, continue from existing portfolio (for month-by-month training)
        """
        print(f"\n{'='*60}")
        print(f"🚀 STARTING BACKTEST: {self.start_date} to {self.end_date}")
        print(f"{'='*60}\n")

        # Step 1: Get trading days
        print("📅 Loading trading days...")
        self.trading_days = self.get_trading_days()
        print(f"   Found {len(self.trading_days)} trading days\n")

        # Step 2: Clear old data (optionally preserve portfolio)
        self.clear_backtest_data(preserve_portfolio=preserve_portfolio)

        # Step 3: Run backtest for each day
        print("🔄 Running daily simulations...\n")

        for i, trade_date in enumerate(self.trading_days, 1):
            print(f"Day {i}/{len(self.trading_days)}: {trade_date}")

            # Generate signal
            print("   Generating signal...", end=" ")
            if not self.generate_signal(trade_date):
                print("❌ FAILED - Skipping day")
                continue
            print("✓")

            # Execute trades
            print("   Executing trades...", end=" ")
            if not self.execute_trades(trade_date):
                print("❌ FAILED - Skipping day")
                continue
            print("✓")

            # Calculate metrics
            print("   Calculating metrics...", end=" ")
            metrics = self.calculate_daily_metrics(trade_date, preserve_portfolio=preserve_portfolio)
            self.save_daily_metrics(metrics)
            print(f"✓ (Portfolio: ${metrics['total_value']:,.2f}, Return: {metrics['cumulative_return']:+.2f}%)")
            print()

        # Step 4: Generate report
        self.generate_report()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Run backtest over a date range')
    parser.add_argument('--start-date', required=True, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', required=True, help='End date (YYYY-MM-DD)')
    parser.add_argument('--preserve-portfolio', action='store_true',
                        help='Preserve existing portfolio state (for month-by-month training)')

    args = parser.parse_args()

    try:
        start_date = datetime.strptime(args.start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(args.end_date, '%Y-%m-%d').date()

        if start_date > end_date:
            raise ValueError("Start date must be before end date")

        backtest = Backtest(start_date, end_date)
        backtest.run(preserve_portfolio=args.preserve_portfolio)
        backtest.close()
        return 0
    except Exception as e:
        print(f"❌ Backtest failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())