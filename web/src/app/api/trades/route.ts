/**
 * Trades API Route
 * GET /api/trades?days=14
 */

import { NextRequest, NextResponse } from 'next/server';
import { TradesService } from '@/services/trades.service';

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;
    const days = parseInt(searchParams.get('days') || '14', 10);

    const data = await TradesService.getTrades(days);

    return NextResponse.json({
      data,
      error: null,
    });
  } catch (error) {
    console.error('Error fetching trades:', error);
    return NextResponse.json(
      {
        data: null,
        error: error instanceof Error ? error.message : 'Failed to fetch trades',
      },
      { status: 500 }
    );
  }
}
