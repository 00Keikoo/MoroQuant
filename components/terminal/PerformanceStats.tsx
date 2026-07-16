'use client';

import { useQuery } from '@tanstack/react-query';
import { getPerformance } from '@/lib/services/terminalService';
import { useTradingMode } from '@/lib/hooks/useTradingMode';

export default function PerformanceStats() {
  const { mode } = useTradingMode();

  const { data: performance, isLoading } = useQuery({
    queryKey: ['terminal-performance', mode],
    queryFn: () => getPerformance(mode || 'OFF'),
    enabled: mode !== null && mode !== 'OFF',
    refetchInterval: 30000,
  });

  if (isLoading) {
    return (
      <div className="bg-[#141414] border border-[#262626] rounded-sm p-4">
        <div className="text-xs font-bold text-[#666666] tracking-wider mb-3">PERFORMANCE METRICS</div>
        <div className="text-[#666666] text-xs">Loading...</div>
      </div>
    );
  }

  const formatPercent = (value: number | null | undefined) => {
    if (value === null || value === undefined) return '-';
    return `${value.toFixed(2)}%`;
  };

  const formatNumber = (value: number | null | undefined, decimals = 2) => {
    if (value === null || value === undefined) return '-';
    return value.toFixed(decimals);
  };

  const formatCurrency = (value: number | null | undefined) => {
    if (value === null || value === undefined) return '-';
    const sign = value >= 0 ? '+' : '';
    return `${sign}$${Math.abs(value).toFixed(2)}`;
  };

  return (
    <div className="bg-[#141414] border border-[#262626] rounded-sm p-4">
      <div className="text-xs font-bold text-[#666666] tracking-wider mb-3">PERFORMANCE METRICS</div>

      <div className="space-y-2.5">
        <div className="flex justify-between items-center">
          <span className="text-xs text-[#666666]">Win Rate</span>
          <span className="text-sm font-mono text-white">{formatPercent(performance?.win_rate)}</span>
        </div>

        <div className="flex justify-between items-center">
          <span className="text-xs text-[#666666]">Profit Factor</span>
          <span className="text-sm font-mono text-white">{formatNumber(performance?.profit_factor)}</span>
        </div>

        <div className="flex justify-between items-center">
          <span className="text-xs text-[#666666]">Expectancy</span>
          <span className="text-sm font-mono text-white">{formatCurrency(performance?.expectancy)}</span>
        </div>

        <div className="flex justify-between items-center">
          <span className="text-xs text-[#666666]">Sharpe Ratio</span>
          <span className="text-sm font-mono text-white">{formatNumber(performance?.sharpe)}</span>
        </div>

        <div className="flex justify-between items-center">
          <span className="text-xs text-[#666666]">Max Drawdown</span>
          <span className="text-sm font-mono text-red-500">{formatCurrency(performance?.max_drawdown)}</span>
        </div>

        <div className="flex justify-between items-center">
          <span className="text-xs text-[#666666]">Total Trades</span>
          <span className="text-sm font-mono text-[#A1A1A1]">{performance?.total_trades || 0}</span>
        </div>

        <div className="flex justify-between items-center">
          <span className="text-xs text-[#666666]">Avg Hold Time</span>
          <span className="text-sm font-mono text-[#A1A1A1]">
            {performance?.avg_hold_hours ? `${performance.avg_hold_hours.toFixed(1)}h` : '-'}
          </span>
        </div>

        <div className="flex justify-between items-center">
          <span className="text-xs text-[#666666]">Total Realized PnL</span>
          <span className={`text-sm font-mono font-bold ${(performance?.total_realized_pnl || 0) >= 0 ? 'text-green-500' : 'text-red-500'}`}>
            {formatCurrency(performance?.total_realized_pnl)}
          </span>
        </div>
      </div>
    </div>
  );
}
