"""
Trade Execution Script
Executes trades based on the latest signal generated

TRADING RULES:
1. Daily $1000 budget (fresh each day)
2. Can spend $0-$1000 on any combination of SPY/QQQ/DIA
3. OR sell existing holdings (no buy+sell same day)
4. Execution at opening price
5. Track cumulative positions and P&L
"""
import os
import sys
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List

import psycopg2
from psycopg2.extras import RealDictCursor

# Import configuration
from config import get_settings, get_trading_config

settings = get_settings()
DATABASE_URL = settings.database_url


class TradeExecutor:
    def __init__(self):
        self.conn = psycopg2.connect(DATABASE_URL)
        self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)

    def close(self):
        self.cursor.close()
        self.conn.close()

    def get_latest_signal(self) -> Dict:
        """Fetch the most recent trading signal"""
        self.cursor.execute("""
            SELECT * FROM daily_signals 
            ORDER BY trade_date DESC 
            LIMIT 1
        """)
        signal = self.cursor.fetchone()
        
        if not signal:
            raise Exception("No signals found in database")
        
        return dict(signal)

    def get_opening_price(self, symbol: str, date: str) -> Decimal:
        """Get opening price for a symbol on a given date"""
        self.cursor.execute("""
            SELECT open_price FROM price_history 
            WHERE symbol = %s AND date = %s
        """, (symbol, date))
        
        result = self.cursor.fetchone()
        if not result:
            raise Exception(f"No opening price found for {symbol} on {date}")
        
        return Decimal(str(result['open_price']))

    def ensure_cash_exists(self):
        """Ensure CASH entry exists in portfolio table"""
        self.cursor.execute("""
            SELECT quantity FROM portfolio WHERE symbol = 'CASH'
        """)
        result = self.cursor.fetchone()

        if not result:
            # Initialize CASH with 0
            self.cursor.execute("""
                INSERT INTO portfolio (symbol, quantity, avg_cost, last_updated)
                VALUES ('CASH', 0, 1.0, %s)
            """, (datetime.now(timezone.utc),))
            self.conn.commit()

    def get_cash_balance(self) -> Decimal:
        """Get current CASH balance from portfolio"""
        self.ensure_cash_exists()
        self.cursor.execute("""
            SELECT quantity FROM portfolio WHERE symbol = 'CASH'
        """)
        result = self.cursor.fetchone()
        return Decimal(str(result['quantity'])) if result else Decimal(0)

    def add_cash(self, amount: Decimal, description: str = ""):
        """Add cash to portfolio (from daily capital or sells)"""
        self.ensure_cash_exists()
        self.cursor.execute("""
            UPDATE portfolio
            SET quantity = quantity + %s, last_updated = %s
            WHERE symbol = 'CASH'
        """, (amount, datetime.now(timezone.utc)))
        self.conn.commit()

    def deduct_cash(self, amount: Decimal, description: str = ""):
        """Deduct cash from portfolio (for buys)"""
        self.ensure_cash_exists()
        cash_balance = self.get_cash_balance()
        if cash_balance < amount:
            raise ValueError(f"Insufficient cash: have ${cash_balance:.2f}, need ${amount:.2f}")

        self.cursor.execute("""
            UPDATE portfolio
            SET quantity = quantity - %s, last_updated = %s
            WHERE symbol = 'CASH'
        """, (amount, datetime.now(timezone.utc)))
        self.conn.commit()

    def get_current_positions(self) -> Dict[str, Dict]:
        """
        Get current positions from portfolio table (excluding CASH)
        Returns: {symbol: {'quantity': Decimal, 'avg_cost': Decimal}}
        """
        self.cursor.execute("""
            SELECT symbol, quantity, avg_cost
            FROM portfolio
            WHERE symbol != 'CASH' AND quantity > 0.0001
        """)

        positions = {}
        for row in self.cursor.fetchall():
            positions[row['symbol']] = {
                'quantity': Decimal(str(row['quantity'])),
                'avg_cost': Decimal(str(row['avg_cost']))
            }

        return positions

    def calculate_portfolio_pnl(self, positions: Dict, current_prices: Dict[str, Decimal]) -> Dict:
        """Calculate P&L for current positions"""
        total_cost = Decimal(0)
        total_value = Decimal(0)

        for symbol, pos in positions.items():
            cost = pos['quantity'] * pos['avg_cost']
            value = pos['quantity'] * current_prices.get(symbol, Decimal(0))
            total_cost += cost
            total_value += value

        pnl = total_value - total_cost
        pnl_pct = (pnl / total_cost * 100) if total_cost > 0 else Decimal(0)

        return {
            'total_cost': total_cost,
            'total_value': total_value,
            'pnl': pnl,
            'pnl_pct': pnl_pct
        }

    def execute_buy_trades(self, signal: Dict, signal_id: int, execution_date: str) -> List[Dict]:
        """
        Execute buy trades based on signal allocations
        Uses opening price of execution_date
        Deducts cash from portfolio for each purchase
        """
        trades = []
        target_allocations = signal['allocations']  # Dollar amounts

        for symbol, dollar_amount in target_allocations.items():
            if dollar_amount <= 0:
                continue

            # Get opening price for execution
            opening_price = self.get_opening_price(symbol, execution_date)

            # Calculate shares to buy
            quantity = (Decimal(str(dollar_amount)) / opening_price).quantize(Decimal('0.0001'))

            if quantity > 0:
                total_cost = quantity * opening_price

                # Deduct cash from portfolio BEFORE buying
                self.deduct_cash(total_cost, f"BUY {quantity:.4f} {symbol} @ ${opening_price:.2f}")

                # Record trade
                self.cursor.execute("""
                    INSERT INTO trades (signal_id, trade_date, executed_at, symbol, action, quantity, price, amount)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    signal_id,
                    execution_date,
                    datetime.now(timezone.utc),
                    symbol,
                    'BUY',
                    quantity,
                    opening_price,
                    total_cost
                ))

                trades.append({
                    'symbol': symbol,
                    'quantity': quantity,
                    'price': opening_price,
                    'side': 'BUY',
                    'total': total_cost
                })

        self.conn.commit()
        return trades

    def update_portfolio(self, trades: List[Dict]) -> None:
        """
        Update portfolio table with new positions
        Calculates weighted average cost for buys
        """
        for trade in trades:
            symbol = trade['symbol']
            quantity = trade['quantity']
            price = trade['price']
            side = trade['side']
            
            # Get current position
            self.cursor.execute("""
                SELECT quantity, avg_cost FROM portfolio WHERE symbol = %s
            """, (symbol,))
            
            result = self.cursor.fetchone()
            
            if side == 'BUY':
                if result:
                    # Update existing position with weighted average cost
                    old_qty = Decimal(str(result['quantity']))
                    old_avg = Decimal(str(result['avg_cost']))
                    new_qty = old_qty + quantity
                    new_avg = ((old_qty * old_avg) + (quantity * price)) / new_qty
                    
                    self.cursor.execute("""
                        UPDATE portfolio 
                        SET quantity = %s, avg_cost = %s, last_updated = %s
                        WHERE symbol = %s
                    """, (new_qty, new_avg, datetime.now(timezone.utc), symbol))
                else:
                    # Insert new position
                    self.cursor.execute("""
                        INSERT INTO portfolio (symbol, quantity, avg_cost, last_updated)
                        VALUES (%s, %s, %s, %s)
                    """, (symbol, quantity, price, datetime.now(timezone.utc)))
            
            elif side == 'SELL':
                if result:
                    old_qty = Decimal(str(result['quantity']))
                    new_qty = old_qty - quantity
                    
                    if new_qty <= Decimal('0.0001'):
                        # Remove position if fully closed
                        self.cursor.execute("DELETE FROM portfolio WHERE symbol = %s", (symbol,))
                    else:
                        # Update quantity, keep avg_cost same
                        self.cursor.execute("""
                            UPDATE portfolio 
                            SET quantity = %s, last_updated = %s
                            WHERE symbol = %s
                        """, (new_qty, datetime.now(timezone.utc), symbol))
        
        self.conn.commit()

    def execute_sell_trades(self, signal: Dict, signal_id: int, execution_date: str) -> List[Dict]:
        """
        Execute sell trades based on signal
        Sells specified percentage of holdings at opening price
        """
        trades = []
        features_used = signal['features_used']

        # Get current positions
        positions = self.get_current_positions()

        if not positions:
            print("   No positions to sell")
            return trades

        # Get sell percentage from signal (allocation_pct when action=SELL)
        allocation_pct = features_used.get('allocation_pct', 0.0)
        signal_type = features_used.get('signal_type', 'unknown')

        print(f"   Signal type: {signal_type}, Sell percentage: {allocation_pct*100:.0f}%")

        # Get asset scores for ranking which to sell first
        assets = features_used.get('assets', {})

        # Rank assets by score (sell worst performers first)
        holdings_with_scores = []
        for symbol, pos in positions.items():
            asset_data = assets.get(symbol, {})
            score = asset_data.get('score', 0)
            holdings_with_scores.append((symbol, pos, score))

        # Sort by score ascending (worst first)
        holdings_with_scores.sort(key=lambda x: x[2])

        # Sell the specified percentage of each holding (or all if weakest)
        for symbol, pos, score in holdings_with_scores:
            # Get opening price
            opening_price = self.get_opening_price(symbol, execution_date)

            # Sell based on allocation_pct from signal
            sell_quantity = (pos['quantity'] * Decimal(str(allocation_pct))).quantize(Decimal('0.0001'))

            if sell_quantity > 0:
                total_proceeds = sell_quantity * opening_price

                # Add cash to portfolio from sale proceeds
                self.add_cash(total_proceeds, f"SELL {sell_quantity:.4f} {symbol} @ ${opening_price:.2f}")

                # Record trade (negative quantity for sell)
                self.cursor.execute("""
                    INSERT INTO trades (signal_id, trade_date, executed_at, symbol, action, quantity, price, amount)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    signal_id,
                    execution_date,
                    datetime.now(timezone.utc),
                    symbol,
                    'SELL',
                    -sell_quantity,
                    opening_price,
                    total_proceeds
                ))

                trades.append({
                    'symbol': symbol,
                    'quantity': sell_quantity,
                    'price': opening_price,
                    'side': 'SELL',
                    'total': total_proceeds
                })

        self.conn.commit()
        return trades

    def run(self, execution_date: str = None) -> None:
        """
        Main execution flow

        Args:
            execution_date: Date to execute trades (YYYY-MM-DD). Uses today if not provided.
        """
        if not execution_date:
            execution_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')

        # Get trading configuration from database
        from datetime import datetime as dt
        exec_date_obj = dt.strptime(execution_date, '%Y-%m-%d').date()
        trading_config = get_trading_config(exec_date_obj)
        DAILY_BUDGET = Decimal(str(trading_config.daily_capital))

        print(f"\n{'='*60}")
        print(f"Trade Execution - {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"Execution Date: {execution_date}")
        print(f"Daily Budget: ${DAILY_BUDGET:,.2f} (from config ID: {trading_config.id})")
        print(f"{'='*60}\n")

        # Inject daily capital as CASH into portfolio
        self.add_cash(DAILY_BUDGET, f"Daily capital injection for {execution_date}")

        # 1. Get latest signal
        signal = self.get_latest_signal()
        action = signal['features_used']['action']
        allocation_pct = signal['features_used']['allocation_pct']

        print(f"📊 Latest Signal (ID: {signal['id']}):")
        print(f"   Signal Date: {signal['trade_date']}")
        print(f"   Action: {action}")
        print(f"   Budget Allocation: ${DAILY_BUDGET * Decimal(str(allocation_pct)):,.2f} ({allocation_pct * 100}%)")
        print(f"   Target Allocations: {signal['allocations']}\n")
        
        # 2. Show current portfolio state
        positions = self.get_current_positions()
        
        # Get latest prices for P&L calculation
        self.cursor.execute("""
            SELECT DISTINCT ON (symbol) symbol, close_price 
            FROM price_history 
            ORDER BY symbol, date DESC
        """)
        current_prices = {row['symbol']: Decimal(str(row['close_price'])) for row in self.cursor.fetchall()}
        
        if positions:
            pnl_data = self.calculate_portfolio_pnl(positions, current_prices)
            
            print(f"💼 Current Portfolio:")
            print(f"   Total Cost: ${pnl_data['total_cost']:,.2f}")
            print(f"   Total Value: ${pnl_data['total_value']:,.2f}")
            print(f"   P&L: ${pnl_data['pnl']:,.2f} ({pnl_data['pnl_pct']:.2f}%)")
            print(f"   Positions:")
            for symbol, pos in positions.items():
                current_value = pos['quantity'] * current_prices.get(symbol, Decimal(0))
                cost = pos['quantity'] * pos['avg_cost']
                position_pnl = current_value - cost
                print(f"      {symbol}: {pos['quantity']:.4f} shares @ ${pos['avg_cost']:.2f} avg | "
                      f"Current: ${current_value:,.2f} | P&L: ${position_pnl:,.2f}")
        else:
            print(f"💼 Current Portfolio: Empty (no positions)\n")
        
        # 3. Execute trades based on action
        print(f"\n{'='*60}")
        if action == 'BUY':
            print(f"🔄 Executing BUY orders (Budget: ${DAILY_BUDGET * Decimal(str(allocation_pct)):,.2f}):\n")
            trades = self.execute_buy_trades(signal, signal['id'], execution_date)
            
            if trades:
                # Update portfolio table
                self.update_portfolio(trades)
                
                total_spent = sum(t['total'] for t in trades)
                for trade in trades:
                    print(f"   ✅ BUY {trade['quantity']:.4f} {trade['symbol']} @ ${trade['price']:.2f} = ${trade['total']:,.2f}")
                print(f"\n   Total Spent: ${total_spent:,.2f}")
                print(f"   Cash Held: ${DAILY_BUDGET * Decimal(str(allocation_pct)) - total_spent:,.2f}")
            else:
                print("   No buy orders executed")
                
        elif action == 'SELL':
            print(f"🔄 Executing SELL orders:\n")
            trades = self.execute_sell_trades(signal, signal['id'], execution_date)
            
            if trades:
                # Update portfolio table
                self.update_portfolio(trades)
                
                total_proceeds = sum(t['total'] for t in trades)
                for trade in trades:
                    print(f"   ✅ SELL {trade['quantity']:.4f} {trade['symbol']} @ ${trade['price']:.2f} = ${trade['total']:,.2f}")
                print(f"\n   Total Proceeds: ${total_proceeds:,.2f}")
            else:
                print("   No sell orders executed")
                
        else:  # HOLD
            print(f"✋ Action: HOLD - No trades executed today")
        
        print(f"{'='*60}\n")


def main():
    """Main entry point"""
    try:
        # Allow passing execution date as command line argument
        execution_date = sys.argv[1] if len(sys.argv) > 1 else None
        
        executor = TradeExecutor()
        executor.run(execution_date)
        executor.close()
        print("✅ Trade execution completed successfully\n")
        return 0
    except Exception as e:
        print(f"❌ Error during trade execution: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())