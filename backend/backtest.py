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
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
DAILY_BUDGET = Decimal("1000.00")


class Backtest:
    def __init__(self, start_date: date, end_date: date):
        self.conn = psycopg2.connect(DATABASE_URL)
        self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        self.start_date = start_date
        self.end_date = end_date
        self.trading_days = []
        
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
    
    def clear_backtest_data(self):
        """Clear any existing backtest data for this date range"""
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
        
        # Clear portfolio (reset to clean state)
        self.cursor.execute("DELETE FROM portfolio")
        
        # Clear performance metrics
        self.cursor.execute("""
            DELETE FROM performance_metrics 
            WHERE date >= %s AND date <= %s
        """, (self.start_date, self.end_date))
        
        self.conn.commit()
        print("   ✓ Cleared signals, trades, portfolio, and performance metrics\n")
    
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
    
    def calculate_daily_metrics(self, trade_date: date) -> Dict:
        """Calculate performance metrics for a given day"""
        # Get current portfolio value
        self.cursor.execute("""
            SELECT
                symbol,
                quantity,
                avg_cost
            FROM portfolio
        """)
        positions = self.cursor.fetchall()

        # Get closing prices for the day
        self.cursor.execute("""
            SELECT symbol, close_price
            FROM price_history
            WHERE date = %s
        """, (trade_date,))
        prices = {row['symbol']: Decimal(str(row['close_price'])) for row in self.cursor.fetchall()}

        # Calculate portfolio value
        portfolio_value = Decimal(0)
        total_cost = Decimal(0)

        for pos in positions:
            symbol = pos['symbol']
            qty = Decimal(str(pos['quantity']))
            avg_cost = Decimal(str(pos['avg_cost']))

            current_price = prices.get(symbol, Decimal(0))
            position_value = qty * current_price
            position_cost = qty * avg_cost

            portfolio_value += position_value
            total_cost += position_cost

        # Calculate total capital injected (sum of all BUY trades up to this date within backtest range)
        self.cursor.execute("""
            SELECT SUM(amount) as total_injected
            FROM trades
            WHERE trade_date >= %s AND trade_date <= %s AND action = 'BUY'
        """, (self.start_date, trade_date))
        result = self.cursor.fetchone()
        cash_injected = Decimal(str(result['total_injected'])) if result['total_injected'] else Decimal(0)

        # Get cash from sells (within backtest range)
        self.cursor.execute("""
            SELECT SUM(amount) as total_proceeds
            FROM trades
            WHERE trade_date >= %s AND trade_date <= %s AND action = 'SELL'
        """, (self.start_date, trade_date))
        result = self.cursor.fetchone()
        cash_from_sells = Decimal(str(result['total_proceeds'])) if result['total_proceeds'] else Decimal(0)
        
        # Total value = portfolio + cash from sells
        total_value = portfolio_value + cash_from_sells
        
        # Daily return (vs previous day within backtest range)
        self.cursor.execute("""
            SELECT total_value
            FROM performance_metrics
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
        
        # Cumulative return (vs total injected capital)
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
        final_value = Decimal(str(last_day['total_value']))
        
        self.cursor.execute("""
            SELECT SUM(amount) as total_injected
            FROM trades
            WHERE trade_date >= %s AND trade_date <= %s
            AND action = 'BUY'
        """, (self.start_date, self.end_date))
        result = self.cursor.fetchone()
        total_injected = Decimal(str(result['total_injected'])) if result['total_injected'] else Decimal(0)
        
        total_return = final_value - total_injected
        total_return_pct = (total_return / total_injected * 100) if total_injected > 0 else Decimal(0)
        
        # Calculate total account value (including unused cash)
        total_capital_received = DAILY_BUDGET * total_days
        unused_cash = total_capital_received - total_injected
        total_account_value = final_value + unused_cash
        account_return = total_account_value - total_capital_received
        account_return_pct = (account_return / total_capital_received * 100) if total_capital_received > 0 else Decimal(0)
        
        # Calculate benchmark returns (100% invested in single asset daily)
        benchmarks = {}
        for symbol in ['SPY', 'QQQ', 'DIA']:
            total_shares = Decimal(0)
            
            # Simulate buying $1000 worth each trading day at opening price
            for trade_date in self.trading_days:
                self.cursor.execute("""
                    SELECT open_price FROM price_history
                    WHERE symbol = %s AND date = %s
                """, (symbol, trade_date))
                row = self.cursor.fetchone()
                
                if row:
                    open_price = Decimal(str(row['open_price']))
                    shares_bought = DAILY_BUDGET / open_price
                    total_shares += shares_bought
            
            # Value all shares at end date's closing price
            self.cursor.execute("""
                SELECT close_price FROM price_history
                WHERE symbol = %s AND date = %s
            """, (symbol, self.end_date))
            end_row = self.cursor.fetchone()
            
            if end_row:
                end_price = Decimal(str(end_row['close_price']))
                benchmark_value = total_shares * end_price
                benchmark_return = benchmark_value - total_capital_received
                benchmark_return_pct = (benchmark_return / total_capital_received * 100) if total_capital_received > 0 else Decimal(0)
                
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
        
        print_and_save(f"Trading Days: {total_days}")
        print_and_save(f"\n💰 ACTIVE INVESTMENT PERFORMANCE")
        print_and_save(f"Capital Injected: ${total_injected:,.2f}")
        print_and_save(f"Portfolio Value: ${final_value:,.2f}")
        print_and_save(f"P&L (Invested): ${total_return:,.2f} ({total_return_pct:+.2f}%)")
        
        print_and_save(f"\n💼 TOTAL ACCOUNT PERFORMANCE")
        print_and_save(f"Total Capital Received: ${total_capital_received:,.2f}")
        print_and_save(f"   Invested: ${total_injected:,.2f}")
        print_and_save(f"   Unused Cash: ${unused_cash:,.2f}")
        print_and_save(f"Total Account Value: ${total_account_value:,.2f}")
        print_and_save(f"P&L (Total Account): ${account_return:,.2f} ({account_return_pct:+.2f}%)")
        
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
        
        self.cursor.execute("SELECT * FROM portfolio ORDER BY symbol")
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
            print_and_save("No positions (all cash)")
        
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
    
    def run(self):
        """Run complete backtest"""
        print(f"\n{'='*60}")
        print(f"🚀 STARTING BACKTEST: {self.start_date} to {self.end_date}")
        print(f"{'='*60}\n")
        
        # Step 1: Get trading days
        print("📅 Loading trading days...")
        self.trading_days = self.get_trading_days()
        print(f"   Found {len(self.trading_days)} trading days\n")
        
        # Step 2: Clear old data
        self.clear_backtest_data()
        
        # Step 3: Run backtest for each day
        print("🔄 Running daily simulations...\n")
        for i, trade_date in enumerate(self.trading_days, 1):
            print(f"Day {i}/{len(self.trading_days)}: {trade_date}")
            
            # Generate signal
            print("   Generating signal...", end=" ")
            if not self.generate_signal(trade_date):
                print("❌ FAILED")
                continue
            print("✓")
            
            # Execute trades
            print("   Executing trades...", end=" ")
            if not self.execute_trades(trade_date):
                print("❌ FAILED")
                continue
            print("✓")
            
            # Calculate metrics
            print("   Calculating metrics...", end=" ")
            metrics = self.calculate_daily_metrics(trade_date)
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
    
    args = parser.parse_args()
    
    try:
        start_date = datetime.strptime(args.start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(args.end_date, '%Y-%m-%d').date()
        
        if start_date > end_date:
            raise ValueError("Start date must be before end date")
        
        backtest = Backtest(start_date, end_date)
        backtest.run()
        backtest.close()
        return 0
    except Exception as e:
        print(f"❌ Backtest failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())