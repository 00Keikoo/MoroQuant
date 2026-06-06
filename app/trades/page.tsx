'use client';

import { useState, useEffect } from 'react';
import Sidebar from '@/components/layout/Sidebar';
import { getSignal, closeTrade, getTradeHistory } from '@/lib/api/ml-trading';
import { OpenPosition, ClosedTrade, TradeHistoryResponse } from '@/lib/types/ml';

const CRYPTO_SYMBOLS = [
  'BTCUSDT',
  'ETHUSDT',
  'BNBUSDT',
  'SOLUSDT',
  'HYPEUSDT',
  'ADAUSDT',
  'DOGEUSDT',
  'XRPUSDT',
  'AVAXUSDT',
  'LINKUSDT',
  'DOTUSDT',
  'UNIUSDT',
  'ATOMUSDT',
  'LTCUSDT',
  'NEARUSDT',
];

export default function TradesPage() {
  const [openPositions, setOpenPositions] = useState<OpenPosition[]>([]);
  const [tradeHistory, setTradeHistory] = useState<TradeHistoryResponse | null>(null);
  const [livePrices, setLivePrices] = useState<Record<string, number>>({});
  const [showCloseModal, setShowCloseModal] = useState(false);
  const [positionToClose, setPositionToClose] = useState<OpenPosition | null>(null);
  const [exitPrice, setExitPrice] = useState('');
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [positionToDelete, setPositionToDelete] = useState<OpenPosition | null>(null);

  const [newPosition, setNewPosition] = useState({
    symbol: 'BTCUSDT',
    direction: 'long' as 'long' | 'short',
    entryPrice: '',
    leverage: '10',
    sizeUsdt: '100',
    notes: '',
  });

  useEffect(() => {
    const stored = localStorage.getItem('openPositions');
    if (stored) {
      setOpenPositions(JSON.parse(stored));
    }
  }, []);

  useEffect(() => {
    localStorage.setItem('openPositions', JSON.stringify(openPositions));
  }, [openPositions]);

  useEffect(() => {
    loadTradeHistory();
  }, []);

  useEffect(() => {
    if (openPositions.length === 0) return;

    const fetchPrices = async () => {
      const symbols = [...new Set(openPositions.map(p => p.symbol))];
      const prices: Record<string, number> = {};

      await Promise.all(
        symbols.map(async (symbol) => {
          try {
            const res = await fetch(`/api/price/${symbol}`, {
              signal: AbortSignal.timeout(10000),
            });
            const data = await res.json();
            if (data.price) {
              prices[symbol] = data.price;
            }
          } catch (err) {
            console.error(`Error fetching price for ${symbol}:`, err);
          }
        })
      );

      setLivePrices(prices);
    };

    fetchPrices();
    const interval = setInterval(fetchPrices, 10000);
    return () => clearInterval(interval);
  }, [openPositions]);

  const loadTradeHistory = async () => {
    try {
      const data = await getTradeHistory();
      setTradeHistory(data);
    } catch (err) {
      console.error('Error loading trade history:', err);
    }
  };

  const handleOpenPosition = () => {
    if (!newPosition.entryPrice || !newPosition.leverage || !newPosition.sizeUsdt) return;

    const position: OpenPosition = {
      id: Date.now().toString(),
      symbol: newPosition.symbol,
      direction: newPosition.direction,
      entry_price: parseFloat(newPosition.entryPrice),
      leverage: parseFloat(newPosition.leverage),
      size_usdt: parseFloat(newPosition.sizeUsdt),
      opened_at: new Date().toISOString(),
      notes: newPosition.notes,
    };

    setOpenPositions([...openPositions, position]);
    setNewPosition({
      symbol: 'BTCUSDT',
      direction: 'long',
      entryPrice: '',
      leverage: '10',
      sizeUsdt: '100',
      notes: '',
    });
  };

  const handleClosePositionClick = (position: OpenPosition) => {
    setPositionToClose(position);
    const currentPrice = livePrices[position.symbol] || position.entry_price;
    setExitPrice(currentPrice.toString());
    setShowCloseModal(true);
  };

  const handleDeletePositionClick = (position: OpenPosition) => {
    setPositionToDelete(position);
    setShowDeleteModal(true);
  };

  const handleDeletePositionConfirm = () => {
    if (!positionToDelete) return;
    setOpenPositions(openPositions.filter(p => p.id !== positionToDelete.id));
    setShowDeleteModal(false);
    setPositionToDelete(null);
  };

  const handleClosePositionConfirm = async () => {
    if (!positionToClose || !exitPrice) return;

    const exit = parseFloat(exitPrice);
    const entry = positionToClose.entry_price;
    const leverage = positionToClose.leverage;
    const size = positionToClose.size_usdt;

    let pnlPct: number;
    if (positionToClose.direction === 'long') {
      pnlPct = ((exit - entry) / entry) * 100;
    } else {
      pnlPct = ((entry - exit) / entry) * 100;
    }

    const pnl = (pnlPct / 100) * size * leverage;

    const closedTrade: ClosedTrade = {
      symbol: positionToClose.symbol,
      direction: positionToClose.direction,
      entry_price: entry,
      exit_price: exit,
      leverage: leverage,
      size_usdt: size,
      pnl: pnl,
      pnl_pct: pnlPct * leverage,
      opened_at: positionToClose.opened_at,
      closed_at: new Date().toISOString(),
      notes: positionToClose.notes,
    };

    try {
      await closeTrade(closedTrade);
      setOpenPositions(openPositions.filter(p => p.id !== positionToClose.id));
      await loadTradeHistory();
      setShowCloseModal(false);
      setPositionToClose(null);
      setExitPrice('');
    } catch (err) {
      console.error('Error closing trade:', err);
    }
  };

  const calculatePnL = (position: OpenPosition) => {
    const currentPrice = livePrices[position.symbol];
    if (!currentPrice) return null;

    const entry = position.entry_price;
    const leverage = position.leverage;
    const size = position.size_usdt;

    let pnlPct: number;
    if (position.direction === 'long') {
      pnlPct = ((currentPrice - entry) / entry) * 100;
    } else {
      pnlPct = ((entry - currentPrice) / entry) * 100;
    }

    const pnl = (pnlPct / 100) * size * leverage;

    const liquidationPrice =
      position.direction === 'long'
        ? entry * (1 - 1 / leverage + 0.004)
        : entry * (1 + 1 / leverage - 0.004);

    const distanceToLiq = Math.abs((currentPrice - liquidationPrice) / currentPrice) * 100;

    return {
      pnl: pnl.toFixed(2),
      pnlPct: (pnlPct * leverage).toFixed(2),
      liquidationPrice: liquidationPrice.toFixed(2),
      nearLiquidation: distanceToLiq < 15,
    };
  };

  const getTimeHeld = (openedAt: string) => {
    const opened = new Date(openedAt);
    const now = new Date();
    const diff = now.getTime() - opened.getTime();
    const hours = Math.floor(diff / (1000 * 60 * 60));
    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
    return `${hours}h ${minutes}m`;
  };

  return (
    <div className="flex h-screen bg-black text-white">
      <Sidebar />

      <div className="flex-1 p-6 overflow-y-auto">
        <div className="max-w-7xl mx-auto space-y-6">
          <div className="bg-gradient-to-r from-green-900/30 via-blue-900/20 to-green-900/30 rounded-2xl p-8 border border-green-800/30">
            <h1 className="text-4xl font-bold text-white mb-2">My Trades</h1>
            <p className="text-lg text-gray-300">Track and manage your live positions</p>
          </div>

          <div className="bg-gray-900 rounded-xl p-6 border border-gray-800">
            <h2 className="text-lg font-bold text-white mb-4">Open New Position</h2>
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm text-gray-400 mb-2">Symbol</label>
                <select
                  value={newPosition.symbol}
                  onChange={(e) => setNewPosition({ ...newPosition, symbol: e.target.value })}
                  className="w-full bg-gray-800 text-white border border-gray-700 rounded-lg px-4 py-3 focus:outline-none focus:border-blue-500"
                >
                  {CRYPTO_SYMBOLS.map((sym) => (
                    <option key={sym} value={sym}>
                      {sym}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm text-gray-400 mb-2">Direction</label>
                <div className="flex gap-2">
                  <button
                    onClick={() => setNewPosition({ ...newPosition, direction: 'long' })}
                    className={`flex-1 px-4 py-3 rounded-lg font-bold transition-all ${
                      newPosition.direction === 'long'
                        ? 'bg-green-600 text-white'
                        : 'bg-gray-800 text-gray-400 border border-gray-700'
                    }`}
                  >
                    LONG
                  </button>
                  <button
                    onClick={() => setNewPosition({ ...newPosition, direction: 'short' })}
                    className={`flex-1 px-4 py-3 rounded-lg font-bold transition-all ${
                      newPosition.direction === 'short'
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
                  value={newPosition.entryPrice}
                  onChange={(e) => setNewPosition({ ...newPosition, entryPrice: e.target.value })}
                  className="w-full bg-gray-800 text-white border border-gray-700 rounded-lg px-4 py-3 focus:outline-none focus:border-blue-500"
                  placeholder="0.00"
                />
              </div>

              <div>
                <label className="block text-sm text-gray-400 mb-2">Leverage (1-125x)</label>
                <input
                  type="number"
                  value={newPosition.leverage}
                  onChange={(e) => setNewPosition({ ...newPosition, leverage: e.target.value })}
                  className="w-full bg-gray-800 text-white border border-gray-700 rounded-lg px-4 py-3 focus:outline-none focus:border-blue-500"
                  placeholder="10"
                  min="1"
                  max="125"
                />
              </div>

              <div>
                <label className="block text-sm text-gray-400 mb-2">Position Size (USDT)</label>
                <input
                  type="number"
                  value={newPosition.sizeUsdt}
                  onChange={(e) => setNewPosition({ ...newPosition, sizeUsdt: e.target.value })}
                  className="w-full bg-gray-800 text-white border border-gray-700 rounded-lg px-4 py-3 focus:outline-none focus:border-blue-500"
                  placeholder="100"
                />
              </div>

              <div>
                <label className="block text-sm text-gray-400 mb-2">Notes (optional)</label>
                <input
                  type="text"
                  value={newPosition.notes}
                  onChange={(e) => setNewPosition({ ...newPosition, notes: e.target.value })}
                  className="w-full bg-gray-800 text-white border border-gray-700 rounded-lg px-4 py-3 focus:outline-none focus:border-blue-500"
                  placeholder="Trade notes..."
                />
              </div>
            </div>

            <button
              onClick={handleOpenPosition}
              disabled={!newPosition.entryPrice || !newPosition.leverage || !newPosition.sizeUsdt}
              className="mt-4 w-full px-6 py-3 bg-green-600 hover:bg-green-700 disabled:bg-gray-700 disabled:cursor-not-allowed text-white font-bold rounded-lg transition-all"
            >
              Open Position
            </button>
          </div>

          <div className="bg-gray-900 rounded-xl p-6 border border-gray-800">
            <h2 className="text-lg font-bold text-white mb-4">Open Positions ({openPositions.length})</h2>
            {openPositions.length === 0 ? (
              <p className="text-gray-400 text-center py-8">No open positions</p>
            ) : (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {openPositions.map((position) => {
                  const pnlData = calculatePnL(position);
                  const currentPrice = livePrices[position.symbol];

                  const positionSize = position.size_usdt * position.leverage;
                  const collateral = position.size_usdt;

                  return (
                    <div
                      key={position.id}
                      className={`bg-gray-800 rounded-lg p-4 border ${
                        pnlData?.nearLiquidation ? 'border-red-500' : 'border-gray-700'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-2">
                          <span className="text-lg font-bold">{position.symbol}</span>
                          <span
                            className={`px-2 py-1 rounded text-xs font-bold ${
                              position.direction === 'long' ? 'bg-green-600' : 'bg-red-600'
                            }`}
                          >
                            {position.direction.toUpperCase()}
                          </span>
                          <span className="px-2 py-1 rounded text-xs font-bold bg-gray-700">
                            {position.leverage}x
                          </span>
                        </div>
                        <button
                          onClick={() => handleDeletePositionClick(position)}
                          className="text-gray-400 hover:text-red-400 transition-colors text-lg"
                          title="Delete position"
                        >
                          ✕
                        </button>
                      </div>

                      <div className="space-y-2">
                        <div className="flex items-center justify-between text-sm">
                          <span className="text-gray-400">Entry:</span>
                          <span className="font-semibold">${position.entry_price.toFixed(2)}</span>
                        </div>
                        <div className="flex items-center justify-between text-sm">
                          <span className="text-gray-400">Current:</span>
                          <span className="font-semibold">
                            {currentPrice ? `$${currentPrice.toFixed(2)}` : 'Loading...'}
                          </span>
                        </div>
                        <div className="flex items-center justify-between text-sm">
                          <span className="text-gray-400">Collateral:</span>
                          <span className="font-semibold">${collateral.toFixed(2)}</span>
                        </div>
                        <div className="flex items-center justify-between text-sm">
                          <span className="text-gray-400">Position Size:</span>
                          <span className="font-semibold">${positionSize.toFixed(2)}</span>
                        </div>
                        {pnlData && (
                          <>
                            <div className="flex items-center justify-between text-sm">
                              <span className="text-gray-400">Liq Price:</span>
                              <span
                                className={`font-bold flex items-center gap-1 ${
                                  pnlData.nearLiquidation ? 'text-red-400' : 'text-gray-300'
                                }`}
                              >
                                ${pnlData.liquidationPrice}
                                {pnlData.nearLiquidation && <span>⚠️</span>}
                              </span>
                            </div>
                            <div className="flex items-center justify-between text-sm pt-2 border-t border-gray-700">
                              <span className="text-gray-400">PnL:</span>
                              <span
                                className={`font-bold flex items-center gap-1 ${
                                  parseFloat(pnlData.pnl) >= 0 ? 'text-green-400' : 'text-red-400'
                                }`}
                              >
                                {parseFloat(pnlData.pnl) >= 0 ? '+' : ''}${pnlData.pnl} ({parseFloat(pnlData.pnlPct) >= 0 ? '+' : ''}{pnlData.pnlPct}%)
                                {parseFloat(pnlData.pnl) >= 0 ? ' ✓' : ''}
                              </span>
                            </div>
                          </>
                        )}
                      </div>

                      <div className="flex items-center justify-between pt-3 mt-3 border-t border-gray-700">
                        <span className="text-xs text-gray-400">Held: {getTimeHeld(position.opened_at)}</span>
                        <button
                          onClick={() => handleClosePositionClick(position)}
                          className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white text-sm font-bold rounded transition-all"
                        >
                          Close
                        </button>
                      </div>

                      {position.notes && (
                        <p className="text-xs text-gray-500 mt-2 italic">{position.notes}</p>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {tradeHistory && (
            <>
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="bg-gray-900 rounded-xl p-6 border border-gray-800">
                  <p className="text-sm text-gray-400 mb-1">Total PnL</p>
                  <p
                    className={`text-3xl font-bold ${
                      tradeHistory.summary.total_pnl >= 0 ? 'text-green-400' : 'text-red-400'
                    }`}
                  >
                    ${tradeHistory.summary.total_pnl.toFixed(2)}
                  </p>
                </div>

                <div className="bg-gray-900 rounded-xl p-6 border border-gray-800">
                  <p className="text-sm text-gray-400 mb-1">Win Rate</p>
                  <p className="text-3xl font-bold text-white">{tradeHistory.summary.win_rate.toFixed(1)}%</p>
                </div>

                <div className="bg-gray-900 rounded-xl p-6 border border-gray-800">
                  <p className="text-sm text-gray-400 mb-1">Best Trade</p>
                  <p className="text-3xl font-bold text-green-400">
                    {tradeHistory.summary.best_trade
                      ? `$${tradeHistory.summary.best_trade.pnl.toFixed(2)}`
                      : '-'}
                  </p>
                </div>

                <div className="bg-gray-900 rounded-xl p-6 border border-gray-800">
                  <p className="text-sm text-gray-400 mb-1">Worst Trade</p>
                  <p className="text-3xl font-bold text-red-400">
                    {tradeHistory.summary.worst_trade
                      ? `$${tradeHistory.summary.worst_trade.pnl.toFixed(2)}`
                      : '-'}
                  </p>
                </div>
              </div>

              <div className="bg-gray-900 rounded-xl p-6 border border-gray-800">
                <h2 className="text-lg font-bold text-white mb-4">
                  Trade History ({tradeHistory.summary.total_trades})
                </h2>
                {tradeHistory.trades.length === 0 ? (
                  <p className="text-gray-400 text-center py-8">No closed trades yet</p>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-gray-800">
                          <th className="text-left py-3 text-gray-400 font-semibold">Symbol</th>
                          <th className="text-left py-3 text-gray-400 font-semibold">Dir</th>
                          <th className="text-right py-3 text-gray-400 font-semibold">Entry</th>
                          <th className="text-right py-3 text-gray-400 font-semibold">Exit</th>
                          <th className="text-right py-3 text-gray-400 font-semibold">PnL $</th>
                          <th className="text-right py-3 text-gray-400 font-semibold">PnL %</th>
                          <th className="text-right py-3 text-gray-400 font-semibold">Lev</th>
                          <th className="text-right py-3 text-gray-400 font-semibold">Date</th>
                        </tr>
                      </thead>
                      <tbody>
                        {tradeHistory.trades.map((trade) => (
                          <tr
                            key={trade.id}
                            className={`border-b border-gray-800 ${
                              trade.pnl >= 0 ? 'bg-green-900/10' : 'bg-red-900/10'
                            }`}
                          >
                            <td className="py-3 font-semibold">{trade.symbol}</td>
                            <td className="py-3">
                              <span
                                className={`px-2 py-1 rounded text-xs font-bold ${
                                  trade.direction === 'long' ? 'bg-green-600' : 'bg-red-600'
                                }`}
                              >
                                {trade.direction.toUpperCase()}
                              </span>
                            </td>
                            <td className="text-right py-3 text-gray-300">${trade.entry_price.toFixed(2)}</td>
                            <td className="text-right py-3 text-gray-300">${trade.exit_price.toFixed(2)}</td>
                            <td
                              className={`text-right py-3 font-bold ${
                                trade.pnl >= 0 ? 'text-green-400' : 'text-red-400'
                              }`}
                            >
                              ${trade.pnl.toFixed(2)}
                            </td>
                            <td
                              className={`text-right py-3 font-bold ${
                                trade.pnl_pct >= 0 ? 'text-green-400' : 'text-red-400'
                              }`}
                            >
                              {trade.pnl_pct >= 0 ? '+' : ''}
                              {trade.pnl_pct.toFixed(2)}%
                            </td>
                            <td className="text-right py-3 text-gray-400">{trade.leverage}x</td>
                            <td className="text-right py-3 text-gray-400">
                              {new Date(trade.closed_at).toLocaleDateString()}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </div>

      {showCloseModal && positionToClose && (
        <div
          className="fixed inset-0 bg-black/80 flex items-center justify-center z-50"
          onClick={() => setShowCloseModal(false)}
        >
          <div
            className="bg-gray-900 rounded-xl p-8 border border-gray-800 max-w-md w-full mx-4"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="text-2xl font-bold text-white mb-4">Close Position</h2>
            <div className="space-y-4 mb-6">
              <div>
                <p className="text-sm text-gray-400">Symbol</p>
                <p className="text-lg font-bold">{positionToClose.symbol}</p>
              </div>
              <div>
                <p className="text-sm text-gray-400">Direction</p>
                <span
                  className={`px-3 py-1 rounded text-sm font-bold ${
                    positionToClose.direction === 'long' ? 'bg-green-600' : 'bg-red-600'
                  }`}
                >
                  {positionToClose.direction.toUpperCase()}
                </span>
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-2">Exit Price</label>
                <input
                  type="number"
                  value={exitPrice}
                  onChange={(e) => setExitPrice(e.target.value)}
                  className="w-full bg-gray-800 text-white border border-gray-700 rounded-lg px-4 py-3 focus:outline-none focus:border-blue-500"
                  placeholder="0.00"
                />
              </div>
            </div>
            <div className="flex gap-3">
              <button
                onClick={() => setShowCloseModal(false)}
                className="flex-1 px-6 py-3 bg-gray-800 hover:bg-gray-700 text-white font-bold rounded-lg transition-all"
              >
                Cancel
              </button>
              <button
                onClick={handleClosePositionConfirm}
                className="flex-1 px-6 py-3 bg-red-600 hover:bg-red-700 text-white font-bold rounded-lg transition-all"
              >
                Close Position
              </button>
            </div>
          </div>
        </div>
      )}

      {showDeleteModal && positionToDelete && (
        <div
          className="fixed inset-0 bg-black/80 flex items-center justify-center z-50"
          onClick={() => setShowDeleteModal(false)}
        >
          <div
            className="bg-gray-900 rounded-xl p-8 border border-gray-800 max-w-md w-full mx-4"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="text-2xl font-bold text-white mb-4">Delete Position</h2>
            <p className="text-gray-300 mb-6">
              Delete this position? This won't be saved to history.
            </p>
            <div className="space-y-3 mb-6">
              <div>
                <p className="text-sm text-gray-400">Symbol</p>
                <p className="text-lg font-bold">{positionToDelete.symbol}</p>
              </div>
              <div>
                <p className="text-sm text-gray-400">Direction</p>
                <span
                  className={`px-3 py-1 rounded text-sm font-bold ${
                    positionToDelete.direction === 'long' ? 'bg-green-600' : 'bg-red-600'
                  }`}
                >
                  {positionToDelete.direction.toUpperCase()}
                </span>
              </div>
            </div>
            <div className="flex gap-3">
              <button
                onClick={() => setShowDeleteModal(false)}
                className="flex-1 px-6 py-3 bg-gray-800 hover:bg-gray-700 text-white font-bold rounded-lg transition-all"
              >
                Cancel
              </button>
              <button
                onClick={handleDeletePositionConfirm}
                className="flex-1 px-6 py-3 bg-red-600 hover:bg-red-700 text-white font-bold rounded-lg transition-all"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
