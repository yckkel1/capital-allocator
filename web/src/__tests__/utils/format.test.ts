/**
 * Format Utils Tests
 */

import {
  formatCurrency,
  formatPercent,
  formatNumber,
  formatDate,
  formatQuantity,
  formatChange,
  formatPercentChange,
  getValueColorClass,
  formatConfidence,
} from '@/utils/format';

describe('Format Utils', () => {
  describe('formatCurrency', () => {
    it('should format positive values', () => {
      expect(formatCurrency(1234.56)).toBe('$1,234.56');
    });

    it('should format negative values', () => {
      expect(formatCurrency(-1234.56)).toBe('-$1,234.56');
    });

    it('should handle zero', () => {
      expect(formatCurrency(0)).toBe('$0.00');
    });

    it('should respect decimal places', () => {
      expect(formatCurrency(1234.567, 3)).toBe('$1,234.567');
    });
  });

  describe('formatPercent', () => {
    it('should format percentage values', () => {
      expect(formatPercent(12.34)).toBe('12.34%');
    });

    it('should handle negative percentages', () => {
      expect(formatPercent(-5.67)).toBe('-5.67%');
    });

    it('should respect decimal places', () => {
      expect(formatPercent(12.345, 1)).toBe('12.3%');
    });
  });

  describe('formatNumber', () => {
    it('should format numbers with commas', () => {
      expect(formatNumber(1234567)).toBe('1,234,567');
    });

    it('should handle decimals', () => {
      expect(formatNumber(1234.567, 2)).toBe('1,234.57');
    });
  });

  describe('formatDate', () => {
    it('should format ISO date string', () => {
      const result = formatDate('2024-01-15');
      expect(result).toContain('Jan');
      expect(result).toContain('15');
      expect(result).toContain('2024');
    });

    it('should handle custom format', () => {
      const result = formatDate('2024-01-15', 'yyyy-MM-dd');
      expect(result).toBe('2024-01-15');
    });
  });

  describe('formatQuantity', () => {
    it('should format small quantities with high precision', () => {
      expect(formatQuantity(0.001234)).toBe('0.001234');
    });

    it('should format fractional shares', () => {
      expect(formatQuantity(0.5)).toBe('0.5000');
    });

    it('should format whole shares', () => {
      expect(formatQuantity(10.5)).toBe('10.50');
    });

    it('should handle zero', () => {
      expect(formatQuantity(0)).toBe('0');
    });
  });

  describe('formatChange', () => {
    it('should add plus sign for positive values', () => {
      expect(formatChange(123.45)).toBe('+123.45');
    });

    it('should keep minus sign for negative values', () => {
      expect(formatChange(-123.45)).toBe('-123.45');
    });

    it('should handle zero', () => {
      expect(formatChange(0)).toBe('+0');
    });
  });

  describe('formatPercentChange', () => {
    it('should format positive percent change', () => {
      expect(formatPercentChange(5.67)).toBe('+5.67%');
    });

    it('should format negative percent change', () => {
      expect(formatPercentChange(-5.67)).toBe('-5.67%');
    });
  });

  describe('getValueColorClass', () => {
    it('should return success class for positive values', () => {
      expect(getValueColorClass(100)).toBe('text-success-600');
    });

    it('should return danger class for negative values', () => {
      expect(getValueColorClass(-100)).toBe('text-danger-600');
    });

    it('should return gray class for zero', () => {
      expect(getValueColorClass(0)).toBe('text-gray-600');
    });
  });

  describe('formatConfidence', () => {
    it('should format confidence score as percentage', () => {
      expect(formatConfidence(0.75)).toBe('75%');
    });

    it('should handle edge cases', () => {
      expect(formatConfidence(0)).toBe('0%');
      expect(formatConfidence(1)).toBe('100%');
    });
  });
});
