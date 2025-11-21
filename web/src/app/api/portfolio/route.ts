/**
 * Portfolio API Route
 * GET /api/portfolio
 */

import { NextResponse } from 'next/server';
import { PortfolioService } from '@/services/portfolio.service';

export async function GET() {
  try {
    const data = await PortfolioService.getPortfolioWithMetrics();

    return NextResponse.json({
      data,
      error: null,
    });
  } catch (error) {
    console.error('Error fetching portfolio:', error);
    return NextResponse.json(
      {
        data: null,
        error: error instanceof Error ? error.message : 'Failed to fetch portfolio',
      },
      { status: 500 }
    );
  }
}
