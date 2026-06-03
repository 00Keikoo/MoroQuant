'use client';

import { useMarketStore } from '@/lib/stores/marketStore';
import { TOP_FUTURES_PAIRS } from '@/lib/api/binance';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

export default function Sidebar() {
  const { pairs, selectedPair, setSelectedPair } = useMarketStore();
  const pathname = usePathname();

  return (
    <div className="w-64 bg-gray-950 border-r border-gray-800 flex flex-col">
      <div className="p-4 border-b border-gray-800">
        <h1 className="text-xl font-bold text-white">CybxAI Trading</h1>
        <p className="text-xs text-gray-500 mt-1">Market Analysis Dashboard</p>
      </div>

      <div className="flex-1 overflow-y-auto">
        <div className="p-3 border-b border-gray-800">
          <h2 className="text-xs font-semibold text-gray-400 uppercase mb-2">Navigation</h2>
          <div className="space-y-1">
            <Link
              href="/"
              className={`block w-full text-left px-3 py-2 rounded transition-colors text-sm ${
                pathname === '/'
                  ? 'bg-blue-600 text-white'
                  : 'hover:bg-gray-800 text-gray-300'
              }`}
            >
              Dashboard
            </Link>
            <Link
              href="/trading"
              className={`block w-full text-left px-3 py-2 rounded transition-colors text-sm ${
                pathname === '/trading'
                  ? 'bg-blue-600 text-white'
                  : 'hover:bg-gray-800 text-gray-300'
              }`}
            >
              ML Signals
            </Link>
          </div>
        </div>

        <div className="p-3">
          <h2 className="text-xs font-semibold text-gray-400 uppercase mb-2">Watchlist</h2>
          <div className="space-y-1">
            {TOP_FUTURES_PAIRS.map((symbol) => {
              const pair = pairs.get(symbol);
              const isSelected = selectedPair === symbol;

              return (
                <button
                  key={symbol}
                  onClick={() => setSelectedPair(symbol)}
                  className={`w-full text-left px-3 py-2 rounded transition-colors ${
                    isSelected
                      ? 'bg-blue-600 text-white'
                      : 'hover:bg-gray-800 text-gray-300'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">
                      {symbol.replace('USDT', '/USDT')}
                    </span>
                    {pair && (
                      <span className={`text-xs ${pair.change24h >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {pair.change24h >= 0 ? '+' : ''}{pair.change24h.toFixed(2)}%
                      </span>
                    )}
                  </div>
                  {pair && (
                    <div className="text-xs text-gray-400 mt-1">
                      ${pair.price.toLocaleString()}
                    </div>
                  )}
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
