/**
 * Portfolio Service
 * Handles portfolio holdings and position data
 */

import { query } from '@/lib/db';
import { Portfolio, PriceHistory, DailySignal } from '@/types/models';
import { PortfolioSummary, PortfolioWithMetrics } from '@/types/api';

export class PortfolioService {
  /**
   * Get current portfolio with calculated metrics
   */
  static async getPortfolioWithMetrics(): Promise<PortfolioSummary> {
    // Get current holdings
    const portfolioResult = await query<Portfolio>(
      `SELECT * FROM portfolio WHERE quantity > 0 ORDER BY symbol`
    );

    // Get latest prices
    const latestPricesResult = await query<PriceHistory>(
      `SELECT DISTINCT ON (symbol) symbol, close_price, date
       FROM price_history
       WHERE symbol = ANY($1)
       ORDER BY symbol, date DESC`,
      [portfolioResult.rows.map(p => p.symbol)]
    );

    const priceMap = new Map(
      latestPricesResult.rows.map(p => [p.symbol, p.close_price])
    );

    // Get today's signal for pending changes
    const signalResult = await query<DailySignal>(
      `SELECT allocations
       FROM daily_signals
       WHERE trade_date = CURRENT_DATE
       LIMIT 1`
    );

    const todaySignal = signalResult.rows[0];
    const pendingAllocations = todaySignal?.allocations?.assets || {};

    // Calculate metrics for each position
    const positions: PortfolioWithMetrics[] = portfolioResult.rows.map(position => {
      const currentPrice = priceMap.get(position.symbol) || position.avg_cost;
      const marketValue = position.quantity * currentPrice;
      const costBasis = position.quantity * position.avg_cost;
      const unrealizedPnl = marketValue - costBasis;
      const unrealizedPnlPct = costBasis > 0 ? (unrealizedPnl / costBasis) * 100 : 0;

      // Calculate pending quantity change from today's signal
      let pendingQuantityChange: number | undefined;
      const pendingAllocation = pendingAllocations[position.symbol];
      if (pendingAllocation && currentPrice > 0) {
        const targetQuantity = pendingAllocation.allocation / currentPrice;
        pendingQuantityChange = targetQuantity - position.quantity;
      }

      return {
        ...position,
        current_price: currentPrice,
        market_value: marketValue,
        unrealized_pnl: unrealizedPnl,
        unrealized_pnl_pct: unrealizedPnlPct,
        pending_quantity_change: pendingQuantityChange,
      };
    });

    const totalValue = positions.reduce((sum, p) => sum + p.market_value, 0);
    const totalCost = positions.reduce((sum, p) => sum + (p.quantity * p.avg_cost), 0);
    const totalPnl = totalValue - totalCost;
    const totalPnlPct = totalCost > 0 ? (totalPnl / totalCost) * 100 : 0;

    // Get cash balance from latest performance metrics
    const cashResult = await query<{ cash_balance: number }>(
      `SELECT cash_balance FROM performance_metrics
       ORDER BY date DESC LIMIT 1`
    );
    const cashBalance = cashResult.rows[0]?.cash_balance || 0;

    return {
      positions,
      total_value: totalValue,
      total_cost: totalCost,
      total_pnl: totalPnl,
      total_pnl_pct: totalPnlPct,
      cash_balance: cashBalance,
      last_updated: positions[0]?.last_updated || new Date().toISOString(),
    };
  }

  /**
   * Get portfolio holdings for a specific date
   */
  static async getPortfolioByDate(date: string): Promise<Portfolio[]> {
    // This would require historical portfolio snapshots
    // For now, we'll return current portfolio
    const result = await query<Portfolio>(
      `SELECT * FROM portfolio WHERE quantity > 0 ORDER BY symbol`
    );

    return result.rows;
  }
}
