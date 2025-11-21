/**
 * Yesterday's Signal API Route (D-1 Strategy)
 * GET /api/signals/yesterday
 */

import { NextResponse } from 'next/server';
import { SignalsService } from '@/services/signals.service';

export async function GET() {
  try {
    const data = await SignalsService.getYesterdayDecision();

    return NextResponse.json({
      data,
      error: null,
    });
  } catch (error) {
    console.error('Error fetching yesterday signal:', error);
    return NextResponse.json(
      {
        data: null,
        error: error instanceof Error ? error.message : 'Failed to fetch yesterday signal',
      },
      { status: 500 }
    );
  }
}
