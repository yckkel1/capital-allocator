/**
 * Latest Signal API Route
 * GET /api/signals/latest
 */

import { NextResponse } from 'next/server';
import { SignalsService } from '@/services/signals.service';

export async function GET() {
  try {
    const data = await SignalsService.getLatestSignal();

    return NextResponse.json({
      data,
      error: null,
    });
  } catch (error) {
    console.error('Error fetching latest signal:', error);
    return NextResponse.json(
      {
        data: null,
        error: error instanceof Error ? error.message : 'Failed to fetch latest signal',
      },
      { status: 500 }
    );
  }
}
