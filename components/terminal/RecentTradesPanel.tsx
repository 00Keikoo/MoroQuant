'use client';

import { useQuery } from '@tanstack/react-query';
import { getRecentTrades } from '@/lib/services/terminalService';
import { useTradingMode } from '@/lib/hooks/useTradingMode';

export default function RecentTradesPanel() {
  const { mode } = useTradingMode();

  const { data: trades, isLoading } = useQuery({
    queryKey: ['terminal-recent-trades', mode],
    queryFn: () => getRecentTrades(mode || 'OFF', 10),
    enabled: mode !== null && mode !== 'OFF',
    refetchInterval: 5000,
  });

  const formatCurrency = (value: number) => {
    const sign = value >= 0 ? '+' : '';
    return `${sign}$${Math.abs(value).toFixed(2)}`;
  };

  const formatPercent = (value: number) => {
    const sign = value >= 0 ? '+' : '';
    return `${sign}${value.toFixed(2)}%`;
  };

  const formatTime = (timestamp: number) => {
    return new Date(timestamp).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false
    });
  };

  const formatDuration = (minutes: number) => {
    if (minutes < 60) return `${minutes}m`;
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    if (hours < 24) return `${hours}h ${mins}m`;
    const days = Math.floor(hours / 24);
    const remainingHours = hours % 24;
    return `${days}d ${remainingHours}h`;
  };

  if (isLoading) {
    return (
      <div className="bg-[#141414] border border-[#262626] rounded-sm p-4">
        <div className="text-xs font-bold text-[#666666] tracking-wider mb-3">RECENT TRADES</div>
        <div className="text-[#666666] text-xs">Loading...</div>
      </div>
    );
  }

  if (!trades || trades.length === 0) {
    return (
      <div className="bg-[#141414] border border-[#262626] rounded-sm p-4">
        <div className="text-xs font-bold text-[#666666] tracking-wider mb-3">RECENT TRADES</div>
        <div className="text-[#666666] text-xs">No closed trades</div>
      </div>
    );
  }

  return (
    <div className="bg-[#141414] border border-[#262626] rounded-sm p-4">
      <div className="flex justify-between items-center mb-3">
        <div className="text-xs font-bold text-[#666666] tracking-wider">RECENT TRADES</div>
        <div className="text-xs text-[#666666] font-mono">Last {trades.length}</div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-xs font-mono">
          <thead>
            <tr className="bg-[#141414] border-b border-[#262626]">
              <th className="text-left text-[#666666] font-bold tracking-wider py-2 px-2">TIME</th>
              <th className="text-left text-[#666666] font-bold tracking-wider py-2 px-2">SYMBOL</th>
              <th className="text-left text-[#666666] font-bold tracking-wider py-2 px-2">SIDE</th>
              <th className="text-right text-[#666666] font-bold tracking-wider py-2 px-2">ENTRY</th>
              <th className="text-right text-[#666666] font-bold tracking-wider py-2 px-2">EXIT</th>
              <th className="text-right text-[#666666] font-bold tracking-wider py-2 px-2">DURATION</th>
              <th className="text-right text-[#666666] font-bold tracking-wider py-2 px-2">PNL</th>
              <th className="text-right text-[#666666] font-bold tracking-wider py-2 px-2">ROI%</th>
              <th className="text-right text-[#666666] font-bold tracking-wider py-2 px-2">CONF</th>
              <th className="text-center text-[#666666] font-bold tracking-wider py-2 px-2">EXIT REASON</th>
              <th className="text-center text-[#666666] font-bold tracking-wider py-2 px-2">EXEC CLASS</th>
            </tr>
          </thead>
          <tbody>
            {trades.map((trade, idx) => {
              const sizeUsdt = trade.quantity * trade.entry_price;
              const pnlPct = sizeUsdt > 0 ? (trade.net_pnl / sizeUsdt) * 100 : 0;
              return (
                <tr
                  key={idx}
                  className="border-b border-[#262626] hover:bg-[#1C1C1C] transition-colors"
                >
                  <td className="py-2 px-2 text-[#A1A1A1]">{formatTime(trade.exit_time)}</td>
                  <td className="py-2 px-2 text-white font-bold">{trade.symbol}</td>
                  <td className="py-2 px-2">
                    <span className={`${trade.side === 'LONG' ? 'text-green-500' : 'text-red-500'}`}>
                      {trade.side}
                    </span>
                  </td>
                  <td className="py-2 px-2 text-right text-[#A1A1A1]">${trade.entry_price.toFixed(2)}</td>
                  <td className="py-2 px-2 text-right text-white">${trade.exit_price.toFixed(2)}</td>
                  <td className="py-2 px-2 text-right text-[#A1A1A1]">
                    {formatDuration(trade.duration_minutes)}
                  </td>
                  <td className={`py-2 px-2 text-right font-bold ${trade.net_pnl >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                    {formatCurrency(trade.net_pnl)}
                  </td>
                  <td className={`py-2 px-2 text-right font-bold ${pnlPct >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                    {formatPercent(pnlPct)}
                  </td>
                  <td className="py-2 px-2 text-right text-[#A1A1A1]">
                    {trade.confidence ? `${(trade.confidence * 100).toFixed(0)}%` : '-'}
                  </td>
                  <td className="py-2 px-2 text-center">
                    <span className="text-[10px] px-1.5 py-0.5 bg-[#1C1C1C] border border-[#262626] rounded text-[#A1A1A1]">
                      {trade.exit_reason || 'N/A'}
                    </span>
                  </td>
                  <td className="py-2 px-2 text-center">
                    <span className="text-[10px] px-1.5 py-0.5 bg-[#1C1C1C] border border-[#262626] rounded text-[#A1A1A1]">
                      {trade.execution_class || 'N/A'}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
