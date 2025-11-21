/**
 * P&L API Route
 * GET /api/pnl?timeRange=1Y
 */

import { NextRequest, NextResponse } from 'next/server';
import { PerformanceService } from '@/services/performance.service';

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;
    const timeRange = searchParams.get('timeRange') || '1Y';

    const data = await PerformanceService.getPnLData(timeRange);

    return NextResponse.json({
      data,
      error: null,
    });
  } catch (error) {
    console.error('Error fetching P&L data:', error);
    return NextResponse.json(
      {
        data: null,
        error: error instanceof Error ? error.message : 'Failed to fetch P&L data',
      },
      { status: 500 }
    );
  }
}
