/**
 * Latest Prices API Route
 * GET /api/prices/latest
 */

import { NextResponse } from 'next/server';
import { PricesService } from '@/services/prices.service';

export async function GET() {
  try {
    const data = await PricesService.getLatestPrices();

    return NextResponse.json({
      data,
      error: null,
    });
  } catch (error) {
    console.error('Error fetching latest prices:', error);
    return NextResponse.json(
      {
        data: null,
        error: error instanceof Error ? error.message : 'Failed to fetch latest prices',
      },
      { status: 500 }
    );
  }
}
