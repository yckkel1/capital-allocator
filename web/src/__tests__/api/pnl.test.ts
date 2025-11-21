/**
 * P&L API Route Tests
 */

import { GET } from '@/app/api/pnl/route';
import { PerformanceService } from '@/services/performance.service';
import { NextRequest } from 'next/server';

jest.mock('@/services/performance.service');

describe('P&L API Route', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should return P&L data for default time range', async () => {
    const mockData = {
      data: [
        { date: '2024-01-01', value: 1000, daily_return: 0, cumulative_return: 0 },
      ],
      start_date: '2023-01-01',
      end_date: '2024-01-01',
      total_return: 100,
      total_return_pct: 10,
      max_drawdown: -5,
      sharpe_ratio: 1.5,
    };

    jest.spyOn(PerformanceService, 'getPnLData').mockResolvedValue(mockData);

    const request = new NextRequest('http://localhost:3000/api/pnl?timeRange=1Y');
    const response = await GET(request);
    const json = await response.json();

    expect(json.error).toBeNull();
    expect(json.data).toEqual(mockData);
    expect(PerformanceService.getPnLData).toHaveBeenCalledWith('1Y');
  });

  it('should handle errors gracefully', async () => {
    jest.spyOn(PerformanceService, 'getPnLData').mockRejectedValue(new Error('DB Error'));

    const request = new NextRequest('http://localhost:3000/api/pnl?timeRange=1Y');
    const response = await GET(request);
    const json = await response.json();

    expect(json.data).toBeNull();
    expect(json.error).toBe('DB Error');
    expect(response.status).toBe(500);
  });
});
