'use client';

import { useMarketStore } from '@/lib/stores/marketStore';

export default function MarketStats() {
  const { selectedPair, pairs } = useMarketStore();
  const pair = pairs.get(selectedPair);

  if (!pair) {
    return (
      <div className="bg-gray-900 rounded-lg p-4 border border-gray-800">
        <p className="text-gray-500 text-sm">Loading market data...</p>
      </div>
    );
  }

  return (
    <div className="bg-gray-900 rounded-lg p-4 border border-gray-800">
      <div className="grid grid-cols-5 gap-4">
        <div>
          <span className="text-xs text-gray-500">24h Change</span>
          <div className={`text-lg font-semibold ${pair.change24h >= 0 ? 'text-green-400' : 'text-red-400'}`}>
            {pair.change24h >= 0 ? '+' : ''}{pair.change24h.toFixed(2)}%
          </div>
        </div>

        <div>
          <span className="text-xs text-gray-500">24h High</span>
          <div className="text-lg font-semibold text-white">
            ${pair.high24h.toLocaleString()}
          </div>
        </div>

        <div>
          <span className="text-xs text-gray-500">24h Low</span>
          <div className="text-lg font-semibold text-white">
            ${pair.low24h.toLocaleString()}
          </div>
        </div>

        <div>
          <span className="text-xs text-gray-500">24h Volume</span>
          <div className="text-lg font-semibold text-white">
            ${(pair.volume24h / 1e9).toFixed(2)}B
          </div>
        </div>

        {pair.fundingRate !== undefined && (
          <div>
            <span className="text-xs text-gray-500">Funding Rate</span>
            <div className={`text-lg font-semibold ${pair.fundingRate >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              {(pair.fundingRate * 100).toFixed(4)}%
            </div>
          </div>
        )}
      </div>

      {pair.openInterest !== undefined && pair.longShortRatio !== undefined && (
        <div className="grid grid-cols-2 gap-4 mt-4 pt-4 border-t border-gray-800">
          <div>
            <span className="text-xs text-gray-500">Open Interest</span>
            <div className="text-lg font-semibold text-white">
              ${(pair.openInterest / 1e9).toFixed(2)}B
            </div>
          </div>

          <div>
            <span className="text-xs text-gray-500">Long/Short Ratio</span>
            <div className={`text-lg font-semibold ${pair.longShortRatio > 1 ? 'text-green-400' : 'text-red-400'}`}>
              {pair.longShortRatio.toFixed(2)}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
