/**
 * Performance Service Tests
 */

import { PerformanceService } from '@/services/performance.service';
import { query } from '@/lib/db';

jest.mock('@/lib/db');

const mockQuery = query as jest.MockedFunction<typeof query>;

describe('PerformanceService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('getPnLData', () => {
    it('should fetch P&L data for 1Y time range', async () => {
      const mockData = {
        rows: [
          {
            date: '2024-01-01',
            total_value: 1000,
            daily_return: 0.01,
            cumulative_return: 0.01,
            sharpe_ratio: 1.5,
            max_drawdown: -0.05,
          },
          {
            date: '2024-01-02',
            total_value: 1010,
            daily_return: 0.01,
            cumulative_return: 0.02,
            sharpe_ratio: 1.5,
            max_drawdown: -0.05,
          },
        ],
        rowCount: 2,
      };

      mockQuery.mockResolvedValue(mockData as any);

      const result = await PerformanceService.getPnLData('1Y');

      expect(result.data).toHaveLength(2);
      expect(result.total_return).toBe(10);
      expect(result.total_return_pct).toBe(1);
      expect(mockQuery).toHaveBeenCalledWith(
        expect.any(String),
        expect.arrayContaining([expect.any(String)])
      );
    });

    it('should handle YTD time range', async () => {
      mockQuery.mockResolvedValue({ rows: [], rowCount: 0 } as any);

      const result = await PerformanceService.getPnLData('YTD');

      expect(result.data).toHaveLength(0);
      expect(mockQuery).toHaveBeenCalled();
    });

    it('should return empty data when no records found', async () => {
      mockQuery.mockResolvedValue({ rows: [], rowCount: 0 } as any);

      const result = await PerformanceService.getPnLData('1M');

      expect(result.data).toHaveLength(0);
      expect(result.total_return).toBe(0);
    });
  });

  describe('getLatestMetrics', () => {
    it('should fetch latest performance metrics', async () => {
      const mockMetrics = {
        rows: [
          {
            id: 1,
            date: '2024-01-15',
            portfolio_value: 1500,
            cash_balance: 500,
            total_value: 2000,
            daily_return: 0.015,
            cumulative_return: 0.25,
            sharpe_ratio: 1.8,
            max_drawdown: -0.08,
            created_at: '2024-01-15T10:00:00Z',
          },
        ],
        rowCount: 1,
      };

      mockQuery.mockResolvedValue(mockMetrics as any);

      const result = await PerformanceService.getLatestMetrics();

      expect(result).toBeTruthy();
      expect(result?.total_value).toBe(2000);
      expect(mockQuery).toHaveBeenCalledWith(expect.stringContaining('ORDER BY date DESC'));
    });

    it('should return null when no metrics found', async () => {
      mockQuery.mockResolvedValue({ rows: [], rowCount: 0 } as any);

      const result = await PerformanceService.getLatestMetrics();

      expect(result).toBeNull();
    });
  });

  describe('getMetricsByDate', () => {
    it('should fetch metrics for specific date', async () => {
      const mockMetrics = {
        rows: [
          {
            id: 1,
            date: '2024-01-10',
            total_value: 1950,
          },
        ],
        rowCount: 1,
      };

      mockQuery.mockResolvedValue(mockMetrics as any);

      const result = await PerformanceService.getMetricsByDate('2024-01-10');

      expect(result).toBeTruthy();
      expect(result?.date).toBe('2024-01-10');
      expect(mockQuery).toHaveBeenCalledWith(
        expect.stringContaining('WHERE date = $1'),
        ['2024-01-10']
      );
    });
  });
});
