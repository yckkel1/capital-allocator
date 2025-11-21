/**
 * Trades Service Tests
 */

import { TradesService } from '@/services/trades.service';
import { query } from '@/lib/db';
import { ActionType } from '@/types/models';

jest.mock('@/lib/db');

const mockQuery = query as jest.MockedFunction<typeof query>;

describe('TradesService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('getTrades', () => {
    it('should fetch trades for default 14 days', async () => {
      const mockTrades = {
        rows: [
          {
            id: 1,
            trade_date: '2024-01-15',
            executed_at: '2024-01-15T09:30:00Z',
            symbol: 'SPY',
            action: ActionType.BUY,
            quantity: 10,
            price: 420,
            amount: 4200,
            signal_id: 1,
          },
        ],
        rowCount: 1,
      };

      mockQuery.mockResolvedValue(mockTrades as any);

      const result = await TradesService.getTrades(14);

      expect(result.trades).toHaveLength(1);
      expect(result.total_count).toBe(1);
      expect(mockQuery).toHaveBeenCalledWith(
        expect.stringContaining('WHERE trade_date >= $1'),
        expect.any(Array)
      );
    });

    it('should handle custom day range', async () => {
      mockQuery.mockResolvedValue({ rows: [], rowCount: 0 } as any);

      const result = await TradesService.getTrades(30);

      expect(result.trades).toHaveLength(0);
      expect(result.total_count).toBe(0);
    });
  });

  describe('getTradesByDate', () => {
    it('should fetch trades for specific date', async () => {
      const mockTrades = {
        rows: [
          {
            id: 1,
            trade_date: '2024-01-15',
            symbol: 'SPY',
            action: ActionType.BUY,
            quantity: 5,
            price: 420,
            amount: 2100,
          },
          {
            id: 2,
            trade_date: '2024-01-15',
            symbol: 'QQQ',
            action: ActionType.BUY,
            quantity: 3,
            price: 360,
            amount: 1080,
          },
        ],
        rowCount: 2,
      };

      mockQuery.mockResolvedValue(mockTrades as any);

      const result = await TradesService.getTradesByDate('2024-01-15');

      expect(result).toHaveLength(2);
      expect(result[0].trade_date).toBe('2024-01-15');
    });
  });

  describe('getTradesBySymbol', () => {
    it('should fetch trades for specific symbol', async () => {
      const mockTrades = {
        rows: [
          {
            id: 1,
            symbol: 'SPY',
            action: ActionType.BUY,
            quantity: 10,
          },
        ],
        rowCount: 1,
      };

      mockQuery.mockResolvedValue(mockTrades as any);

      const result = await TradesService.getTradesBySymbol('SPY', 30);

      expect(result).toHaveLength(1);
      expect(result[0].symbol).toBe('SPY');
      expect(mockQuery).toHaveBeenCalledWith(
        expect.stringContaining('WHERE symbol = $1'),
        expect.arrayContaining(['SPY'])
      );
    });
  });

  describe('getTradeStats', () => {
    it('should calculate trade statistics', async () => {
      const mockStats = {
        rows: [
          {
            total_trades: 50,
            buy_count: 30,
            sell_count: 20,
            total_volume: 125000,
          },
        ],
        rowCount: 1,
      };

      mockQuery.mockResolvedValue(mockStats as any);

      const result = await TradesService.getTradeStats(30);

      expect(result.total_trades).toBe(50);
      expect(result.buy_count).toBe(30);
      expect(result.sell_count).toBe(20);
      expect(result.total_volume).toBe(125000);
    });

    it('should return zero stats when no trades found', async () => {
      mockQuery.mockResolvedValue({ rows: [], rowCount: 0 } as any);

      const result = await TradesService.getTradeStats(30);

      expect(result.total_trades).toBe(0);
      expect(result.buy_count).toBe(0);
      expect(result.sell_count).toBe(0);
      expect(result.total_volume).toBe(0);
    });
  });
});
