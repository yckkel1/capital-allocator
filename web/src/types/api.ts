/**
 * API Response Types
 * Types for API responses and DTOs
 */

import {
  Trade,
  Portfolio,
  PerformanceMetrics,
  TradingConfig,
  DailySignal,
  PriceHistory
} from './models';

export interface TimeRange {
  label: string;
  value: string;
  days?: number;
}

export interface PortfolioWithMetrics extends Portfolio {
  current_price: number;
  market_value: number;
  unrealized_pnl: number;
  unrealized_pnl_pct: number;
  pending_quantity_change?: number;
}

export interface PortfolioSummary {
  positions: PortfolioWithMetrics[];
  total_value: number;
  total_cost: number;
  total_pnl: number;
  total_pnl_pct: number;
  cash_balance: number;
  last_updated: string;
}

export interface PnLDataPoint {
  date: string;
  value: number;
  daily_return: number;
  cumulative_return: number;
}

export interface PnLChartData {
  data: PnLDataPoint[];
  start_date: string;
  end_date: string;
  total_return: number;
  total_return_pct: number;
  max_drawdown: number;
  sharpe_ratio: number | null;
}

export interface TradesResponse {
  trades: Trade[];
  total_count: number;
  start_date: string;
  end_date: string;
}

export interface ConfigComparison {
  current: TradingConfig;
  previous: TradingConfig | null;
  changes: ConfigChange[];
}

export interface ConfigChange {
  field: string;
  old_value: any;
  new_value: any;
  change_pct?: number;
}

export interface StrategyDecision {
  signal: DailySignal;
  trades: Trade[];
  is_executed: boolean;
}

export interface DashboardData {
  pnl: PnLChartData;
  portfolio: PortfolioSummary;
  recent_trades: Trade[];
  latest_signal: DailySignal;
  performance: PerformanceMetrics;
}

export interface HistoricalConfigsResponse {
  configs: TradingConfig[];
  total_count: number;
}

export interface PriceHistoryResponse {
  prices: PriceHistory[];
  symbol: string;
  start_date: string;
  end_date: string;
}

export type ApiResponse<T> = {
  data: T;
  error: null;
} | {
  data: null;
  error: string;
};
