/**
 * Formatting Utilities
 * Functions for formatting numbers, dates, and other display values
 */

import { format, parseISO, startOfYear } from 'date-fns';

/**
 * Format a number as currency
 */
export function formatCurrency(value: number, decimals: number = 2): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value);
}

/**
 * Format a number as percentage
 */
export function formatPercent(value: number, decimals: number = 2): string {
  return new Intl.NumberFormat('en-US', {
    style: 'percent',
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value / 100);
}

/**
 * Format a number with commas
 */
export function formatNumber(value: number, decimals: number = 0): string {
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value);
}

/**
 * Format a date string
 */
export function formatDate(dateString: string, formatStr: string = 'MMM d, yyyy'): string {
  try {
    const date = parseISO(dateString);
    return format(date, formatStr);
  } catch (error) {
    return dateString;
  }
}

/**
 * Format a datetime string
 */
export function formatDateTime(dateString: string, formatStr: string = 'MMM d, yyyy h:mm a'): string {
  try {
    const date = parseISO(dateString);
    return format(date, formatStr);
  } catch (error) {
    return dateString;
  }
}

/**
 * Get date range for YTD
 */
export function getYTDStartDate(): string {
  const start = startOfYear(new Date());
  return format(start, 'yyyy-MM-dd');
}

/**
 * Get date N days ago
 */
export function getDaysAgo(days: number): string {
  const date = new Date();
  date.setDate(date.getDate() - days);
  return format(date, 'yyyy-MM-dd');
}

/**
 * Format a quantity with appropriate decimal places
 */
export function formatQuantity(quantity: number): string {
  if (quantity === 0) return '0';
  if (Math.abs(quantity) < 0.01) return quantity.toFixed(6);
  if (Math.abs(quantity) < 1) return quantity.toFixed(4);
  return quantity.toFixed(2);
}

/**
 * Format a change value with +/- sign
 */
export function formatChange(value: number, decimals: number = 2): string {
  const sign = value >= 0 ? '+' : '';
  return `${sign}${formatNumber(value, decimals)}`;
}

/**
 * Format a percentage change with +/- sign
 */
export function formatPercentChange(value: number, decimals: number = 2): string {
  const sign = value >= 0 ? '+' : '';
  return `${sign}${formatPercent(value, decimals)}`;
}

/**
 * Get color class based on value (positive = green, negative = red)
 */
export function getValueColorClass(value: number): string {
  if (value > 0) return 'text-success-600';
  if (value < 0) return 'text-danger-600';
  return 'text-gray-600';
}

/**
 * Format confidence score
 */
export function formatConfidence(score: number): string {
  return formatPercent(score * 100, 0);
}
