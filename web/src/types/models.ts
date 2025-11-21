/**
 * Database Models
 * TypeScript interfaces matching the PostgreSQL database schema
 */

export enum ActionType {
  BUY = 'BUY',
  SELL = 'SELL',
  HOLD = 'HOLD',
}

export interface PriceHistory {
  id: number;
  date: string;
  symbol: string;
  open_price: number;
  high_price: number;
  low_price: number;
  close_price: number;
  volume: number;
  created_at: string;
}

export interface AssetAllocation {
  allocation: number;
  score: number;
}

export interface SignalAllocations {
  action: ActionType;
  regime: string;
  regime_score: number;
  risk_level: string;
  risk_score: number;
  assets: Record<string, AssetAllocation>;
  circuit_breaker_active: boolean;
}

export interface DailySignal {
  id: number;
  trade_date: string;
  generated_at: string;
  allocations: SignalAllocations;
  model_type: string;
  confidence_score: number;
  features_used: Record<string, any>;
}

export interface Trade {
  id: number;
  trade_date: string;
  executed_at: string;
  symbol: string;
  action: ActionType;
  quantity: number;
  price: number;
  amount: number;
  signal_id: number;
}

export interface Portfolio {
  id: number;
  symbol: string;
  quantity: number;
  avg_cost: number;
  last_updated: string;
}

export interface PerformanceMetrics {
  id: number;
  date: string;
  portfolio_value: number;
  cash_balance: number;
  total_value: number;
  daily_return: number | null;
  cumulative_return: number | null;
  sharpe_ratio: number | null;
  max_drawdown: number | null;
  created_at: string;
}

export interface TradingConfig {
  id: number;
  start_date: string;
  end_date: string | null;
  daily_capital: number;
  assets: string[];
  lookback_days: number;
  regime_bullish_threshold: number;
  regime_bearish_threshold: number;
  risk_high_threshold: number;
  risk_medium_threshold: number;
  allocation_low_risk: number;
  allocation_medium_risk: number;
  allocation_high_risk: number;
  allocation_neutral: number;
  sell_percentage: number;
  momentum_weight: number;
  price_momentum_weight: number;
  max_drawdown_tolerance: number;
  min_sharpe_target: number;
  rsi_oversold_threshold: number;
  rsi_overbought_threshold: number;
  bollinger_std_multiplier: number;
  mean_reversion_allocation: number;
  volatility_adjustment_factor: number;
  base_volatility: number;
  min_confidence_threshold: number;
  confidence_scaling_factor: number;
  intramonth_drawdown_limit: number;
  circuit_breaker_reduction: number;
  created_at: string;
  created_by: string | null;
  notes: string | null;
}
