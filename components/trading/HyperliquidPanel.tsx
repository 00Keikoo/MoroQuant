'use client';

import { useHyperliquidStore } from '@/lib/stores/hyperliquidStore';

const typeColors = {
  'crypto': 'bg-purple-900/50 text-purple-300',
  'stock': 'bg-blue-900/50 text-blue-300',
  'commodity': 'bg-yellow-900/50 text-yellow-300',
};

export default function HyperliquidPanel() {
  const { markets, loading } = useHyperliquidStore();

  return (
    <div className="bg-gray-900 rounded-lg p-4 border border-gray-800">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-white">Hyperliquid Markets</h3>
        {loading && <span className="text-xs text-gray-500">Loading...</span>}
      </div>

      <div className="space-y-2 max-h-96 overflow-y-auto">
        {markets.map((market) => (
          <div key={market.name} className="bg-gray-950 rounded p-3 border border-gray-800">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-white">{market.name}</span>
                <span className={`text-xs px-2 py-0.5 rounded ${typeColors[market.type]}`}>
                  {market.type}
                </span>
              </div>
              <span className="text-sm font-semibold text-white">
                ${market.price.toLocaleString()}
              </span>
            </div>

            <div className="grid grid-cols-3 gap-2 text-xs">
              <div>
                <span className="text-gray-500">Funding</span>
                <div className={`font-medium ${market.fundingRate >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {(market.fundingRate * 100).toFixed(4)}%
                </div>
              </div>
              <div>
                <span className="text-gray-500">OI</span>
                <div className="text-gray-300">
                  ${(market.openInterest / 1e6).toFixed(1)}M
                </div>
              </div>
              <div>
                <span className="text-gray-500">Vol 24h</span>
                <div className="text-gray-300">
                  ${(market.volume24h / 1e6).toFixed(1)}M
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
