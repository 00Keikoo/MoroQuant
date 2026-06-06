import { NextRequest, NextResponse } from 'next/server';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ symbol: string }> }
) {
  const { symbol } = await params;

  try {
    const response = await fetch(
      `https://fapi.binance.com/fapi/v1/ticker/price?symbol=${symbol}`,
      { signal: AbortSignal.timeout(8000) }
    );

    if (!response.ok) {
      return NextResponse.json(
        { error: 'Failed to fetch price from Binance' },
        { status: response.status }
      );
    }

    const data = await response.json();

    return NextResponse.json({
      symbol: data.symbol,
      price: parseFloat(data.price),
      live: true,
    });
  } catch (error) {
    console.error(`Error fetching price for ${symbol}:`, error);
    return NextResponse.json(
      { error: 'Failed to fetch price', live: false },
      { status: 500 }
    );
  }
}
