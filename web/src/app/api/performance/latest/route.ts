/**
 * Latest Performance Metrics API Route
 * GET /api/performance/latest
 */

import { NextResponse } from 'next/server';
import { PerformanceService } from '@/services/performance.service';

export async function GET() {
  try {
    const data = await PerformanceService.getLatestMetrics();

    return NextResponse.json({
      data,
      error: null,
    });
  } catch (error) {
    console.error('Error fetching latest performance:', error);
    return NextResponse.json(
      {
        data: null,
        error: error instanceof Error ? error.message : 'Failed to fetch latest performance',
      },
      { status: 500 }
    );
  }
}
