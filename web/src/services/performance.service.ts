/**
 * Performance Service
 * Handles P&L and performance metrics data retrieval
 */

import { query } from '@/lib/db';
import { PerformanceMetrics } from '@/types/models';
import { PnLChartData, PnLDataPoint } from '@/types/api';
import { getYTDStartDate, getDaysAgo } from '@/utils/format';

export class PerformanceService {
  /**
   * Get P&L data for chart visualization
   */
  static async getPnLData(timeRange: string): Promise<PnLChartData> {
    let startDate: string;

    switch (timeRange) {
      case 'YTD':
        startDate = getYTDStartDate();
        break;
      case 'ALL':
        startDate = '2000-01-01'; // Get all data
        break;
      case '1M':
        startDate = getDaysAgo(30);
        break;
      case '3M':
        startDate = getDaysAgo(90);
        break;
      case '6M':
        startDate = getDaysAgo(180);
        break;
      case '1Y':
        startDate = getDaysAgo(365);
        break;
      case '2Y':
        startDate = getDaysAgo(730);
        break;
      case '5Y':
        startDate = getDaysAgo(1825);
        break;
      default:
        startDate = getDaysAgo(365);
    }

    const result = await query<PerformanceMetrics>(
      `SELECT
        date,
        total_value,
        daily_return,
        cumulative_return,
        sharpe_ratio,
        max_drawdown
       FROM performance_metrics
       WHERE date >= $1
       ORDER BY date ASC`,
      [startDate]
    );

    if (result.rows.length === 0) {
      return {
        data: [],
        start_date: startDate,
        end_date: new Date().toISOString().split('T')[0],
        total_return: 0,
        total_return_pct: 0,
        max_drawdown: 0,
        sharpe_ratio: null,
      };
    }

    const data: PnLDataPoint[] = result.rows.map(row => ({
      date: row.date,
      value: row.total_value,
      daily_return: row.daily_return || 0,
      cumulative_return: row.cumulative_return || 0,
    }));

    const firstValue = data[0]?.value || 0;
    const lastValue = data[data.length - 1]?.value || 0;
    const totalReturn = lastValue - firstValue;
    const totalReturnPct = firstValue > 0 ? ((totalReturn / firstValue) * 100) : 0;

    const lastMetrics = result.rows[result.rows.length - 1];

    return {
      data,
      start_date: startDate,
      end_date: data[data.length - 1]?.date || new Date().toISOString().split('T')[0],
      total_return: totalReturn,
      total_return_pct: totalReturnPct,
      max_drawdown: lastMetrics.max_drawdown || 0,
      sharpe_ratio: lastMetrics.sharpe_ratio,
    };
  }

  /**
   * Get latest performance metrics
   */
  static async getLatestMetrics(): Promise<PerformanceMetrics | null> {
    const result = await query<PerformanceMetrics>(
      `SELECT * FROM performance_metrics
       ORDER BY date DESC
       LIMIT 1`
    );

    return result.rows[0] || null;
  }

  /**
   * Get performance metrics for a specific date
   */
  static async getMetricsByDate(date: string): Promise<PerformanceMetrics | null> {
    const result = await query<PerformanceMetrics>(
      `SELECT * FROM performance_metrics
       WHERE date = $1`,
      [date]
    );

    return result.rows[0] || null;
  }
}
