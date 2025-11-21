/**
 * Prices Service
 * Handles price history data retrieval
 */

import { query } from '@/lib/db';
import { PriceHistory } from '@/types/models';
import { PriceHistoryResponse } from '@/types/api';
import { getDaysAgo } from '@/utils/format';

export class PricesService {
  /**
   * Get latest prices for all assets
   */
  static async getLatestPrices(): Promise<Record<string, number>> {
    const result = await query<Pick<PriceHistory, 'symbol' | 'close_price'>>(
      `SELECT DISTINCT ON (symbol) symbol, close_price
       FROM price_history
       ORDER BY symbol, date DESC`
    );

    return result.rows.reduce((acc, row) => {
      acc[row.symbol] = row.close_price;
      return acc;
    }, {} as Record<string, number>);
  }

  /**
   * Get price history for a specific symbol
   */
  static async getPriceHistory(
    symbol: string,
    days: number = 30
  ): Promise<PriceHistoryResponse> {
    const startDate = getDaysAgo(days);
    const endDate = new Date().toISOString().split('T')[0];

    const result = await query<PriceHistory>(
      `SELECT * FROM price_history
       WHERE symbol = $1
         AND date >= $2
         AND date <= $3
       ORDER BY date ASC`,
      [symbol, startDate, endDate]
    );

    return {
      prices: result.rows,
      symbol,
      start_date: startDate,
      end_date: endDate,
    };
  }

  /**
   * Get price for a specific symbol and date
   */
  static async getPriceByDate(symbol: string, date: string): Promise<number | null> {
    const result = await query<Pick<PriceHistory, 'close_price'>>(
      `SELECT close_price FROM price_history
       WHERE symbol = $1 AND date = $2`,
      [symbol, date]
    );

    return result.rows[0]?.close_price || null;
  }
}
