import { HyperliquidMarket } from '../types';

const HYPERLIQUID_API = 'https://api.hyperliquid.xyz/info';

export async function fetchHyperliquidMarkets(): Promise<HyperliquidMarket[]> {
  try {
    const response = await fetch(HYPERLIQUID_API, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ type: 'metaAndAssetCtxs' }),
    });

    const data = await response.json();

    const markets: HyperliquidMarket[] = [];

    if (data[0]?.universe && data[1]) {
      data[0].universe.forEach((asset: any, index: number) => {
        const ctx = data[1][index];
        if (!ctx) return;

        let type: HyperliquidMarket['type'] = 'crypto';
        if (asset.name.includes('TSLA') || asset.name.includes('AAPL') || asset.name.includes('NVDA')) {
          type = 'stock';
        } else if (asset.name.includes('XAU') || asset.name.includes('WTI')) {
          type = 'commodity';
        }

        markets.push({
          name: asset.name,
          type,
          price: parseFloat(ctx.markPx || '0'),
          fundingRate: parseFloat(ctx.funding || '0'),
          openInterest: parseFloat(ctx.openInterest || '0'),
          volume24h: parseFloat(ctx.dayNtlVlm || '0'),
        });
      });
    }

    return markets;
  } catch (error) {
    console.error('Error fetching Hyperliquid markets:', error);
    return getMockHyperliquidMarkets();
  }
}

function getMockHyperliquidMarkets(): HyperliquidMarket[] {
  return [
    {
      name: 'BTC',
      type: 'crypto',
      price: 67500,
      fundingRate: 0.0001,
      openInterest: 1250000000,
      volume24h: 3500000000,
    },
    {
      name: 'ETH',
      type: 'crypto',
      price: 3200,
      fundingRate: 0.00008,
      openInterest: 850000000,
      volume24h: 1800000000,
    },
    {
      name: 'TSLA',
      type: 'stock',
      price: 245.50,
      fundingRate: 0.00005,
      openInterest: 45000000,
      volume24h: 120000000,
    },
    {
      name: 'AAPL',
      type: 'stock',
      price: 185.25,
      fundingRate: 0.00004,
      openInterest: 38000000,
      volume24h: 95000000,
    },
    {
      name: 'NVDA',
      type: 'stock',
      price: 892.75,
      fundingRate: 0.00012,
      openInterest: 125000000,
      volume24h: 380000000,
    },
    {
      name: 'XAU',
      type: 'commodity',
      price: 2340.50,
      fundingRate: 0.00003,
      openInterest: 28000000,
      volume24h: 75000000,
    },
    {
      name: 'WTI',
      type: 'commodity',
      price: 78.25,
      fundingRate: 0.00006,
      openInterest: 15000000,
      volume24h: 42000000,
    },
  ];
}
