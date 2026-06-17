'use client';

import { useState, useEffect } from 'react';
import Sidebar from '@/components/layout/Sidebar';

interface LiveMetrics {
  total_trades: number;
  win_rate: number;
  profit_factor: number | string;
  expectancy: number;
  total_pnl: number;
  sharpe_ratio: number | null;
  max_drawdown: number;
  avg_hold_time_hours: number | null;
}

interface EquityPoint {
  timestamp: number;
  cumulative_pnl: number;
  trade_count: number;
}

interface Position {
  symbol: string;
  side: string;
  entry_price: number;
  mark_price: number;
  unrealized_pnl: number;
  signal?: {
    direction: string;
    confidence: number;
  };
  agreement: string;
}

interface RegimeMetrics {
  regime_label: string;
  total_trades: number;
  win_rate: number;
  profit_factor: number | string;
  expectancy: number;
}

interface ConfidenceMetrics {
  bucket: string;
  total_trades: number;
  win_rate: number;
  expectancy: number;
  total_pnl: number;
}

export default function PerformanceDashboard() {
  const [metrics, setMetrics] = useState<LiveMetrics | null>(null);
  const [equityCurve, setEquityCurve] = useState<EquityPoint[]>([]);
  const [positions, setPositions] = useState<Position[]>([]);
  const [regimes, setRegimes] = useState<Record<string, RegimeMetrics>>({});
  const [confidence, setConfidence] = useState<Record<string, ConfidenceMetrics>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchAllData();
    const interval = setInterval(fetchAllData, 30000);
    return () => clearInterval(interval);
  }, []);

  const fetchAllData = async () => {
    try {
      const [metricsRes, positionsRes, regimesRes, confidenceRes] = await Promise.all([
        fetch('http://localhost:8000/api/analytics/live-performance'),
        fetch('http://localhost:8000/api/positions/open'),
        fetch('http://localhost:8000/api/analytics/regimes'),
        fetch('http://localhost:8000/api/analytics/confidence'),
      ]);

      if (!metricsRes.ok) {
        console.error('Live performance API failed:', metricsRes.status, metricsRes.statusText);
        throw new Error(`API error: ${metricsRes.status} ${metricsRes.statusText}`);
      }
      if (!positionsRes.ok) {
        console.error('Positions API failed:', positionsRes.status, positionsRes.statusText);
        throw new Error(`API error: ${positionsRes.status} ${positionsRes.statusText}`);
      }
      if (!regimesRes.ok) {
        console.error('Regimes API failed:', regimesRes.status, regimesRes.statusText);
        throw new Error(`API error: ${regimesRes.status} ${regimesRes.statusText}`);
      }
      if (!confidenceRes.ok) {
        console.error('Confidence API failed:', confidenceRes.status, confidenceRes.statusText);
        throw new Error(`API error: ${confidenceRes.status} ${confidenceRes.statusText}`);
      }

      const metricsData = await metricsRes.json();
      const positionsData = await positionsRes.json();
      const regimesData = await regimesRes.json();
      const confidenceData = await confidenceRes.json();

      if (metricsData.status === 'success') {
        setMetrics(metricsData.metrics);
        setEquityCurve(metricsData.equity_curve || []);
      } else if (metricsData.status === 'no_data') {
        console.warn('No trade data available yet');
      }

      if (positionsData.positions) {
        setPositions(positionsData.positions);
      }

      if (regimesData.status === 'success') {
        setRegimes(regimesData.regimes);
      }

      if (confidenceData.status === 'success') {
        setConfidence(confidenceData.confidence_buckets);
      }

      setLoading(false);
      setError(null);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch analytics data';
      console.error('Analytics fetch error:', err);
      setError(`Backend error: ${errorMessage}. Ensure ml_service is running on port 8000.`);
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex h-screen bg-black text-white">
        <Sidebar />
        <div className="flex-1 flex items-center justify-center">
          <div className="text-gray-400">Loading analytics...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-screen bg-black text-white">
        <Sidebar />
        <div className="flex-1 flex items-center justify-center">
          <div className="text-red-400">{error}</div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-black text-white">
      <Sidebar />

      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-7xl mx-auto space-y-6">
          <div className="flex items-center justify-between">
            <h1 className="text-2xl font-bold">Live Trading Performance</h1>
            <button
              onClick={fetchAllData}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded text-sm"
            >
              Refresh
            </button>
          </div>

          {metrics && (
            <>
              <div className="grid grid-cols-4 gap-4">
                <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
                  <div className="text-gray-400 text-sm">Win Rate</div>
                  <div className="text-2xl font-bold mt-1">{metrics.win_rate}%</div>
                </div>
                <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
                  <div className="text-gray-400 text-sm">Profit Factor</div>
                  <div className="text-2xl font-bold mt-1">{metrics.profit_factor}</div>
                </div>
                <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
                  <div className="text-gray-400 text-sm">Expectancy</div>
                  <div className={`text-2xl font-bold mt-1 ${metrics.expectancy >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    ${metrics.expectancy}
                  </div>
                </div>
                <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
                  <div className="text-gray-400 text-sm">Sharpe Ratio</div>
                  <div className="text-2xl font-bold mt-1">
                    {metrics.sharpe_ratio !== null ? metrics.sharpe_ratio.toFixed(2) : 'N/A'}
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-4 gap-4">
                <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
                  <div className="text-gray-400 text-sm">Total Trades</div>
                  <div className="text-2xl font-bold mt-1">{metrics.total_trades}</div>
                </div>
                <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
                  <div className="text-gray-400 text-sm">Total PnL</div>
                  <div className={`text-2xl font-bold mt-1 ${metrics.total_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    ${metrics.total_pnl}
                  </div>
                </div>
                <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
                  <div className="text-gray-400 text-sm">Max Drawdown</div>
                  <div className="text-2xl font-bold mt-1 text-red-400">${metrics.max_drawdown}</div>
                </div>
                <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
                  <div className="text-gray-400 text-sm">Avg Hold Time</div>
                  <div className="text-2xl font-bold mt-1">
                    {metrics.avg_hold_time_hours !== null ? `${metrics.avg_hold_time_hours}h` : 'N/A'}
                  </div>
                </div>
              </div>
            </>
          )}

          {equityCurve.length > 0 && (
            <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
              <h2 className="text-lg font-bold mb-4">Equity Curve</h2>
              <div className="h-64 flex items-end space-x-1">
                {equityCurve.map((point, idx) => {
                  const maxPnl = Math.max(...equityCurve.map(p => p.cumulative_pnl));
                  const minPnl = Math.min(...equityCurve.map(p => p.cumulative_pnl));
                  const range = maxPnl - minPnl || 1;
                  const height = ((point.cumulative_pnl - minPnl) / range) * 100;

                  return (
                    <div
                      key={idx}
                      className="flex-1 bg-blue-600 hover:bg-blue-500 transition-colors"
                      style={{ height: `${Math.max(height, 2)}%` }}
                      title={`Trade ${point.trade_count}: $${point.cumulative_pnl}`}
                    />
                  );
                })}
              </div>
            </div>
          )}

          {positions.length > 0 && (
            <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
              <h2 className="text-lg font-bold mb-4">Open Positions ({positions.length})</h2>
              <div className="space-y-2">
                {positions.map((pos, idx) => (
                  <div key={idx} className="flex items-center justify-between p-3 bg-zinc-800 rounded">
                    <div className="flex items-center space-x-4">
                      <div className="font-bold">{pos.symbol}</div>
                      <div className={`px-2 py-1 rounded text-xs ${pos.side === 'long' ? 'bg-green-900 text-green-300' : 'bg-red-900 text-red-300'}`}>
                        {pos.side.toUpperCase()}
                      </div>
                      <div className="text-sm text-gray-400">Entry: ${pos.entry_price}</div>
                      <div className="text-sm text-gray-400">Mark: ${pos.mark_price}</div>
                    </div>
                    <div className="flex items-center space-x-4">
                      <div className={`font-bold ${pos.unrealized_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        ${pos.unrealized_pnl.toFixed(2)}
                      </div>
                      {pos.signal && (
                        <div className={`text-xs px-2 py-1 rounded ${
                          pos.agreement === 'match' ? 'bg-green-900 text-green-300' :
                          pos.agreement === 'conflict' ? 'bg-red-900 text-red-300' :
                          'bg-gray-700 text-gray-300'
                        }`}>
                          Signal: {pos.signal.direction} ({pos.signal.confidence}%)
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {Object.keys(confidence).length > 0 && (
            <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
              <h2 className="text-lg font-bold mb-4">Confidence Analysis</h2>
              <div className="space-y-2">
                {Object.entries(confidence).map(([bucket, data]) => (
                  <div key={bucket} className="flex items-center justify-between p-3 bg-zinc-800 rounded">
                    <div className="flex items-center space-x-4">
                      <div className="font-bold w-24">{data.bucket}</div>
                      <div className="text-sm text-gray-400">Trades: {data.total_trades}</div>
                    </div>
                    <div className="flex items-center space-x-6">
                      <div className="text-sm">Win Rate: <span className="font-bold">{data.win_rate}%</span></div>
                      <div className="text-sm">Expectancy: <span className={`font-bold ${data.expectancy >= 0 ? 'text-green-400' : 'text-red-400'}`}>${data.expectancy}</span></div>
                      <div className="text-sm">PnL: <span className={`font-bold ${data.total_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>${data.total_pnl}</span></div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {Object.keys(regimes).length > 0 && (
            <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
              <h2 className="text-lg font-bold mb-4">Regime Performance</h2>
              <div className="space-y-2">
                {Object.entries(regimes).map(([regime, data]) => (
                  <div key={regime} className="flex items-center justify-between p-3 bg-zinc-800 rounded">
                    <div className="flex items-center space-x-4">
                      <div className="font-bold w-32">{data.regime_label}</div>
                      <div className="text-sm text-gray-400">Trades: {data.total_trades}</div>
                    </div>
                    <div className="flex items-center space-x-6">
                      <div className="text-sm">Win Rate: <span className="font-bold">{data.win_rate}%</span></div>
                      <div className="text-sm">PF: <span className="font-bold">{data.profit_factor}</span></div>
                      <div className="text-sm">Expectancy: <span className={`font-bold ${data.expectancy >= 0 ? 'text-green-400' : 'text-red-400'}`}>${data.expectancy}</span></div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
