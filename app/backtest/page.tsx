'use client';

import { useState, useEffect } from 'react';
import Sidebar from '@/components/layout/Sidebar';
import { getSymbols, getBacktestResults } from '@/lib/api/ml-trading';
import { BacktestResults } from '@/lib/types/ml';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

export default function BacktestPage() {
  const [symbols, setSymbols] = useState<string[]>([]);
  const [selectedSymbol, setSelectedSymbol] = useState<string>('BTCUSDT');
  const [timeframe, setTimeframe] = useState<'1h' | '4h'>('1h');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<BacktestResults | null>(null);
  const [error, setError] = useState<string>('');
  const [showModal, setShowModal] = useState(false);

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

  const handleLoadResults = async () => {
    if (!selectedSymbol) return;

    setLoading(true);
    setError('');
    setResults(null);

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

  const chartData = results?.equity_curve?.map((point) => ({
    timestamp: new Date(point.timestamp * 1000).toLocaleDateString(),
    equity: point.equity,
  })) || [];

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
                  onClick={() => setShowModal(true)}
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
              </div>
            </div>

            {showModal && (
              <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50" onClick={() => setShowModal(false)}>
                <div className="bg-gray-900 rounded-xl p-8 border border-gray-800 max-w-2xl w-full mx-4" onClick={(e) => e.stopPropagation()}>
                  <h2 className="text-2xl font-bold text-white mb-4">Run Backtest from Terminal</h2>
                  <p className="text-gray-400 mb-4">
                    Backtests must be run from the terminal. Copy and paste the command below:
                  </p>
                  <div className="bg-gray-800 rounded-lg p-4 mb-4 flex items-center justify-between">
                    <code className="text-green-400 text-sm">{backtestCommand}</code>
                    <button
                      onClick={copyToClipboard}
                      className="ml-4 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-bold rounded transition-all"
                    >
                      Copy
                    </button>
                  </div>
                  <p className="text-gray-500 text-sm mb-6">
                    After running the backtest, click "Load Results" to view the results in the dashboard.
                  </p>
                  <button
                    onClick={() => setShowModal(false)}
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
                  <ResponsiveContainer width="100%" height={300}>
                    <LineChart data={chartData}>
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
                      <Line
                        type="monotone"
                        dataKey="equity"
                        stroke={results.metrics.total_return_pct >= 0 ? '#10B981' : '#EF4444'}
                        strokeWidth={2}
                        dot={false}
                      />
                    </LineChart>
                  </ResponsiveContainer>
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
