/**
 * Trading Config API Route
 * GET /api/config - Get current and previous config with comparison
 * GET /api/config?history=true&limit=12 - Get historical configs
 */

import { NextRequest, NextResponse } from 'next/server';
import { ConfigService } from '@/services/config.service';

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;
    const history = searchParams.get('history') === 'true';
    const limit = parseInt(searchParams.get('limit') || '12', 10);

    if (history) {
      const data = await ConfigService.getHistoricalConfigs(limit);
      return NextResponse.json({
        data,
        error: null,
      });
    }

    const data = await ConfigService.getConfigComparison();

    return NextResponse.json({
      data,
      error: null,
    });
  } catch (error) {
    console.error('Error fetching config:', error);
    return NextResponse.json(
      {
        data: null,
        error: error instanceof Error ? error.message : 'Failed to fetch config',
      },
      { status: 500 }
    );
  }
}
