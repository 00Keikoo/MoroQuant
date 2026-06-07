'use client';

import { useState, useEffect } from 'react';
import Sidebar from '@/components/layout/Sidebar';
import { getSymbols, getBacktestResults, getAllBacktestResults } from '@/lib/api/ml-trading';
import { BacktestResults, BacktestTrade } from '@/lib/types/ml';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, PieChart, Pie, Cell, ReferenceLine, Area, ComposedChart, Legend } from 'recharts';

const CHART_COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899', '#14B8A6', '#F97316'];
const STARTING_CAPITAL = 10000;

export default function BacktestPage() {
  const [symbols, setSymbols] = useState<string[]>([]);
  const [selectedSymbol, setSelectedSymbol] = useState<string>('BTCUSDT');
  const [timeframe, setTimeframe] = useState<'1h' | '4h'>('1h');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<BacktestResults | null>(null);
  const [error, setError] = useState<string>('');
  const [showModal, setShowModal] = useState(false);
  const [compareMode, setCompareMode] = useState(false);
  const [allResults, setAllResults] = useState<BacktestResults[]>([]);
  const [loadingAll, setLoadingAll] = useState(false);
  const [isPolling, setIsPolling] = useState(false);

  const [posCalc, setPosCalc] = useState({
    type: 'long' as 'long' | 'short',
    entryPrice: '',
    currentPrice: '',
    leverage: '10',
    positionSize: '100',
  });

  useEffect(() => {
    const loadSymbols = async () => {
      try {
        const data = await getSymbols();
        const symbolList = Object.keys(data.symbols);
        setSymbols(symbolList);
        if (symbolList.length > 0) {
          setSelectedSymbol(symbolList[0]);
        }
      } catch (err) {
        console.error('Error loading symbols:', err);
      }
    };
    loadSymbols();
  }, []);

  useEffect(() => {
    let pollInterval: NodeJS.Timeout;

    if (isPolling && selectedSymbol) {
      pollInterval = setInterval(async () => {
        try {
          const data = await getBacktestResults(selectedSymbol, timeframe);
          if (!data.error || data.error !== 'no_data') {
            setResults(data);
            setError('');
            setIsPolling(false);
            setShowModal(false);
          }
        } catch (err) {
          console.error('Polling error:', err);
        }
      }, 5000);
    }

    return () => {
      if (pollInterval) clearInterval(pollInterval);
    };
  }, [isPolling, selectedSymbol, timeframe]);

  const handleLoadResults = async () => {
    if (!selectedSymbol) return;

    setLoading(true);
    setError('');
    setResults(null);
    setCompareMode(false);

    try {
      const data = await getBacktestResults(selectedSymbol, timeframe);
      if (data.error) {
        setError(data.message || data.error);
      } else {
        setResults(data);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load backtest results');
    } finally {
      setLoading(false);
    }
  };

  const handleLoadAll = async () => {
    if (symbols.length === 0) return;

    setLoadingAll(true);
    setError('');
    setResults(null);
    setAllResults([]);

    try {
      const data = await getAllBacktestResults(symbols, timeframe);
      setAllResults(data);
      setCompareMode(true);
    } catch (err: any) {
      setError(err.message || 'Failed to load backtest results');
    } finally {
      setLoadingAll(false);
    }
  };

  const handleRunBacktest = () => {
    setShowModal(true);
    setIsPolling(true);
  };

  const getAggregateStats = () => {
    if (allResults.length === 0) return null;

    const validResults = allResults.filter(r => r.metrics);
    if (validResults.length === 0) return null;

    const sorted = [...validResults].sort((a, b) =>
      (b.metrics!.total_return_pct) - (a.metrics!.total_return_pct)
    );

    const avgWinRate = validResults.reduce((sum, r) => sum + r.metrics!.win_rate_pct, 0) / validResults.length;
    const totalTrades = validResults.reduce((sum, r) => sum + r.metrics!.total_trades, 0);

    return {
      best: sorted[0],
      worst: sorted[sorted.length - 1],
      avgWinRate,
      totalTrades,
    };
  };

  const calculateDrawdowns = (equityCurve: { timestamp: number; equity: number }[]) => {
    const drawdowns: { start: number; end: number; depth: number }[] = [];
    let peak = equityCurve[0]?.equity || STARTING_CAPITAL;
    let drawdownStart = 0;
    let inDrawdown = false;
    let maxDrawdown = 0;
    let maxDrawdownPeriod = { start: 0, end: 0 };

    equityCurve.forEach((point, idx) => {
      if (point.equity > peak) {
        if (inDrawdown) {
          drawdowns.push({
            start: drawdownStart,
            end: idx - 1,
            depth: ((peak - equityCurve[idx - 1].equity) / peak) * 100,
          });
          inDrawdown = false;
        }
        peak = point.equity;
      } else if (point.equity < peak) {
        if (!inDrawdown) {
          drawdownStart = idx;
          inDrawdown = true;
        }
        const currentDrawdown = ((peak - point.equity) / peak) * 100;
        if (currentDrawdown > maxDrawdown) {
          maxDrawdown = currentDrawdown;
          maxDrawdownPeriod = { start: drawdownStart, end: idx };
        }
      }
    });

    if (inDrawdown) {
      drawdowns.push({
        start: drawdownStart,
        end: equityCurve.length - 1,
        depth: ((peak - equityCurve[equityCurve.length - 1].equity) / peak) * 100,
      });
    }

    return { drawdowns, maxDrawdownPeriod };
  };

  const getPnLDistribution = (trades: BacktestTrade[]) => {
    const bins = [-100, -50, -25, -10, -5, 0, 5, 10, 25, 50, 100];
    const distribution = bins.slice(0, -1).map((binStart, idx) => ({
      range: `${binStart}% to ${bins[idx + 1]}%`,
      count: 0,
    }));

    trades.forEach(trade => {
      const pnlPct = trade.pnl_pct;
      const binIdx = bins.findIndex((bin, idx) => idx < bins.length - 1 && pnlPct >= bin && pnlPct < bins[idx + 1]);
      if (binIdx >= 0 && binIdx < distribution.length) {
        distribution[binIdx].count++;
      }
    });

    return distribution;
  };

  const getLongShortStats = (trades: BacktestTrade[]) => {
    const longTrades = trades.filter(t => t.type === 'long');
    const shortTrades = trades.filter(t => t.type === 'short');

    const longWins = longTrades.filter(t => t.pnl > 0).length;
    const shortWins = shortTrades.filter(t => t.pnl > 0).length;

    return [
      {
        name: 'Long',
        count: longTrades.length,
        winRate: longTrades.length > 0 ? (longWins / longTrades.length) * 100 : 0,
        color: '#10B981',
      },
      {
        name: 'Short',
        count: shortTrades.length,
        winRate: shortTrades.length > 0 ? (shortWins / shortTrades.length) * 100 : 0,
        color: '#EF4444',
      },
    ];
  };

  const calculatePosition = () => {
    const entry = parseFloat(posCalc.entryPrice);
    const current = parseFloat(posCalc.currentPrice);
    const lev = parseFloat(posCalc.leverage);
    const size = parseFloat(posCalc.positionSize);

    if (!entry || !current || !lev || !size) return null;

    let pnlPct: number;
    let liquidationPrice: number;

    if (posCalc.type === 'long') {
      pnlPct = ((current - entry) / entry) * 100;
      liquidationPrice = entry * (1 - 1 / lev + 0.004);
    } else {
      pnlPct = ((entry - current) / entry) * 100;
      liquidationPrice = entry * (1 + 1 / lev - 0.004);
    }

    const pnlUSD = (pnlPct / 100) * size * lev;

    return {
      pnlUSD: pnlUSD.toFixed(2),
      pnlPct: (pnlPct * lev).toFixed(2),
      liquidationPrice: liquidationPrice.toFixed(2),
      inProfit: pnlUSD >= 0,
    };
  };

  const positionResults = calculatePosition();

  const chartData = results?.equity_curve?.map((point, idx) => ({
    timestamp: new Date(point.timestamp * 1000).toLocaleDateString(),
    equity: point.equity,
    date: new Date(point.timestamp * 1000),
    index: idx,
  })) || [];

  const { drawdowns, maxDrawdownPeriod } = results?.equity_curve
    ? calculateDrawdowns(results.equity_curve)
    : { drawdowns: [], maxDrawdownPeriod: { start: 0, end: 0 } };

  const pnlDistribution = results?.trades ? getPnLDistribution(results.trades) : [];
  const longShortStats = results?.trades ? getLongShortStats(results.trades) : [];

  const aggregateStats = getAggregateStats();

  const compareTableData = allResults
    .filter(r => r.metrics)
    .map(r => ({
      symbol: r.symbol,
      timeframe: r.timeframe,
      returnPct: r.metrics!.total_return_pct,
      winRate: r.metrics!.win_rate_pct,
      sharpe: r.metrics!.sharpe_ratio,
      maxDD: r.metrics!.max_drawdown_pct,
      trades: r.metrics!.total_trades,
    }))
    .sort((a, b) => b.returnPct - a.returnPct);

  const multiSymbolChartData = (() => {
    if (allResults.length === 0) return [];

    const timestampMap = new Map<number, any>();

    allResults.forEach((result, idx) => {
      if (!result.equity_curve || !result.metrics) return;

      result.equity_curve.forEach(point => {
        if (!timestampMap.has(point.timestamp)) {
          timestampMap.set(point.timestamp, {
            timestamp: new Date(point.timestamp * 1000).toLocaleDateString(),
            date: new Date(point.timestamp * 1000),
          });
        }
        const entry = timestampMap.get(point.timestamp)!;
        entry[result.symbol] = point.equity;
      });
    });

    return Array.from(timestampMap.values()).sort((a, b) => a.date - b.date);
  })();

  const backtestCommand = `venv/bin/python3 cli.py backtest --symbol ${selectedSymbol} --timeframe ${timeframe}`;

  const copyToClipboard = () => {
    navigator.clipboard.writeText(backtestCommand);
  };

  return (
    <div className="flex h-screen bg-black text-white">
      <Sidebar />

      <div className="flex-1 flex overflow-hidden">
        <div className="flex-1 p-6 overflow-y-auto">
          <div className="max-w-7xl mx-auto space-y-6">
            <div className="bg-gradient-to-r from-purple-900/30 via-blue-900/20 to-purple-900/30 rounded-2xl p-8 border border-purple-800/30">
              <h1 className="text-4xl font-bold text-white mb-2">Backtest Engine</h1>
              <p className="text-lg text-gray-300">Walk-forward backtesting with ML signals</p>
            </div>

            <div className="bg-gray-900 rounded-xl p-6 border border-gray-800">
              <h2 className="text-lg font-bold text-white mb-4">Select Symbol & Timeframe</h2>
              <div className="flex gap-4 items-end">
                <div className="flex-1">
                  <label className="block text-sm text-gray-400 mb-2">Symbol</label>
                  <select
                    value={selectedSymbol}
                    onChange={(e) => setSelectedSymbol(e.target.value)}
                    className="w-full bg-gray-800 text-white border border-gray-700 rounded-lg px-4 py-3 focus:outline-none focus:border-blue-500"
                  >
                    {symbols.map((sym) => (
                      <option key={sym} value={sym}>
                        {sym}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm text-gray-400 mb-2">Timeframe</label>
                  <div className="flex gap-2">
                    <button
                      onClick={() => setTimeframe('1h')}
                      className={`px-6 py-3 rounded-lg font-bold transition-all ${
                        timeframe === '1h'
                          ? 'bg-blue-600 text-white'
                          : 'bg-gray-800 text-gray-400 border border-gray-700'
                      }`}
                    >
                      1h
                    </button>
                    <button
                      onClick={() => setTimeframe('4h')}
                      className={`px-6 py-3 rounded-lg font-bold transition-all ${
                        timeframe === '4h'
                          ? 'bg-blue-600 text-white'
                          : 'bg-gray-800 text-gray-400 border border-gray-700'
                      }`}
                    >
                      4h
                    </button>
                  </div>
                </div>

                <button
                  onClick={handleRunBacktest}
                  disabled={!selectedSymbol}
                  className="px-8 py-3 bg-purple-600 hover:bg-purple-700 disabled:bg-gray-700 disabled:cursor-not-allowed text-white font-bold rounded-lg transition-all"
                >
                  Run Backtest
                </button>

                <button
                  onClick={handleLoadResults}
                  disabled={loading || !selectedSymbol}
                  className="px-8 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 disabled:cursor-not-allowed text-white font-bold rounded-lg transition-all"
                >
                  {loading ? 'Loading...' : 'Load Results'}
                </button>

                <button
                  onClick={handleLoadAll}
                  disabled={loadingAll}
                  className="px-8 py-3 bg-green-600 hover:bg-green-700 disabled:bg-gray-700 disabled:cursor-not-allowed text-white font-bold rounded-lg transition-all"
                >
                  {loadingAll ? 'Loading All...' : 'Compare All'}
                </button>
              </div>
            </div>

            {showModal && (
              <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50" onClick={() => { setShowModal(false); setIsPolling(false); }}>
                <div className="bg-gray-900 rounded-xl p-8 border border-gray-800 max-w-2xl w-full mx-4" onClick={(e) => e.stopPropagation()}>
                  <h2 className="text-2xl font-bold text-white mb-4">Run Backtest from Terminal</h2>
                  <div className="bg-blue-900/30 border border-blue-800/50 rounded-lg p-4 mb-4">
                    <p className="text-blue-200 text-sm font-semibold mb-2">Backtest must be run from terminal first to generate data</p>
                    <p className="text-blue-300/80 text-sm">Copy this command and run it in your terminal:</p>
                  </div>
                  <div className="bg-gray-800 rounded-lg p-4 mb-4 flex items-center justify-between">
                    <code className="text-green-400 text-sm">{backtestCommand}</code>
                    <button
                      onClick={copyToClipboard}
                      className="ml-4 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-bold rounded transition-all"
                    >
                      Copy
                    </button>
                  </div>
                  {isPolling && (
                    <div className="bg-yellow-900/20 border border-yellow-800/50 rounded-lg p-3 mb-4">
                      <p className="text-yellow-300 text-sm flex items-center">
                        <span className="animate-pulse mr-2">●</span>
                        Auto-polling every 5 seconds for results...
                      </p>
                    </div>
                  )}
                  <p className="text-gray-400 text-sm mb-6">
                    Results will load automatically when available. You can close this dialog and continue working.
                  </p>
                  <button
                    onClick={() => { setShowModal(false); setIsPolling(false); }}
                    className="w-full px-6 py-3 bg-gray-800 hover:bg-gray-700 text-white font-bold rounded-lg transition-all"
                  >
                    Close
                  </button>
                </div>
              </div>
            )}

            {error && (
              <div className="bg-gray-900 rounded-xl p-6 border border-yellow-800/50">
                <p className="text-yellow-400 font-semibold mb-2">No backtest data available</p>
                <p className="text-gray-400 text-sm">
                  Click "Run Backtest" above to get the terminal command, or run manually:
                  <code className="block mt-2 bg-gray-800 px-3 py-2 rounded text-green-400">
                    {backtestCommand}
                  </code>
                </p>
              </div>
            )}

            {compareMode && allResults.length > 0 && (
              <>
                {aggregateStats && (
                  <div className="bg-gradient-to-r from-blue-900/30 via-purple-900/20 to-blue-900/30 rounded-xl p-6 border border-blue-800/30">
                    <h2 className="text-xl font-bold text-white mb-4">Multi-Symbol Performance Summary</h2>
                    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                      <div className="bg-gray-900/50 rounded-lg p-4">
                        <p className="text-sm text-gray-400 mb-1">Best Performer</p>
                        <p className="text-2xl font-bold text-green-400">{aggregateStats.best.symbol}</p>
                        <p className="text-sm text-green-300">+{aggregateStats.best.metrics!.total_return_pct.toFixed(2)}%</p>
                      </div>
                      <div className="bg-gray-900/50 rounded-lg p-4">
                        <p className="text-sm text-gray-400 mb-1">Worst Performer</p>
                        <p className="text-2xl font-bold text-red-400">{aggregateStats.worst.symbol}</p>
                        <p className="text-sm text-red-300">{aggregateStats.worst.metrics!.total_return_pct.toFixed(2)}%</p>
                      </div>
                      <div className="bg-gray-900/50 rounded-lg p-4">
                        <p className="text-sm text-gray-400 mb-1">Avg Win Rate</p>
                        <p className="text-2xl font-bold text-white">{aggregateStats.avgWinRate.toFixed(2)}%</p>
                      </div>
                      <div className="bg-gray-900/50 rounded-lg p-4">
                        <p className="text-sm text-gray-400 mb-1">Total Trades</p>
                        <p className="text-2xl font-bold text-white">{aggregateStats.totalTrades}</p>
                      </div>
                    </div>
                  </div>
                )}

                {allResults.filter(r => r.metrics && r.equity_curve.length > 0).length > 0 && (
                  <div className="bg-gray-900 rounded-xl p-6 border border-gray-800">
                    <h2 className="text-lg font-bold text-white mb-4">All Equity Curves</h2>
                    <ResponsiveContainer width="100%" height={400}>
                      <LineChart data={multiSymbolChartData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                        <XAxis dataKey="timestamp" stroke="#9CA3AF" />
                        <YAxis stroke="#9CA3AF" />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: '#1F2937',
                            border: '1px solid #374151',
                            borderRadius: '8px',
                          }}
                        />
                        <Legend />
                        <ReferenceLine y={STARTING_CAPITAL} stroke="#6B7280" strokeDasharray="3 3" />
                        {allResults.filter(r => r.metrics).map((result, idx) => (
                          <Line
                            key={result.symbol}
                            type="monotone"
                            dataKey={result.symbol}
                            stroke={CHART_COLORS[idx % CHART_COLORS.length]}
                            strokeWidth={2}
                            dot={false}
                          />
                        ))}
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                )}

                {compareTableData.length > 0 && (
                  <div className="bg-gray-900 rounded-xl p-6 border border-gray-800">
                    <h2 className="text-lg font-bold text-white mb-4">Comparison Table</h2>
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="border-b border-gray-800">
                            <th className="text-left py-3 text-gray-400 font-semibold">Symbol</th>
                            <th className="text-center py-3 text-gray-400 font-semibold">TF</th>
                            <th className="text-right py-3 text-gray-400 font-semibold">Return %</th>
                            <th className="text-right py-3 text-gray-400 font-semibold">Win Rate</th>
                            <th className="text-right py-3 text-gray-400 font-semibold">Sharpe</th>
                            <th className="text-right py-3 text-gray-400 font-semibold">Max DD</th>
                            <th className="text-right py-3 text-gray-400 font-semibold">Trades</th>
                          </tr>
                        </thead>
                        <tbody>
                          {compareTableData.map((row, idx) => (
                            <tr
                              key={row.symbol}
                              className={`border-b border-gray-800 ${
                                idx === 0
                                  ? 'bg-green-900/20'
                                  : idx === compareTableData.length - 1
                                  ? 'bg-red-900/20'
                                  : ''
                              }`}
                            >
                              <td className="py-3 font-bold text-white">{row.symbol}</td>
                              <td className="text-center py-3 text-gray-300">{row.timeframe}</td>
                              <td className={`text-right py-3 font-bold ${row.returnPct >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                {row.returnPct >= 0 ? '+' : ''}{row.returnPct.toFixed(2)}%
                              </td>
                              <td className="text-right py-3 text-gray-300">{row.winRate.toFixed(2)}%</td>
                              <td className="text-right py-3 text-gray-300">{row.sharpe.toFixed(2)}</td>
                              <td className="text-right py-3 text-red-400">{row.maxDD.toFixed(2)}%</td>
                              <td className="text-right py-3 text-gray-300">{row.trades}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                {allResults.filter(r => r.error === 'no_data').length > 0 && (
                  <div className="bg-gray-900 rounded-xl p-6 border border-gray-800">
                    <h2 className="text-lg font-bold text-white mb-4">Symbols Without Backtest Data</h2>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                      {allResults.filter(r => r.error === 'no_data').map((result) => {
                        const cmd = `venv/bin/python3 cli.py backtest --symbol ${result.symbol} --timeframe ${result.timeframe}`;
                        return (
                          <div key={result.symbol} className="bg-gray-800 rounded-lg p-4 border border-gray-700">
                            <h3 className="font-bold text-white mb-2">{result.symbol}</h3>
                            <p className="text-sm text-gray-400 mb-3">No data — run backtest first:</p>
                            <div className="bg-gray-900 rounded p-2 mb-2">
                              <code className="text-xs text-green-400 break-all">{cmd}</code>
                            </div>
                            <button
                              onClick={() => {
                                navigator.clipboard.writeText(cmd);
                              }}
                              className="w-full px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-bold rounded transition-all"
                            >
                              Copy Command
                            </button>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </>
            )}

            {results && results.metrics && (
              <>
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                  <div className="bg-gray-900 rounded-xl p-6 border border-gray-800">
                    <p className="text-sm text-gray-400 mb-1">Total Return</p>
                    <p className={`text-3xl font-bold ${results.metrics.total_return_pct >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {results.metrics.total_return_pct >= 0 ? '+' : ''}{results.metrics.total_return_pct.toFixed(2)}%
                    </p>
                  </div>

                  <div className="bg-gray-900 rounded-xl p-6 border border-gray-800">
                    <p className="text-sm text-gray-400 mb-1">Win Rate</p>
                    <p className="text-3xl font-bold text-white">{results.metrics.win_rate_pct.toFixed(2)}%</p>
                  </div>

                  <div className="bg-gray-900 rounded-xl p-6 border border-gray-800">
                    <p className="text-sm text-gray-400 mb-1">Profit Factor</p>
                    <p className="text-3xl font-bold text-white">{results.metrics.profit_factor.toFixed(2)}</p>
                  </div>

                  <div className="bg-gray-900 rounded-xl p-6 border border-gray-800">
                    <p className="text-sm text-gray-400 mb-1">Max Drawdown</p>
                    <p className="text-3xl font-bold text-red-400">{results.metrics.max_drawdown_pct.toFixed(2)}%</p>
                  </div>

                  <div className="bg-gray-900 rounded-xl p-6 border border-gray-800">
                    <p className="text-sm text-gray-400 mb-1">Sharpe Ratio</p>
                    <p className="text-3xl font-bold text-white">{results.metrics.sharpe_ratio.toFixed(2)}</p>
                  </div>

                  <div className="bg-gray-900 rounded-xl p-6 border border-gray-800">
                    <p className="text-sm text-gray-400 mb-1">Total Trades</p>
                    <p className="text-3xl font-bold text-white">{results.metrics.total_trades}</p>
                  </div>

                  <div className="bg-gray-900 rounded-xl p-6 border border-gray-800 col-span-2">
                    <p className="text-sm text-gray-400 mb-1">Avg Profit/Trade</p>
                    <p className={`text-3xl font-bold ${results.metrics.avg_profit_per_trade >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      ${results.metrics.avg_profit_per_trade.toFixed(2)}
                    </p>
                  </div>
                </div>

                <div className="bg-gray-900 rounded-xl p-6 border border-gray-800">
                  <h2 className="text-lg font-bold text-white mb-4">Equity Curve</h2>
                  <ResponsiveContainer width="100%" height={400}>
                    <ComposedChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                      <XAxis dataKey="timestamp" stroke="#9CA3AF" />
                      <YAxis stroke="#9CA3AF" />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: '#1F2937',
                          border: '1px solid #374151',
                          borderRadius: '8px',
                        }}
                        content={({ active, payload }) => {
                          if (active && payload && payload.length > 0) {
                            const data = payload[0].payload;
                            const pnl = data.equity - STARTING_CAPITAL;
                            return (
                              <div className="bg-gray-900 border border-gray-700 rounded p-3">
                                <p className="text-gray-400 text-xs mb-1">{data.timestamp}</p>
                                <p className="text-white font-bold">${data.equity.toFixed(2)}</p>
                                <p className={`text-xs ${pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                  {pnl >= 0 ? '+' : ''}${pnl.toFixed(2)} from start
                                </p>
                              </div>
                            );
                          }
                          return null;
                        }}
                      />
                      <ReferenceLine
                        y={STARTING_CAPITAL}
                        stroke="#6B7280"
                        strokeDasharray="3 3"
                        label={{ value: `Start: $${STARTING_CAPITAL}`, fill: '#9CA3AF', fontSize: 12 }}
                      />
                      {drawdowns.map((dd, idx) => (
                        chartData[dd.start] && chartData[dd.end] && (
                          <Area
                            key={idx}
                            type="monotone"
                            dataKey="equity"
                            fill="#EF4444"
                            fillOpacity={0.1}
                            stroke="none"
                            data={chartData.slice(dd.start, dd.end + 1)}
                          />
                        )
                      ))}
                      <Line
                        type="monotone"
                        dataKey="equity"
                        stroke={results.metrics.total_return_pct >= 0 ? '#10B981' : '#EF4444'}
                        strokeWidth={2}
                        dot={false}
                      />
                      {results.trades && results.trades.map((trade, idx) => {
                        const entryPoint = chartData.find(d => d.index === trade.entry_idx);
                        return entryPoint ? (
                          <circle
                            key={`trade-${idx}`}
                            cx={0}
                            cy={0}
                            r={3}
                            fill={trade.pnl >= 0 ? '#10B981' : '#EF4444'}
                            style={{
                              transform: `translate(${(trade.entry_idx / chartData.length) * 100}%, 0)`,
                            }}
                          />
                        ) : null;
                      })}
                    </ComposedChart>
                  </ResponsiveContainer>
                  {maxDrawdownPeriod.start !== maxDrawdownPeriod.end && chartData[maxDrawdownPeriod.start] && (
                    <p className="text-xs text-gray-400 mt-2">
                      Max drawdown period: {chartData[maxDrawdownPeriod.start].timestamp} to {chartData[maxDrawdownPeriod.end]?.timestamp}
                    </p>
                  )}
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                  <div className="bg-gray-900 rounded-xl p-6 border border-gray-800">
                    <h2 className="text-lg font-bold text-white mb-4">PnL Distribution</h2>
                    <ResponsiveContainer width="100%" height={250}>
                      <BarChart data={pnlDistribution}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                        <XAxis dataKey="range" stroke="#9CA3AF" angle={-45} textAnchor="end" height={80} fontSize={10} />
                        <YAxis stroke="#9CA3AF" />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: '#1F2937',
                            border: '1px solid #374151',
                            borderRadius: '8px',
                          }}
                        />
                        <Bar dataKey="count" fill="#3B82F6" />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>

                  <div className="bg-gray-900 rounded-xl p-6 border border-gray-800">
                    <h2 className="text-lg font-bold text-white mb-4">Long vs Short Performance</h2>
                    <ResponsiveContainer width="100%" height={250}>
                      <PieChart>
                        <Pie
                          data={longShortStats}
                          cx="50%"
                          cy="50%"
                          labelLine={false}
                          label={(entry: any) => `${entry.name}: ${entry.count} (${entry.winRate.toFixed(1)}% WR)`}
                          outerRadius={80}
                          fill="#8884d8"
                          dataKey="count"
                        >
                          {longShortStats.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={entry.color} />
                          ))}
                        </Pie>
                        <Tooltip
                          contentStyle={{
                            backgroundColor: '#1F2937',
                            border: '1px solid #374151',
                            borderRadius: '8px',
                          }}
                        />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                {results.trades && results.trades.length > 0 && (
                  <div className="bg-gray-900 rounded-xl p-6 border border-gray-800">
                    <h2 className="text-lg font-bold text-white mb-4">Trade Log (Last 20)</h2>
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="border-b border-gray-800">
                            <th className="text-left py-3 text-gray-400 font-semibold">Type</th>
                            <th className="text-right py-3 text-gray-400 font-semibold">Entry</th>
                            <th className="text-right py-3 text-gray-400 font-semibold">Exit</th>
                            <th className="text-right py-3 text-gray-400 font-semibold">PnL $</th>
                            <th className="text-right py-3 text-gray-400 font-semibold">PnL %</th>
                            <th className="text-right py-3 text-gray-400 font-semibold">Hold</th>
                          </tr>
                        </thead>
                        <tbody>
                          {results.trades.slice(-20).reverse().map((trade, idx) => (
                            <tr
                              key={idx}
                              className={`border-b border-gray-800 ${trade.pnl >= 0 ? 'bg-green-900/10' : 'bg-red-900/10'}`}
                            >
                              <td className="py-3">
                                <span className={`px-2 py-1 rounded text-xs font-bold ${trade.type === 'long' ? 'bg-green-600' : 'bg-red-600'}`}>
                                  {trade.type.toUpperCase()}
                                </span>
                              </td>
                              <td className="text-right py-3 text-gray-300">${trade.entry_price.toFixed(2)}</td>
                              <td className="text-right py-3 text-gray-300">${trade.exit_price.toFixed(2)}</td>
                              <td className={`text-right py-3 font-bold ${trade.pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                ${trade.pnl.toFixed(2)}
                              </td>
                              <td className={`text-right py-3 font-bold ${trade.pnl_pct >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                {trade.pnl_pct >= 0 ? '+' : ''}{trade.pnl_pct.toFixed(2)}%
                              </td>
                              <td className="text-right py-3 text-gray-400">{trade.hold_candles}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        </div>

        <div className="w-80 bg-gray-950 border-l border-gray-800 p-6 overflow-y-auto">
          <h2 className="text-lg font-bold text-white mb-4">Position Calculator</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm text-gray-400 mb-2">Position Type</label>
              <div className="flex gap-2">
                <button
                  onClick={() => setPosCalc({ ...posCalc, type: 'long' })}
                  className={`flex-1 px-4 py-3 rounded-lg font-bold transition-all ${
                    posCalc.type === 'long'
                      ? 'bg-green-600 text-white'
                      : 'bg-gray-800 text-gray-400 border border-gray-700'
                  }`}
                >
                  LONG
                </button>
                <button
                  onClick={() => setPosCalc({ ...posCalc, type: 'short' })}
                  className={`flex-1 px-4 py-3 rounded-lg font-bold transition-all ${
                    posCalc.type === 'short'
                      ? 'bg-red-600 text-white'
                      : 'bg-gray-800 text-gray-400 border border-gray-700'
                  }`}
                >
                  SHORT
                </button>
              </div>
            </div>

            <div>
              <label className="block text-sm text-gray-400 mb-2">Entry Price</label>
              <input
                type="number"
                value={posCalc.entryPrice}
                onChange={(e) => setPosCalc({ ...posCalc, entryPrice: e.target.value })}
                className="w-full bg-gray-800 text-white border border-gray-700 rounded-lg px-3 py-2 focus:outline-none focus:border-blue-500"
                placeholder="0.00"
              />
            </div>

            <div>
              <label className="block text-sm text-gray-400 mb-2">Current Price</label>
              <input
                type="number"
                value={posCalc.currentPrice}
                onChange={(e) => setPosCalc({ ...posCalc, currentPrice: e.target.value })}
                className="w-full bg-gray-800 text-white border border-gray-700 rounded-lg px-3 py-2 focus:outline-none focus:border-blue-500"
                placeholder="0.00"
              />
            </div>

            <div>
              <label className="block text-sm text-gray-400 mb-2">Leverage</label>
              <input
                type="number"
                value={posCalc.leverage}
                onChange={(e) => setPosCalc({ ...posCalc, leverage: e.target.value })}
                className="w-full bg-gray-800 text-white border border-gray-700 rounded-lg px-3 py-2 focus:outline-none focus:border-blue-500"
                placeholder="10"
              />
            </div>

            <div>
              <label className="block text-sm text-gray-400 mb-2">Position Size (USDT)</label>
              <input
                type="number"
                value={posCalc.positionSize}
                onChange={(e) => setPosCalc({ ...posCalc, positionSize: e.target.value })}
                className="w-full bg-gray-800 text-white border border-gray-700 rounded-lg px-3 py-2 focus:outline-none focus:border-blue-500"
                placeholder="100"
              />
            </div>

            {positionResults && (
              <div className="mt-6 pt-6 border-t border-gray-800 space-y-3">
                <div className={`rounded-lg p-4 ${positionResults.inProfit ? 'bg-green-900/30 border border-green-700' : 'bg-red-900/30 border border-red-700'}`}>
                  <p className="text-xs text-gray-400 mb-1">Status</p>
                  <p className={`text-lg font-bold ${positionResults.inProfit ? 'text-green-400' : 'text-red-400'}`}>
                    {positionResults.inProfit ? 'In Profit ✓' : 'In Loss ✗'}
                  </p>
                </div>

                <div className="bg-gray-800 rounded-lg p-4">
                  <p className="text-xs text-gray-400 mb-1">PnL (USD)</p>
                  <p className={`text-2xl font-bold ${parseFloat(positionResults.pnlUSD) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    ${positionResults.pnlUSD}
                  </p>
                </div>

                <div className="bg-gray-800 rounded-lg p-4">
                  <p className="text-xs text-gray-400 mb-1">PnL (%)</p>
                  <p className={`text-2xl font-bold ${parseFloat(positionResults.pnlPct) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {parseFloat(positionResults.pnlPct) >= 0 ? '+' : ''}{positionResults.pnlPct}%
                  </p>
                </div>

                <div className="bg-gray-800 rounded-lg p-4">
                  <p className="text-xs text-gray-400 mb-1">Liquidation Price</p>
                  <p className="text-2xl font-bold text-red-400">${positionResults.liquidationPrice}</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
