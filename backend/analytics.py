"""
Analytics Script
Calculates risk-adjusted performance metrics from backtest results
"""
import os
import sys
import argparse
from datetime import datetime, date
from decimal import Decimal
from typing import List, Dict
import math

import psycopg2
from psycopg2.extras import RealDictCursor

# Import configuration
from config import get_settings, get_trading_config

settings = get_settings()
DATABASE_URL = settings.database_url
RISK_FREE_RATE = Decimal("0.05")  # 5% annual risk-free rate


class Analytics:
    def __init__(self, start_date: date, end_date: date):
        self.conn = psycopg2.connect(DATABASE_URL)
        self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        self.start_date = start_date
        self.end_date = end_date
        # Load daily budget from trading config
        trading_config = get_trading_config(start_date)
        self.daily_budget = Decimal(str(trading_config.daily_capital))
        
    def close(self):
        self.cursor.close()
        self.conn.close()
    
    def get_performance_data(self) -> List[Dict]:
        """Get performance metrics for date range"""
        self.cursor.execute("""
            SELECT * FROM performance_metrics
            WHERE date >= %s AND date <= %s
            ORDER BY date
        """, (self.start_date, self.end_date))
        
        return self.cursor.fetchall()
    
    def get_trading_days(self) -> List[date]:
        """Get all trading days in date range"""
        self.cursor.execute("""
            SELECT DISTINCT date FROM price_history
            WHERE date >= %s AND date <= %s
            AND symbol = 'SPY'
            ORDER BY date
        """, (self.start_date, self.end_date))
        
        return [row['date'] for row in self.cursor.fetchall()]
    
    def calculate_benchmark_returns(self, symbol: str) -> Dict:
        """Calculate daily returns for benchmark symbol"""
        trading_days = self.get_trading_days()
        
        daily_returns = []
        total_shares = Decimal(0)
        prev_value = Decimal(0)
        
        for i, trade_date in enumerate(trading_days):
            # Buy $1000 worth at opening
            self.cursor.execute("""
                SELECT open_price, close_price FROM price_history
                WHERE symbol = %s AND date = %s
            """, (symbol, trade_date))
            
            row = self.cursor.fetchone()
            if not row:
                continue
            
            open_price = Decimal(str(row['open_price']))
            close_price = Decimal(str(row['close_price']))
            
            shares_bought = self.daily_budget / open_price
            total_shares += shares_bought

            # Current portfolio value
            curr_value = total_shares * close_price

            # Daily return (excluding today's capital injection)
            if i > 0 and prev_value > 0:
                portfolio_change = curr_value - prev_value - self.daily_budget
                daily_ret = float(portfolio_change / prev_value * 100)
                daily_returns.append(daily_ret)

            prev_value = curr_value

        total_invested = self.daily_budget * len(trading_days)
        final_value = total_shares * close_price  # Using last close_price from loop
        total_return = final_value - total_invested
        total_return_pct = float(total_return / total_invested * 100) if total_invested > 0 else 0
        
        return {
            'daily_returns': daily_returns,
            'total_return_pct': total_return_pct,
            'final_value': float(final_value)
        }
    
    def calculate_sharpe_ratio(self, daily_returns: List[float], trading_days: int) -> float:
        """Calculate Sharpe Ratio (annualized)"""
        if not daily_returns or len(daily_returns) < 2:
            return 0.0
        
        # Calculate mean and std dev of daily returns
        mean_return = sum(daily_returns) / len(daily_returns)
        variance = sum((r - mean_return) ** 2 for r in daily_returns) / (len(daily_returns) - 1)
        std_dev = math.sqrt(variance)
        
        if std_dev == 0:
            return 0.0
        
        # Annualize (assuming ~252 trading days per year)
        daily_risk_free = float(RISK_FREE_RATE) / 252
        annualized_return = mean_return * 252
        annualized_std = std_dev * math.sqrt(252)
        
        sharpe = (annualized_return - float(RISK_FREE_RATE)) / annualized_std if annualized_std > 0 else 0
        
        return sharpe
    
    def calculate_max_drawdown(self, performance_data: List[Dict]) -> Dict:
        """Calculate maximum drawdown"""
        if not performance_data:
            return {'max_drawdown': 0, 'peak_date': None, 'trough_date': None}
        
        peak_value = Decimal(0)
        max_drawdown = Decimal(0)
        peak_date = None
        trough_date = None
        
        for data in performance_data:
            value = Decimal(str(data['total_value']))
            current_date = data['date']
            
            if value > peak_value:
                peak_value = value
                peak_date = current_date
            
            drawdown = (peak_value - value) / peak_value * 100 if peak_value > 0 else Decimal(0)
            
            if drawdown > max_drawdown:
                max_drawdown = drawdown
                trough_date = current_date
        
        return {
            'max_drawdown': float(max_drawdown),
            'peak_date': peak_date,
            'trough_date': trough_date
        }
    
    def calculate_calmar_ratio(self, total_return_pct: float, max_drawdown: float, years: float) -> float:
        """Calculate Calmar Ratio (annualized return / max drawdown)"""
        if max_drawdown == 0 or max_drawdown < 0.01:
            return float('inf')  # Return infinity if no meaningful drawdown
        
        annualized_return = total_return_pct / years
        return annualized_return / max_drawdown
    
    def generate_report(self):
        """Generate analytics report"""
        report_lines = []
        
        def print_and_save(text=""):
            print(text)
            report_lines.append(text)
        
        print_and_save(f"\n{'='*60}")
        print_and_save(f"📊 ANALYTICS REPORT: {self.start_date} to {self.end_date}")
        print_and_save(f"{'='*60}\n")
        
        # Get performance data
        performance_data = self.get_performance_data()
        
        if not performance_data:
            print_and_save("❌ No performance data found for this date range")
            print_and_save("Run backtest.py first to generate data\n")
            return
        
        trading_days = len(performance_data)
        years = trading_days / 252  # Approximate years
        
        # Calculate total account value properly (portfolio + unused cash)
        total_capital_received = self.daily_budget * trading_days
        
        # Get how much was actually invested
        self.cursor.execute("""
            SELECT COALESCE(SUM(amount), 0) as total_spent
            FROM trades
            WHERE trade_date >= %s AND trade_date <= %s
            AND action = 'BUY'
        """, (self.start_date, self.end_date))
        result = self.cursor.fetchone()
        total_spent = Decimal(str(result['total_spent']))
        
        # Get cash from sells
        self.cursor.execute("""
            SELECT COALESCE(SUM(amount), 0) as total_proceeds
            FROM trades
            WHERE trade_date >= %s AND trade_date <= %s
            AND action = 'SELL'
        """, (self.start_date, self.end_date))
        result = self.cursor.fetchone()
        cash_from_sells = Decimal(str(result['total_proceeds']))
        
        # Final portfolio value
        last_portfolio_value = Decimal(str(performance_data[-1]['portfolio_value']))
        
        # Total account value = portfolio + unused cash + cash from sells
        unused_cash = total_capital_received - total_spent + cash_from_sells
        total_account_value = last_portfolio_value + unused_cash
        
        total_return = total_account_value - total_capital_received
        total_return_pct = float(total_return / total_capital_received * 100) if total_capital_received > 0 else 0
        
        # Calculate daily returns based on portfolio performance (excluding capital injections)
        daily_returns = []
        
        for i in range(1, len(performance_data)):
            prev_portfolio = Decimal(str(performance_data[i-1]['portfolio_value']))
            curr_portfolio = Decimal(str(performance_data[i]['portfolio_value']))
            
            # Get capital invested today
            trade_date = performance_data[i]['date']
            self.cursor.execute("""
                SELECT COALESCE(SUM(amount), 0) as invested_today
                FROM trades
                WHERE trade_date = %s AND action = 'BUY'
            """, (trade_date,))
            invested_today = Decimal(str(self.cursor.fetchone()['invested_today']))
            
            # Get proceeds from sells today
            self.cursor.execute("""
                SELECT COALESCE(SUM(amount), 0) as sold_today
                FROM trades
                WHERE trade_date = %s AND action = 'SELL'
            """, (trade_date,))
            sold_today = Decimal(str(self.cursor.fetchone()['sold_today']))
            
            # Portfolio change = curr - prev - new capital + sells
            # (sells reduce portfolio but give cash, so add them back)
            if prev_portfolio > 0:
                portfolio_change = curr_portfolio - prev_portfolio - invested_today + sold_today
                daily_ret = float(portfolio_change / prev_portfolio * 100)
                daily_returns.append(daily_ret)
            elif curr_portfolio > 0:
                # First day with investment
                daily_ret = float((curr_portfolio - invested_today) / invested_today * 100) if invested_today > 0 else 0
                daily_returns.append(daily_ret)
        
        strategy_sharpe = self.calculate_sharpe_ratio(daily_returns, trading_days)
        
        # Calculate max drawdown using full account values (portfolio + unused cash)
        account_values = []
        for i, perf in enumerate(performance_data):
            day_num = i + 1
            capital_received_to_date = self.daily_budget * day_num
            
            # Get spent up to this date
            self.cursor.execute("""
                SELECT COALESCE(SUM(amount), 0) as spent
                FROM trades
                WHERE trade_date <= %s AND action = 'BUY'
                AND trade_date >= %s
            """, (perf['date'], self.start_date))
            spent = Decimal(str(self.cursor.fetchone()['spent']))
            
            # Get proceeds from sells up to this date
            self.cursor.execute("""
                SELECT COALESCE(SUM(amount), 0) as proceeds
                FROM trades
                WHERE trade_date <= %s AND action = 'SELL'
                AND trade_date >= %s
            """, (perf['date'], self.start_date))
            proceeds = Decimal(str(self.cursor.fetchone()['proceeds']))
            
            portfolio_val = Decimal(str(perf['portfolio_value']))
            unused_cash = capital_received_to_date - spent + proceeds
            account_val = portfolio_val + unused_cash
            
            account_values.append({'total_value': float(account_val), 'date': perf['date']})
        
        strategy_drawdown = self.calculate_max_drawdown(account_values)
        
        # Calculate volatility (annualized)
        if len(daily_returns) > 1:
            mean_return = sum(daily_returns) / len(daily_returns)
            variance = sum((r - mean_return) ** 2 for r in daily_returns) / (len(daily_returns) - 1)
            daily_volatility = math.sqrt(variance)
            annualized_volatility = daily_volatility * math.sqrt(252)
        else:
            annualized_volatility = 0
        
        strategy_calmar = self.calculate_calmar_ratio(
            total_return_pct, 
            strategy_drawdown['max_drawdown'],
            years
        )
        
        print_and_save(f"📈 STRATEGY PERFORMANCE")
        print_and_save(f"Total Return: {total_return_pct:+.2f}%")
        print_and_save(f"Annualized Return: {total_return_pct / years:+.2f}%")
        print_and_save(f"Sharpe Ratio: {strategy_sharpe:.3f}")
        print_and_save(f"Volatility (annualized): {annualized_volatility:.2f}%")
        print_and_save(f"Max Drawdown: {strategy_drawdown['max_drawdown']:.2f}%")
        if strategy_drawdown['peak_date'] and strategy_drawdown['trough_date']:
            print_and_save(f"  Peak: {strategy_drawdown['peak_date']}, Trough: {strategy_drawdown['trough_date']}")
        calmar_display = "N/A" if math.isinf(strategy_calmar) else f"{strategy_calmar:.3f}"
        print_and_save(f"Calmar Ratio: {calmar_display}")
        
        # Benchmark metrics
        print_and_save(f"\n📊 BENCHMARK COMPARISON")
        print_and_save(f"{'Symbol':<10} {'Return':<12} {'Sharpe':<12} {'Volatility':<12} {'Max DD':<12} {'Calmar':<12}")
        print_and_save("-" * 60)
        
        # Strategy row
        calmar_str = "N/A" if math.isinf(strategy_calmar) else f"{strategy_calmar:>10.3f}"
        print_and_save(f"{'Strategy':<10} {total_return_pct:>10.2f}%  {strategy_sharpe:>10.3f}  {annualized_volatility:>10.2f}%  {strategy_drawdown['max_drawdown']:>10.2f}%  {calmar_str:>10}")
        
        for symbol in ['SPY', 'QQQ', 'DIA']:
            bench_data = self.calculate_benchmark_returns(symbol)
            bench_sharpe = self.calculate_sharpe_ratio(bench_data['daily_returns'], trading_days)
            
            # Calculate benchmark max drawdown using proper cumulative portfolio values
            trading_days_list = self.get_trading_days()
            bench_values = []
            total_shares = Decimal(0)
            
            for trade_date in trading_days_list:
                self.cursor.execute("""
                    SELECT open_price, close_price FROM price_history
                    WHERE symbol = %s AND date = %s
                """, (symbol, trade_date))
                
                row = self.cursor.fetchone()
                if row:
                    open_price = Decimal(str(row['open_price']))
                    close_price = Decimal(str(row['close_price']))
                    shares_bought = self.daily_budget / open_price
                    total_shares += shares_bought
                    portfolio_value = total_shares * close_price
                    bench_values.append({'total_value': float(portfolio_value), 'date': trade_date})
            
            bench_drawdown = self.calculate_max_drawdown(bench_values)
            
            # Calculate benchmark volatility
            if len(bench_data['daily_returns']) > 1:
                mean_ret = sum(bench_data['daily_returns']) / len(bench_data['daily_returns'])
                variance = sum((r - mean_ret) ** 2 for r in bench_data['daily_returns']) / (len(bench_data['daily_returns']) - 1)
                daily_vol = math.sqrt(variance)
                bench_volatility = daily_vol * math.sqrt(252)
            else:
                bench_volatility = 0
            
            bench_calmar = self.calculate_calmar_ratio(
                bench_data['total_return_pct'],
                bench_drawdown['max_drawdown'],
                years
            )
            
            bench_calmar_str = "N/A" if math.isinf(bench_calmar) else f"{bench_calmar:>10.3f}"
            
            print_and_save(f"{symbol:<10} {bench_data['total_return_pct']:>10.2f}%  {bench_sharpe:>10.3f}  {bench_volatility:>10.2f}%  {bench_drawdown['max_drawdown']:>10.2f}%  {bench_calmar_str:>10}")
        
        print_and_save(f"\n{'='*60}")
        print_and_save("\n💡 INTERPRETATION:")
        print_and_save("• Sharpe Ratio: Higher is better (>1 is good, >2 is excellent)")
        print_and_save("• Max Drawdown: Lower is better (measures worst decline)")
        print_and_save("• Calmar Ratio: Higher is better (return per unit of drawdown risk)")
        print_and_save("• Volatility: Lower means more consistent returns")
        print_and_save(f"\n{'='*60}\n")
        
        # Save report
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"analytics_report_{self.start_date}_to_{self.end_date}_{timestamp}.txt"
        
        backend_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(backend_dir)
        report_dir = os.path.join(project_root, 'data', 'analytics')
        
        os.makedirs(report_dir, exist_ok=True)
        filepath = os.path.join(report_dir, filename)
        
        with open(filepath, 'w') as f:
            f.write('\n'.join(report_lines))
        
        print(f"💾 Report saved to: {filepath}\n")
    
    def run(self):
        """Run analytics"""
        self.generate_report()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Analyze backtest performance')
    parser.add_argument('--start-date', required=True, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', required=True, help='End date (YYYY-MM-DD)')
    
    args = parser.parse_args()
    
    try:
        start_date = datetime.strptime(args.start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(args.end_date, '%Y-%m-%d').date()
        
        if start_date > end_date:
            raise ValueError("Start date must be before end date")
        
        analytics = Analytics(start_date, end_date)
        analytics.run()
        analytics.close()
        return 0
    except Exception as e:
        print(f"❌ Analytics failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())