/**
 * Signals Service
 * Handles daily trading signals and strategy decisions
 */

import { query } from '@/lib/db';
import { DailySignal } from '@/types/models';
import { StrategyDecision } from '@/types/api';
import { TradesService } from './trades.service';

export class SignalsService {
  /**
   * Get latest trading signal
   */
  static async getLatestSignal(): Promise<DailySignal | null> {
    const result = await query<DailySignal>(
      `SELECT * FROM daily_signals
       ORDER BY trade_date DESC
       LIMIT 1`
    );

    return result.rows[0] || null;
  }

  /**
   * Get signal for a specific date
   */
  static async getSignalByDate(date: string): Promise<DailySignal | null> {
    const result = await query<DailySignal>(
      `SELECT * FROM daily_signals
       WHERE trade_date = $1`,
      [date]
    );

    return result.rows[0] || null;
  }

  /**
   * Get yesterday's strategy decision (D-1)
   */
  static async getYesterdayDecision(): Promise<StrategyDecision | null> {
    // Get yesterday's date
    const yesterday = new Date();
    yesterday.setDate(yesterday.getDate() - 1);
    const yesterdayStr = yesterday.toISOString().split('T')[0];

    const signal = await this.getSignalByDate(yesterdayStr);
    if (!signal) {
      return null;
    }

    // Get today's trades (which execute yesterday's signal)
    const today = new Date().toISOString().split('T')[0];
    const trades = await TradesService.getTradesByDate(today);

    return {
      signal,
      trades,
      is_executed: trades.length > 0,
    };
  }

  /**
   * Get signal history
   */
  static async getSignalHistory(days: number = 30): Promise<DailySignal[]> {
    const result = await query<DailySignal>(
      `SELECT * FROM daily_signals
       WHERE trade_date >= CURRENT_DATE - $1
       ORDER BY trade_date DESC`,
      [days]
    );

    return result.rows;
  }

  /**
   * Get signal with associated trades
   */
  static async getSignalWithTrades(signalId: number): Promise<StrategyDecision | null> {
    const signalResult = await query<DailySignal>(
      `SELECT * FROM daily_signals WHERE id = $1`,
      [signalId]
    );

    if (signalResult.rows.length === 0) {
      return null;
    }

    const tradesResult = await query(
      `SELECT * FROM trades WHERE signal_id = $1 ORDER BY executed_at`,
      [signalId]
    );

    return {
      signal: signalResult.rows[0],
      trades: tradesResult.rows,
      is_executed: tradesResult.rows.length > 0,
    };
  }
}
