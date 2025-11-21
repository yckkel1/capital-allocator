/**
 * Portfolio API Route Tests
 */

import { GET } from '@/app/api/portfolio/route';
import { PortfolioService } from '@/services/portfolio.service';

jest.mock('@/services/portfolio.service');

describe('Portfolio API Route', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should return portfolio data', async () => {
    const mockPortfolio = {
      positions: [
        {
          id: 1,
          symbol: 'SPY',
          quantity: 10,
          avg_cost: 400,
          last_updated: '2024-01-15T10:00:00Z',
          current_price: 420,
          market_value: 4200,
          unrealized_pnl: 200,
          unrealized_pnl_pct: 5,
        },
      ],
      total_value: 4200,
      total_cost: 4000,
      total_pnl: 200,
      total_pnl_pct: 5,
      cash_balance: 1000,
      last_updated: '2024-01-15T10:00:00Z',
    };

    jest.spyOn(PortfolioService, 'getPortfolioWithMetrics').mockResolvedValue(mockPortfolio);

    const response = await GET();
    const json = await response.json();

    expect(json.error).toBeNull();
    expect(json.data).toEqual(mockPortfolio);
    expect(json.data.positions).toHaveLength(1);
  });

  it('should handle errors gracefully', async () => {
    jest
      .spyOn(PortfolioService, 'getPortfolioWithMetrics')
      .mockRejectedValue(new Error('DB Error'));

    const response = await GET();
    const json = await response.json();

    expect(json.data).toBeNull();
    expect(json.error).toBe('DB Error');
    expect(response.status).toBe(500);
  });
});
