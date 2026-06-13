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
        <div className="flex items-center gap-3 mb-2">
          <svg width="32" height="32" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M16 4L4 10L16 16L28 10L16 4Z" fill="#3B82F6" opacity="0.8"/>
            <path d="M4 16L16 22L28 16" stroke="#60A5FA" strokeWidth="2" strokeLinecap="round"/>
            <path d="M4 22L16 28L28 22" stroke="#60A5FA" strokeWidth="2" strokeLinecap="round"/>
            <circle cx="16" cy="10" r="2" fill="#DBEAFE"/>
          </svg>
          <div>
            <h1 className="text-xl font-extrabold text-white">CybxAI</h1>
            <p className="text-xs text-blue-400 font-semibold">Trading Intelligence</p>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        <div className="p-3 border-b border-gray-800">
          <h2 className="text-xs font-semibold text-gray-400 uppercase mb-2">Navigation</h2>
          <div className="space-y-1">
            <Link
              href="/"
              className={`block w-full text-left px-3 py-2 rounded transition-all duration-200 text-sm font-semibold ${
                pathname === '/'
                  ? 'bg-blue-600 text-white border-l-4 border-blue-400 pl-2'
                  : 'hover:bg-gray-800 text-gray-300 hover:border-l-4 hover:border-gray-600 hover:pl-2'
              }`}
            >
              Dashboard
            </Link>
            <Link
              href="/trading"
              className={`block w-full text-left px-3 py-2 rounded transition-all duration-200 text-sm font-semibold ${
                pathname === '/trading'
                  ? 'bg-blue-600 text-white border-l-4 border-blue-400 pl-2'
                  : 'hover:bg-gray-800 text-gray-300 hover:border-l-4 hover:border-gray-600 hover:pl-2'
              }`}
            >
              ML Signals
            </Link>
            <Link
              href="/backtest"
              className={`block w-full text-left px-3 py-2 rounded transition-all duration-200 text-sm font-semibold ${
                pathname === '/backtest'
                  ? 'bg-blue-600 text-white border-l-4 border-blue-400 pl-2'
                  : 'hover:bg-gray-800 text-gray-300 hover:border-l-4 hover:border-gray-600 hover:pl-2'
              }`}
            >
              Backtest
            </Link>
            <Link
              href="/trades"
              className={`block w-full text-left px-3 py-2 rounded transition-all duration-200 text-sm font-semibold ${
                pathname === '/trades'
                  ? 'bg-blue-600 text-white border-l-4 border-blue-400 pl-2'
                  : 'hover:bg-gray-800 text-gray-300 hover:border-l-4 hover:border-gray-600 hover:pl-2'
              }`}
            >
              My Trades
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

      <div className="p-4 border-t border-gray-800 mt-auto">
        <div className="flex items-center justify-between">
          <span className="text-xs text-gray-500 font-medium">CybxAI Platform</span>
          <span className="text-xs font-bold text-blue-400 bg-blue-500/10 px-2 py-1 rounded border border-blue-500/30">
            v1.0 MVP
          </span>
        </div>
      </div>
    </div>
  );
}
