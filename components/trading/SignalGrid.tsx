'use client';

import { useState, useEffect, useRef, useMemo } from 'react';
import { MLSignal } from '@/lib/types/ml';
import { getSignal, getSymbols, getDisplayName } from '@/lib/api/ml-trading';
import SignalCard from './SignalCard';
import SignalFilterBar, {
  DirectionFilter,
  SortField,
  SortOrder,
} from './SignalFilterBar';

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

  // Filter state
  const [directionFilter, setDirectionFilter] = useState<DirectionFilter>('all');
  const [minConfidence, setMinConfidence] = useState(0);
  const [searchQuery, setSearchQuery] = useState('');
  const [sortField, setSortField] = useState<SortField>('symbol');
  const [sortOrder, setSortOrder] = useState<SortOrder>('asc');

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

  // Handle sort change — toggle direction if same field, otherwise default desc
  const handleSortChange = (field: SortField) => {
    if (field === sortField) {
      setSortOrder(prev => (prev === 'desc' ? 'asc' : 'desc'));
    } else {
      setSortField(field);
      setSortOrder('desc');
    }
  };

  // Filtered + sorted signals
  const filteredSignals = useMemo(() => {
    const query = searchQuery.toLowerCase();
    const filtered = signals.filter(s => {
      // Filter out inactive signals (API returns error=signal_inactive)
      if (s.error === 'signal_inactive') return false;
      if (s.signal_status && s.signal_status !== 'ACTIVE') return false;
      if (s.error) return true; // show other error cards (no_signal, etc.)
      if (directionFilter !== 'all' && s.direction !== directionFilter) return false;
      if (s.confidence < minConfidence) return false;
      if (query && !s.symbol.toLowerCase().includes(query)) return false;
      return true;
    });

    filtered.sort((a, b) => {
      if (sortField === 'confidence') {
        return sortOrder === 'desc' ? b.confidence - a.confidence : a.confidence - b.confidence;
      }
      // symbol sort — always asc for symbol
      return a.symbol.localeCompare(b.symbol);
    });

    return filtered;
  }, [signals, directionFilter, minConfidence, searchQuery, sortField, sortOrder]);

  const cryptoSymbols = availableSymbols.filter(s => !s.endsWith('_proxy'));
  const proxySymbols = availableSymbols.filter(s => s.endsWith('_proxy'));

  const filteredCrypto = filteredSignals.filter(s => !s.symbol.endsWith('_proxy'));
  const filteredProxy = filteredSignals.filter(s => s.symbol.endsWith('_proxy'));

  const signalStats = signals.reduce(
    (acc, signal) => {
      if (!signal.error && (!signal.signal_status || signal.signal_status === 'ACTIVE')) {
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
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-3 sm:gap-4">
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
      {/* Stats row */}
      {signalStats.total > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4">
          <div className="bg-gradient-to-br from-blue-900/40 to-blue-950/20 backdrop-blur border border-blue-700/30 rounded-xl p-4 sm:p-5 hover:scale-105 transition-transform duration-300">
            <div className="flex items-center justify-between mb-2">
              <div className="text-xs font-bold text-blue-400 uppercase tracking-wider">Total</div>
              <div className="text-2xl">📊</div>
            </div>
            <div className="text-3xl sm:text-4xl font-extrabold text-white">{signalStats.total}</div>
            <div className="text-xs text-gray-400 mt-1 font-medium">Active Signals</div>
          </div>

          <div className="bg-gradient-to-br from-green-900/40 to-green-950/20 backdrop-blur border border-green-700/30 rounded-xl p-4 sm:p-5 hover:scale-105 transition-transform duration-300">
            <div className="flex items-center justify-between mb-2">
              <div className="text-xs font-bold text-green-400 uppercase tracking-wider">Long</div>
              <div className="text-2xl">↗️</div>
            </div>
            <div className="text-3xl sm:text-4xl font-extrabold text-green-400">{getPercentage(signalStats.long)}%</div>
            <div className="text-xs text-gray-400 mt-1 font-medium">{signalStats.long} signals</div>
          </div>

          <div className="bg-gradient-to-br from-red-900/40 to-red-950/20 backdrop-blur border border-red-700/30 rounded-xl p-4 sm:p-5 hover:scale-105 transition-transform duration-300">
            <div className="flex items-center justify-between mb-2">
              <div className="text-xs font-bold text-red-400 uppercase tracking-wider">Short</div>
              <div className="text-2xl">↘️</div>
            </div>
            <div className="text-3xl sm:text-4xl font-extrabold text-red-400">{getPercentage(signalStats.short)}%</div>
            <div className="text-xs text-gray-400 mt-1 font-medium">{signalStats.short} signals</div>
          </div>

          <div className="bg-gradient-to-br from-gray-800/40 to-gray-900/20 backdrop-blur border border-gray-700/30 rounded-xl p-4 sm:p-5 hover:scale-105 transition-transform duration-300">
            <div className="flex items-center justify-between mb-2">
              <div className="text-xs font-bold text-gray-400 uppercase tracking-wider">Neutral</div>
              <div className="text-2xl">➡️</div>
            </div>
            <div className="text-3xl sm:text-4xl font-extrabold text-gray-400">{getPercentage(signalStats.neutral)}%</div>
            <div className="text-xs text-gray-400 mt-1 font-medium">{signalStats.neutral} signals</div>
          </div>
        </div>
      )}

      {/* Filter bar */}
      <SignalFilterBar
        direction={directionFilter}
        onDirectionChange={setDirectionFilter}
        minConfidence={minConfidence}
        onMinConfidenceChange={setMinConfidence}
        search={searchQuery}
        onSearchChange={setSearchQuery}
        sortField={sortField}
        sortOrder={sortOrder}
        onSortChange={handleSortChange}
      />

      {/* Symbol select + refresh */}
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

      {/* Crypto signals grid — full width, 5 cols on 2xl */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-3 sm:gap-4">
        {filteredCrypto.map(signal => (
          <SignalCard key={signal.symbol} signal={signal} />
        ))}
      </div>

      {filteredProxy.length > 0 && (
        <div className="space-y-3 mt-6">
          <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">Macro Context</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-3 sm:gap-4">
            {filteredProxy.map(signal => (
              <SignalCard key={signal.symbol} signal={signal} />
            ))}
          </div>
        </div>
      )}

      {/* No results */}
      {filteredCrypto.length === 0 && filteredProxy.length === 0 && !loading && signals.length > 0 && (
        <div className="text-center py-12 text-gray-500">
          <p className="text-sm">No signals match the current filters.</p>
          <button
            onClick={() => {
              setDirectionFilter('all');
              setMinConfidence(0);
              setSearchQuery('');
            }}
            className="mt-2 text-xs text-mq-accent hover:underline"
          >
            Clear all filters
          </button>
        </div>
      )}
    </div>
  );
}
