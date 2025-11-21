/**
 * Application Constants
 */

export const TIME_RANGES = [
  { label: '1M', value: '1M', days: 30 },
  { label: '3M', value: '3M', days: 90 },
  { label: '6M', value: '6M', days: 180 },
  { label: '1Y', value: '1Y', days: 365 },
  { label: '2Y', value: '2Y', days: 730 },
  { label: '5Y', value: '5Y', days: 1825 },
  { label: 'YTD', value: 'YTD', days: undefined },
  { label: 'ALL', value: 'ALL', days: undefined },
] as const;

export const ASSETS = ['SPY', 'QQQ', 'DIA'] as const;

export const ASSET_NAMES: Record<string, string> = {
  SPY: 'S&P 500',
  QQQ: 'Nasdaq-100',
  DIA: 'Dow Jones',
};

export const REGIME_COLORS: Record<string, string> = {
  bullish: 'text-success-600',
  neutral: 'text-yellow-600',
  bearish: 'text-danger-600',
};

export const RISK_COLORS: Record<string, string> = {
  low: 'text-success-600',
  medium: 'text-yellow-600',
  high: 'text-danger-600',
};

export const ACTION_COLORS: Record<string, string> = {
  BUY: 'text-success-600 bg-success-50',
  SELL: 'text-danger-600 bg-danger-50',
  HOLD: 'text-gray-600 bg-gray-50',
};
