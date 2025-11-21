/**
 * Trades API Route Tests
 */

import { GET } from '@/app/api/trades/route';
import { TradesService } from '@/services/trades.service';
import { NextRequest } from 'next/server';
import { ActionType } from '@/types/models';

jest.mock('@/services/trades.service');

describe('Trades API Route', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should return trades for specified days', async () => {
    const mockTrades = {
      trades: [
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
      total_count: 1,
      start_date: '2024-01-01',
      end_date: '2024-01-15',
    };

    jest.spyOn(TradesService, 'getTrades').mockResolvedValue(mockTrades);

    const request = new NextRequest('http://localhost:3000/api/trades?days=14');
    const response = await GET(request);
    const json = await response.json();

    expect(json.error).toBeNull();
    expect(json.data).toEqual(mockTrades);
    expect(TradesService.getTrades).toHaveBeenCalledWith(14);
  });

  it('should use default days when not specified', async () => {
    const mockTrades = {
      trades: [],
      total_count: 0,
      start_date: '2024-01-01',
      end_date: '2024-01-15',
    };

    jest.spyOn(TradesService, 'getTrades').mockResolvedValue(mockTrades);

    const request = new NextRequest('http://localhost:3000/api/trades');
    const response = await GET(request);
    const json = await response.json();

    expect(json.error).toBeNull();
    expect(TradesService.getTrades).toHaveBeenCalledWith(14);
  });

  it('should handle errors gracefully', async () => {
    jest.spyOn(TradesService, 'getTrades').mockRejectedValue(new Error('DB Error'));

    const request = new NextRequest('http://localhost:3000/api/trades?days=30');
    const response = await GET(request);
    const json = await response.json();

    expect(json.data).toBeNull();
    expect(json.error).toBe('DB Error');
    expect(response.status).toBe(500);
  });
});
