'use client';

import { useState, useEffect } from 'react';
import { MLSignal } from '@/lib/types/ml';
import { getSignal, getSymbols, getDisplayName } from '@/lib/api/ml-trading';
import SignalCard from './SignalCard';

interface SignalGridProps {
  timeframe: '1h' | '4h';
}

export default function SignalGrid({ timeframe }: SignalGridProps) {
  const [signals, setSignals] = useState<MLSignal[]>([]);
  const [availableSymbols, setAvailableSymbols] = useState<string[]>([]);
  const [selectedSymbol, setSelectedSymbol] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);

  useEffect(() => {
    loadSymbols();
  }, []);

  useEffect(() => {
    if (availableSymbols.length > 0) {
      refreshSignals();
      const interval = setInterval(refreshSignals, 60000);
      return () => clearInterval(interval);
    }
  }, [availableSymbols, selectedSymbol, timeframe]);

  const loadSymbols = async () => {
    try {
      const data = await getSymbols();
      let symbols = Object.keys(data.symbols);

      // Filter out ZB_proxy entirely (F1 score too low)
      symbols = symbols.filter(s => s !== 'ZB_proxy');

      setAvailableSymbols(symbols);
    } catch (error) {
      console.error('Error loading symbols:', error);
    }
  };

  const refreshSignals = async () => {
    setLoading(true);
    try {
      let symbolsToFetch = selectedSymbol ? [selectedSymbol] : availableSymbols;

      // Filter out symbols with insufficient 1h data
      if (timeframe === '1h') {
        symbolsToFetch = symbolsToFetch.filter(s =>
          !['ES_proxy', 'NQ_proxy', 'ZB_proxy'].includes(s)
        );
      }

      const results: MLSignal[] = [];
      const BATCH_SIZE = 2;

      for (let i = 0; i < symbolsToFetch.length; i += BATCH_SIZE) {
        const batch = symbolsToFetch.slice(i, i + BATCH_SIZE);
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

        setSignals([...results]);
      }

      setLastUpdate(new Date());
    } catch (error) {
      console.error('Error refreshing signals:', error);
    } finally {
      setLoading(false);
    }
  };

  const signalStats = signals.reduce(
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
        <div className="flex items-center justify-between">
          <div className="h-10 bg-gray-800 rounded w-48 animate-pulse"></div>
          <div className="h-10 bg-gray-800 rounded w-32 animate-pulse"></div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map(i => (
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
    <div className="space-y-4">
      {signalStats.total > 0 && (
        <div className="bg-gray-900/50 backdrop-blur border border-gray-800 rounded-lg p-4">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-white">{signalStats.total}</div>
              <div className="text-xs text-gray-500 uppercase tracking-wider mt-1">Total Signals</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-green-400">{getPercentage(signalStats.long)}%</div>
              <div className="text-xs text-gray-500 uppercase tracking-wider mt-1">Long ({signalStats.long})</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-red-400">{getPercentage(signalStats.short)}%</div>
              <div className="text-xs text-gray-500 uppercase tracking-wider mt-1">Short ({signalStats.short})</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-gray-400">{getPercentage(signalStats.neutral)}%</div>
              <div className="text-xs text-gray-500 uppercase tracking-wider mt-1">Neutral ({signalStats.neutral})</div>
            </div>
          </div>
        </div>
      )}

      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <select
          value={selectedSymbol}
          onChange={(e) => setSelectedSymbol(e.target.value)}
          className="bg-gray-900 border border-gray-800 text-white rounded px-4 py-2 text-sm focus:outline-none focus:border-gray-700"
        >
          <option value="">All Symbols</option>
          {availableSymbols.map(symbol => (
            <option key={symbol} value={symbol}>{getDisplayName(symbol)}</option>
          ))}
        </select>

        <div className="flex items-center gap-3">
          {lastUpdate && (
            <span className="text-xs text-gray-500">
              Updated {lastUpdate.toLocaleTimeString()}
            </span>
          )}
          <button
            onClick={refreshSignals}
            disabled={loading}
            className="bg-gray-900 border border-gray-800 text-white rounded px-4 py-2 text-sm hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {signals.map(signal => (
          <SignalCard key={signal.symbol} signal={signal} />
        ))}
      </div>
    </div>
  );
}
