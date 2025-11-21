/**
 * Trades Service
 * Handles trade history and execution data
 */

import { query } from '@/lib/db';
import { Trade } from '@/types/models';
import { TradesResponse } from '@/types/api';
import { getDaysAgo } from '@/utils/format';

export class TradesService {
  /**
   * Get trade history with optional filtering
   */
  static async getTrades(days: number = 14): Promise<TradesResponse> {
    const startDate = getDaysAgo(days);
    const endDate = new Date().toISOString().split('T')[0];

    const result = await query<Trade>(
      `SELECT * FROM trades
       WHERE trade_date >= $1 AND trade_date <= $2
       ORDER BY trade_date DESC, executed_at DESC`,
      [startDate, endDate]
    );

    return {
      trades: result.rows,
      total_count: result.rowCount || 0,
      start_date: startDate,
      end_date: endDate,
    };
  }

  /**
   * Get trades for a specific date
   */
  static async getTradesByDate(date: string): Promise<Trade[]> {
    const result = await query<Trade>(
      `SELECT * FROM trades
       WHERE trade_date = $1
       ORDER BY executed_at ASC`,
      [date]
    );

    return result.rows;
  }

  /**
   * Get trades by symbol
   */
  static async getTradesBySymbol(symbol: string, days: number = 30): Promise<Trade[]> {
    const startDate = getDaysAgo(days);

    const result = await query<Trade>(
      `SELECT * FROM trades
       WHERE symbol = $1 AND trade_date >= $2
       ORDER BY trade_date DESC`,
      [symbol, startDate]
    );

    return result.rows;
  }

  /**
   * Get trade statistics
   */
  static async getTradeStats(days: number = 30): Promise<{
    total_trades: number;
    buy_count: number;
    sell_count: number;
    total_volume: number;
  }> {
    const startDate = getDaysAgo(days);

    const result = await query<{
      total_trades: number;
      buy_count: number;
      sell_count: number;
      total_volume: number;
    }>(
      `SELECT
        COUNT(*) as total_trades,
        SUM(CASE WHEN action = 'BUY' THEN 1 ELSE 0 END) as buy_count,
        SUM(CASE WHEN action = 'SELL' THEN 1 ELSE 0 END) as sell_count,
        SUM(amount) as total_volume
       FROM trades
       WHERE trade_date >= $1`,
      [startDate]
    );

    return result.rows[0] || {
      total_trades: 0,
      buy_count: 0,
      sell_count: 0,
      total_volume: 0,
    };
  }
}
