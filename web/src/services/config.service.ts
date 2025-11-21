/**
 * Config Service
 * Handles trading configuration retrieval and comparison
 */

import { query } from '@/lib/db';
import { TradingConfig } from '@/types/models';
import { ConfigComparison, ConfigChange, HistoricalConfigsResponse } from '@/types/api';

export class ConfigService {
  /**
   * Get current active trading configuration
   */
  static async getCurrentConfig(): Promise<TradingConfig | null> {
    const result = await query<TradingConfig>(
      `SELECT * FROM trading_config
       WHERE end_date IS NULL
       ORDER BY start_date DESC
       LIMIT 1`
    );

    return result.rows[0] || null;
  }

  /**
   * Get previous trading configuration
   */
  static async getPreviousConfig(): Promise<TradingConfig | null> {
    const result = await query<TradingConfig>(
      `SELECT * FROM trading_config
       WHERE end_date IS NOT NULL
       ORDER BY end_date DESC
       LIMIT 1`
    );

    return result.rows[0] || null;
  }

  /**
   * Get config comparison (current vs previous)
   */
  static async getConfigComparison(): Promise<ConfigComparison> {
    const current = await this.getCurrentConfig();
    const previous = await this.getPreviousConfig();

    if (!current) {
      throw new Error('No active trading configuration found');
    }

    const changes: ConfigChange[] = [];

    if (previous) {
      // Compare numeric fields
      const numericFields = [
        'daily_capital',
        'lookback_days',
        'regime_bullish_threshold',
        'regime_bearish_threshold',
        'risk_high_threshold',
        'risk_medium_threshold',
        'allocation_low_risk',
        'allocation_medium_risk',
        'allocation_high_risk',
        'allocation_neutral',
        'sell_percentage',
        'rsi_oversold_threshold',
        'rsi_overbought_threshold',
        'bollinger_std_multiplier',
        'mean_reversion_allocation',
        'volatility_adjustment_factor',
        'base_volatility',
        'min_confidence_threshold',
        'confidence_scaling_factor',
        'intramonth_drawdown_limit',
        'circuit_breaker_reduction',
        'max_drawdown_tolerance',
        'min_sharpe_target',
      ];

      for (const field of numericFields) {
        const oldValue = previous[field as keyof TradingConfig];
        const newValue = current[field as keyof TradingConfig];

        if (oldValue !== newValue && typeof oldValue === 'number' && typeof newValue === 'number') {
          const changePct = oldValue !== 0 ? ((newValue - oldValue) / oldValue) * 100 : 0;
          changes.push({
            field,
            old_value: oldValue,
            new_value: newValue,
            change_pct: changePct,
          });
        }
      }

      // Compare array fields
      if (JSON.stringify(previous.assets) !== JSON.stringify(current.assets)) {
        changes.push({
          field: 'assets',
          old_value: previous.assets,
          new_value: current.assets,
        });
      }
    }

    return {
      current,
      previous,
      changes,
    };
  }

  /**
   * Get historical configurations
   */
  static async getHistoricalConfigs(limit: number = 12): Promise<HistoricalConfigsResponse> {
    const result = await query<TradingConfig>(
      `SELECT * FROM trading_config
       ORDER BY start_date DESC
       LIMIT $1`,
      [limit]
    );

    return {
      configs: result.rows,
      total_count: result.rowCount || 0,
    };
  }

  /**
   * Get config for a specific date
   */
  static async getConfigByDate(date: string): Promise<TradingConfig | null> {
    const result = await query<TradingConfig>(
      `SELECT * FROM trading_config
       WHERE start_date <= $1
         AND (end_date IS NULL OR end_date >= $1)
       LIMIT 1`,
      [date]
    );

    return result.rows[0] || null;
  }
}
