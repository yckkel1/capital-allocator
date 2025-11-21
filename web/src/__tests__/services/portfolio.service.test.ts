/**
 * Portfolio Service Tests
 */

import { PortfolioService } from '@/services/portfolio.service';
import { query } from '@/lib/db';

jest.mock('@/lib/db');

const mockQuery = query as jest.MockedFunction<typeof query>;

describe('PortfolioService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('getPortfolioWithMetrics', () => {
    it('should fetch portfolio with calculated metrics', async () => {
      const mockPortfolio = {
        rows: [
          {
            id: 1,
            symbol: 'SPY',
            quantity: 10,
            avg_cost: 400,
            last_updated: '2024-01-15T10:00:00Z',
          },
        ],
        rowCount: 1,
      };

      const mockPrices = {
        rows: [
          {
            symbol: 'SPY',
            close_price: 420,
            date: '2024-01-15',
          },
        ],
        rowCount: 1,
      };

      const mockSignal = {
        rows: [],
        rowCount: 0,
      };

      const mockCash = {
        rows: [{ cash_balance: 1000 }],
        rowCount: 1,
      };

      mockQuery
        .mockResolvedValueOnce(mockPortfolio as any)
        .mockResolvedValueOnce(mockPrices as any)
        .mockResolvedValueOnce(mockSignal as any)
        .mockResolvedValueOnce(mockCash as any);

      const result = await PortfolioService.getPortfolioWithMetrics();

      expect(result.positions).toHaveLength(1);
      expect(result.positions[0].market_value).toBe(4200); // 10 * 420
      expect(result.positions[0].unrealized_pnl).toBe(200); // 4200 - 4000
      expect(result.cash_balance).toBe(1000);
    });

    it('should handle empty portfolio', async () => {
      mockQuery
        .mockResolvedValueOnce({ rows: [], rowCount: 0 } as any)
        .mockResolvedValueOnce({ rows: [], rowCount: 0 } as any)
        .mockResolvedValueOnce({ rows: [], rowCount: 0 } as any)
        .mockResolvedValueOnce({ rows: [{ cash_balance: 5000 }], rowCount: 1 } as any);

      const result = await PortfolioService.getPortfolioWithMetrics();

      expect(result.positions).toHaveLength(0);
      expect(result.total_value).toBe(0);
      expect(result.cash_balance).toBe(5000);
    });

    it('should calculate pending quantity changes from signal', async () => {
      const mockPortfolio = {
        rows: [
          {
            id: 1,
            symbol: 'QQQ',
            quantity: 5,
            avg_cost: 350,
            last_updated: '2024-01-15T10:00:00Z',
          },
        ],
        rowCount: 1,
      };

      const mockPrices = {
        rows: [
          {
            symbol: 'QQQ',
            close_price: 360,
            date: '2024-01-15',
          },
        ],
        rowCount: 1,
      };

      const mockSignal = {
        rows: [
          {
            allocations: {
              assets: {
                QQQ: { allocation: 2160 }, // Target: 6 shares at 360
              },
            },
          },
        ],
        rowCount: 1,
      };

      const mockCash = {
        rows: [{ cash_balance: 2000 }],
        rowCount: 1,
      };

      mockQuery
        .mockResolvedValueOnce(mockPortfolio as any)
        .mockResolvedValueOnce(mockPrices as any)
        .mockResolvedValueOnce(mockSignal as any)
        .mockResolvedValueOnce(mockCash as any);

      const result = await PortfolioService.getPortfolioWithMetrics();

      expect(result.positions[0].pending_quantity_change).toBe(1); // 6 - 5
    });
  });

  describe('getPortfolioByDate', () => {
    it('should fetch portfolio for specific date', async () => {
      const mockPortfolio = {
        rows: [
          { id: 1, symbol: 'SPY', quantity: 8, avg_cost: 380 },
          { id: 2, symbol: 'QQQ', quantity: 4, avg_cost: 340 },
        ],
        rowCount: 2,
      };

      mockQuery.mockResolvedValue(mockPortfolio as any);

      const result = await PortfolioService.getPortfolioByDate('2024-01-10');

      expect(result).toHaveLength(2);
      expect(result[0].symbol).toBe('SPY');
    });
  });
});
