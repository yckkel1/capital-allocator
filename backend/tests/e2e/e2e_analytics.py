"""
E2E Analytics module that uses test tables instead of production tables.
Simplified version of analytics.py for E2E testing.
"""
import os
import sys
import math
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

RISK_FREE_RATE = Decimal("0.05")


class E2EAnalytics:
    """E2E Analytics that uses test tables"""

    def __init__(self, start_date: date, end_date: date, report_dir: str = None):
        self.conn = psycopg2.connect(DATABASE_URL)
        self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        self.start_date = start_date
        self.end_date = end_date

        # Set report directory
        if report_dir is None:
            report_dir = Path(__file__).parent.parent.parent.parent / 'data' / 'test-reports' / 'analytics'
        self.report_dir = Path(report_dir)
        self.report_dir.mkdir(parents=True, exist_ok=True)

        # Load daily budget from test config
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

    def get_performance_data(self) -> List[Dict]:
        """Get performance metrics from test tables"""
        self.cursor.execute("""
            SELECT * FROM test_performance_metrics
            WHERE date >= %s AND date <= %s
            ORDER BY date
        """, (self.start_date, self.end_date))
        return self.cursor.fetchall()

    def calculate_sharpe_ratio(self, daily_returns: List[float]) -> float:
        """Calculate Sharpe Ratio"""
        if not daily_returns or len(daily_returns) < 2:
            return 0.0

        mean_return = sum(daily_returns) / len(daily_returns)
        variance = sum((r - mean_return) ** 2 for r in daily_returns) / (len(daily_returns) - 1)
        std_dev = math.sqrt(variance)

        if std_dev == 0:
            return 0.0

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

    def generate_report(self) -> Dict:
        """Generate analytics report and return metrics"""
        report_lines = []

        report_lines.append(f"\n{'='*60}")
        report_lines.append(f"E2E ANALYTICS REPORT: {self.start_date} to {self.end_date}")
        report_lines.append(f"{'='*60}\n")

        performance_data = self.get_performance_data()

        if not performance_data:
            report_lines.append("No performance data found for this date range")
            self._save_report(report_lines)
            return {'error': 'No data'}

        trading_days = len(performance_data)
        years = trading_days / 252

        # Calculate total return
        total_capital_received = self.daily_budget * trading_days

        self.cursor.execute("""
            SELECT COALESCE(SUM(amount), 0) as total_spent
            FROM test_trades
            WHERE trade_date >= %s AND trade_date <= %s AND action = 'BUY'
        """, (self.start_date, self.end_date))
        total_spent = Decimal(str(self.cursor.fetchone()['total_spent']))

        self.cursor.execute("""
            SELECT COALESCE(SUM(amount), 0) as total_proceeds
            FROM test_trades
            WHERE trade_date >= %s AND trade_date <= %s AND action = 'SELL'
        """, (self.start_date, self.end_date))
        cash_from_sells = Decimal(str(self.cursor.fetchone()['total_proceeds']))

        last_portfolio_value = Decimal(str(performance_data[-1]['portfolio_value']))
        unused_cash = total_capital_received - total_spent + cash_from_sells
        total_account_value = last_portfolio_value + unused_cash

        total_return = total_account_value - total_capital_received
        total_return_pct = float(total_return / total_capital_received * 100) if total_capital_received > 0 else 0

        # Calculate daily returns
        daily_returns = []
        for i in range(1, len(performance_data)):
            prev_portfolio = Decimal(str(performance_data[i-1]['portfolio_value']))
            curr_portfolio = Decimal(str(performance_data[i]['portfolio_value']))

            trade_date = performance_data[i]['date']
            self.cursor.execute("""
                SELECT COALESCE(SUM(amount), 0) as invested_today
                FROM test_trades
                WHERE trade_date = %s AND action = 'BUY'
            """, (trade_date,))
            invested_today = Decimal(str(self.cursor.fetchone()['invested_today']))

            if prev_portfolio > 0:
                portfolio_change = curr_portfolio - prev_portfolio - invested_today
                daily_ret = float(portfolio_change / prev_portfolio * 100)
                daily_returns.append(daily_ret)

        sharpe_ratio = self.calculate_sharpe_ratio(daily_returns)
        max_drawdown_info = self.calculate_max_drawdown(performance_data)

        # Calculate volatility
        if len(daily_returns) > 1:
            mean_return = sum(daily_returns) / len(daily_returns)
            variance = sum((r - mean_return) ** 2 for r in daily_returns) / (len(daily_returns) - 1)
            daily_volatility = math.sqrt(variance)
            annualized_volatility = daily_volatility * math.sqrt(252)
        else:
            annualized_volatility = 0

        report_lines.append(f"STRATEGY PERFORMANCE")
        report_lines.append(f"Trading Days: {trading_days}")
        report_lines.append(f"Total Return: {total_return_pct:+.2f}%")
        report_lines.append(f"Annualized Return: {total_return_pct / years if years > 0 else 0:+.2f}%")
        report_lines.append(f"Sharpe Ratio: {sharpe_ratio:.3f}")
        report_lines.append(f"Volatility (annualized): {annualized_volatility:.2f}%")
        report_lines.append(f"Max Drawdown: {max_drawdown_info['max_drawdown']:.2f}%")
        report_lines.append(f"\n{'='*60}\n")

        report_file = self._save_report(report_lines)

        return {
            'trading_days': trading_days,
            'total_return_pct': total_return_pct,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown_info['max_drawdown'],
            'volatility': annualized_volatility,
            'report_file': report_file
        }

    def _save_report(self, report_lines: list) -> str:
        """Save report to file"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"e2e_analytics_{self.start_date}_to_{self.end_date}_{timestamp}.txt"
        filepath = self.report_dir / filename

        with open(filepath, 'w') as f:
            f.write('\n'.join(report_lines))

        return str(filepath)

    def run(self) -> Dict:
        """Run analytics and return results"""
        return self.generate_report()
