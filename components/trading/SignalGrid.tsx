'use client';

import { useState, useEffect, useRef } from 'react';
import { MLSignal } from '@/lib/types/ml';
import { getSignal, getSymbols, getDisplayName } from '@/lib/api/ml-trading';
import SignalCard from './SignalCard';

interface SignalGridProps {
  timeframe: '1h' | '4h';
}

const ACTIVE_PAIRS = [
  'BTCUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT', 'ZECUSDT',
  'SUIUSDT', 'ADAUSDT', 'ETHUSDT', 'HYPEUSDT', 'LINKUSDT', 'LTCUSDT'
];

export default function SignalGrid({ timeframe }: SignalGridProps) {
  const [signals, setSignals] = useState<MLSignal[]>([]);
  const [availableSymbols, setAvailableSymbols] = useState<string[]>([]);
  const [selectedSymbol, setSelectedSymbol] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const isFirstLoad = useRef(true);
  const previousSignals = useRef<MLSignal[]>([]);

  useEffect(() => {
    console.log('[SignalGrid] Component mounted');
    loadSymbols();
  }, []);

  useEffect(() => {
    console.log('[SignalGrid] availableSymbols changed:', availableSymbols.length, 'symbols');
    console.log('[SignalGrid] selectedSymbol:', selectedSymbol);
    console.log('[SignalGrid] timeframe:', timeframe);

    if (availableSymbols.length > 0) {
      console.log('[SignalGrid] Starting refreshSignals...');
      refreshSignals();
      const interval = setInterval(refreshSignals, 60000);
      return () => clearInterval(interval);
    } else {
      console.log('[SignalGrid] Skipping refreshSignals - no available symbols');
    }
  }, [availableSymbols, selectedSymbol, timeframe]);

  const loadSymbols = async () => {
    try {
      console.log('[SignalGrid] Loading symbols...');
      const data = await getSymbols();
      console.log('[SignalGrid] Symbols response:', data);
      const allSymbols = Object.keys(data.symbols);
      console.log('[SignalGrid] Total symbols before filter:', allSymbols.length);

      const filteredSymbols = allSymbols.filter(symbol => ACTIVE_PAIRS.includes(symbol));
      console.log('[SignalGrid] Filtered to active pairs:', filteredSymbols.length);

      setAvailableSymbols(filteredSymbols);
    } catch (error) {
      console.error('[SignalGrid] Error loading symbols:', error);
    }
  };

  const refreshSignals = async () => {
    console.log('[SignalGrid] refreshSignals called');
    if (isFirstLoad.current) {
      setLoading(true);
    }

    try {
      let symbolsToFetch = selectedSymbol ? [selectedSymbol] : availableSymbols;
      console.log('[SignalGrid] Symbols to fetch:', symbolsToFetch);

      const results: MLSignal[] = [];
      const BATCH_SIZE = 3;

      for (let i = 0; i < symbolsToFetch.length; i += BATCH_SIZE) {
        const batch = symbolsToFetch.slice(i, i + BATCH_SIZE);
        console.log(`[SignalGrid] Fetching batch ${i / BATCH_SIZE + 1}:`, batch);
        const batchPromises = batch.map(symbol =>
          getSignal(symbol, timeframe).catch(error => ({
            symbol,
            timeframe,
            direction: 'neutral' as const,
            confidence: 0,
            price: 0,
            top_features: {},
            regime: '',
            generated_at: new Date().toISOString(),
            model_type: '',
            error: 'error',
            message: error.message || 'Failed to generate signal'
          }))
        );

        const batchResults = await Promise.all(batchPromises);
        results.push(...batchResults);

        // Show cards incrementally as they load
        if (isFirstLoad.current) {
          setSignals([...results]);
        } else if (previousSignals.current.length > 0) {
          // Stale-while-revalidate: merge new signals with previous ones
          const signalMap = new Map(previousSignals.current.map(s => [s.symbol, s]));
          results.forEach(s => signalMap.set(s.symbol, s));
          setSignals(Array.from(signalMap.values()));
        } else {
          setSignals([...results]);
        }
      }

      // Store as previous signals for next refresh
      previousSignals.current = results;
      setLastUpdate(new Date());

      if (isFirstLoad.current) {
        isFirstLoad.current = false;
        setLoading(false);
      }
    } catch (error) {
      console.error('Error refreshing signals:', error);
      if (isFirstLoad.current) {
        isFirstLoad.current = false;
        setLoading(false);
      }
    }
  };

  const cryptoSymbols = availableSymbols.filter(s => !s.endsWith('_proxy'));
  const proxySymbols = availableSymbols.filter(s => s.endsWith('_proxy'));

  const cryptoSignals = signals.filter(s => !s.symbol.endsWith('_proxy'));
  const proxySignals = signals.filter(s => s.symbol.endsWith('_proxy'));

  const signalStats = cryptoSignals.reduce(
    (acc, signal) => {
      if (!signal.error) {
        acc.total++;
        if (signal.direction === 'long') acc.long++;
        else if (signal.direction === 'short') acc.short++;
        else acc.neutral++;
      }
      return acc;
    },
    { total: 0, long: 0, short: 0, neutral: 0 }
  );

  const getPercentage = (count: number) =>
    signalStats.total > 0 ? Math.round((count / signalStats.total) * 100) : 0;

  if (loading && signals.length === 0) {
    return (
      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div className="h-10 bg-gray-800 rounded w-full sm:w-48 animate-pulse"></div>
          <div className="h-10 bg-gray-800 rounded w-full sm:w-32 animate-pulse"></div>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3 sm:gap-4">
          {[1, 2, 3, 4, 5, 6].map(i => (
            <div key={i} className="bg-gray-900 rounded-lg p-4 border border-gray-800">
              <div className="animate-pulse space-y-3">
                <div className="h-4 bg-gray-800 rounded w-3/4"></div>
                <div className="h-8 bg-gray-800 rounded w-1/2"></div>
                <div className="h-4 bg-gray-800 rounded w-full"></div>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-3 sm:space-y-4">
      {signalStats.total > 0 && (
        <div className="bg-gray-900/50 backdrop-blur border border-gray-800 rounded-lg p-3 sm:p-4">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4">
            <div className="text-center">
              <div className="text-xl sm:text-2xl font-bold text-white">{signalStats.total}</div>
              <div className="text-xs text-gray-500 uppercase tracking-wider mt-1">Total</div>
            </div>
            <div className="text-center">
              <div className="text-xl sm:text-2xl font-bold text-green-400">{getPercentage(signalStats.long)}%</div>
              <div className="text-xs text-gray-500 uppercase tracking-wider mt-1">Long ({signalStats.long})</div>
            </div>
            <div className="text-center">
              <div className="text-xl sm:text-2xl font-bold text-red-400">{getPercentage(signalStats.short)}%</div>
              <div className="text-xs text-gray-500 uppercase tracking-wider mt-1">Short ({signalStats.short})</div>
            </div>
            <div className="text-center">
              <div className="text-xl sm:text-2xl font-bold text-gray-400">{getPercentage(signalStats.neutral)}%</div>
              <div className="text-xs text-gray-500 uppercase tracking-wider mt-1">Neutral ({signalStats.neutral})</div>
            </div>
          </div>
        </div>
      )}

      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <select
          value={selectedSymbol}
          onChange={(e) => setSelectedSymbol(e.target.value)}
          className="w-full sm:w-auto bg-gray-900 border border-gray-800 text-white rounded px-4 py-2 text-sm focus:outline-none focus:border-gray-700"
        >
          <option value="">All Symbols</option>
          <optgroup label="Crypto Pairs">
            {cryptoSymbols.map(symbol => (
              <option key={symbol} value={symbol}>{getDisplayName(symbol)}</option>
            ))}
          </optgroup>
          {proxySymbols.length > 0 && (
            <optgroup label="Macro Context">
              {proxySymbols.map(symbol => (
                <option key={symbol} value={symbol}>{getDisplayName(symbol)}</option>
              ))}
            </optgroup>
          )}
        </select>

        <div className="flex items-center justify-between sm:justify-end gap-3">
          {lastUpdate && (
            <span className="text-xs text-gray-500 truncate">
              {lastUpdate.toLocaleTimeString()}
            </span>
          )}
          <button
            onClick={refreshSignals}
            disabled={loading}
            className="bg-gray-900 border border-gray-800 text-white rounded px-4 py-2 text-sm hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex-shrink-0"
          >
            {loading ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3 sm:gap-4">
        {cryptoSignals.map(signal => (
          <SignalCard key={signal.symbol} signal={signal} />
        ))}
      </div>

      {proxySignals.length > 0 && (
        <div className="space-y-3 mt-6">
          <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">Macro Context</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3 sm:gap-4">
            {proxySignals.map(signal => (
              <SignalCard key={signal.symbol} signal={signal} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
