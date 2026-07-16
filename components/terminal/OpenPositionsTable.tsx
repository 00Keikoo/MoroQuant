'use client';

import { useQuery } from '@tanstack/react-query';
import { getPositions } from '@/lib/services/terminalService';
import { useTradingMode } from '@/lib/hooks/useTradingMode';

export default function OpenPositionsTable() {
  const { mode } = useTradingMode();

  const { data: positions, isLoading } = useQuery({
    queryKey: ['terminal-positions', mode],
    queryFn: () => getPositions(mode || 'OFF'),
    enabled: mode !== null && mode !== 'OFF',
    refetchInterval: 1000,
  });

  const formatCurrency = (value: number) => {
    return `$${value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const formatPercent = (value: number) => {
    const sign = value >= 0 ? '+' : '';
    return `${sign}${value.toFixed(2)}%`;
  };

  const formatDuration = (hours: number) => {
    if (hours < 1) return `${Math.round(hours * 60)}m`;
    if (hours < 24) return `${hours.toFixed(1)}h`;
    return `${(hours / 24).toFixed(1)}d`;
  };

  if (isLoading) {
    return (
      <div className="bg-[#141414] border border-[#262626] rounded-sm p-4">
        <div className="text-xs font-bold text-[#666666] tracking-wider mb-3">OPEN POSITIONS</div>
        <div className="text-[#666666] text-xs">Loading...</div>
      </div>
    );
  }

  if (!positions || positions.length === 0) {
    return (
      <div className="bg-[#141414] border border-[#262626] rounded-sm p-4">
        <div className="text-xs font-bold text-[#666666] tracking-wider mb-3">OPEN POSITIONS</div>
        <div className="text-[#666666] text-xs">No open positions</div>
      </div>
    );
  }

  return (
    <div className="bg-[#141414] border border-[#262626] rounded-sm p-4">
      <div className="flex justify-between items-center mb-3">
        <div className="text-xs font-bold text-[#666666] tracking-wider">OPEN POSITIONS</div>
        <div className="text-xs text-[#666666] font-mono">{positions.length} position{positions.length !== 1 ? 's' : ''}</div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-xs font-mono">
          <thead>
            <tr className="bg-[#141414] border-b border-[#262626]">
              <th className="text-left text-[#666666] font-bold tracking-wider py-2 px-2">SYMBOL</th>
              <th className="text-left text-[#666666] font-bold tracking-wider py-2 px-2">SIDE</th>
              <th className="text-right text-[#666666] font-bold tracking-wider py-2 px-2">QTY</th>
              <th className="text-right text-[#666666] font-bold tracking-wider py-2 px-2">ENTRY</th>
              <th className="text-right text-[#666666] font-bold tracking-wider py-2 px-2">MARK</th>
              <th className="text-right text-[#666666] font-bold tracking-wider py-2 px-2">MARGIN</th>
              <th className="text-right text-[#666666] font-bold tracking-wider py-2 px-2">PNL</th>
              <th className="text-right text-[#666666] font-bold tracking-wider py-2 px-2">ROI%</th>
              <th className="text-right text-[#666666] font-bold tracking-wider py-2 px-2">CONF</th>
              <th className="text-right text-[#666666] font-bold tracking-wider py-2 px-2">SL</th>
              <th className="text-right text-[#666666] font-bold tracking-wider py-2 px-2">TP</th>
              <th className="text-right text-[#666666] font-bold tracking-wider py-2 px-2">R:R</th>
              <th className="text-right text-[#666666] font-bold tracking-wider py-2 px-2">DURATION</th>
            </tr>
          </thead>
          <tbody>
            {positions.map((position, idx) => {
              const roiPct = position.entry_price !== 0
                ? ((position.mark_price - position.entry_price) / position.entry_price) * 100 * (position.side === 'LONG' ? 1 : -1)
                : 0;

              const riskReward = (() => {
                if (!position.stop_loss || !position.take_profit) return null;
                const risk = Math.abs(position.entry_price - position.stop_loss);
                const reward = Math.abs(position.take_profit - position.entry_price);
                return risk > 0 ? reward / risk : null;
              })();

              return (
                <tr
                  key={idx}
                  className="border-b border-[#262626] hover:bg-[#1C1C1C] transition-colors"
                >
                  <td className="py-2 px-2 text-white font-bold">{position.symbol}</td>
                  <td className="py-2 px-2">
                    <span className={`${position.side === 'LONG' ? 'text-green-500' : 'text-red-500'}`}>
                      {position.side}
                    </span>
                  </td>
                  <td className="py-2 px-2 text-right text-[#A1A1A1]">{position.quantity.toFixed(3)}</td>
                  <td className="py-2 px-2 text-right text-[#A1A1A1]">${position.entry_price.toFixed(2)}</td>
                  <td className="py-2 px-2 text-right text-white">${position.mark_price.toFixed(2)}</td>
                  <td className="py-2 px-2 text-right text-[#A1A1A1]">
                    {position.margin !== null ? formatCurrency(position.margin) : '-'}
                  </td>
                  <td className={`py-2 px-2 text-right font-bold ${position.unrealized_pnl >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                    {formatCurrency(position.unrealized_pnl)}
                  </td>
                  <td className={`py-2 px-2 text-right font-bold ${roiPct >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                    {formatPercent(roiPct)}
                  </td>
                  <td className="py-2 px-2 text-right text-[#A1A1A1]">
                    {position.confidence ? `${(position.confidence * 100).toFixed(0)}%` : '-'}
                  </td>
                  <td className="py-2 px-2 text-right text-[#A1A1A1]">
                    {position.stop_loss !== null ? `$${position.stop_loss.toFixed(2)}` : '-'}
                  </td>
                  <td className="py-2 px-2 text-right text-[#A1A1A1]">
                    {position.take_profit !== null ? `$${position.take_profit.toFixed(2)}` : '-'}
                  </td>
                  <td className="py-2 px-2 text-right text-[#A1A1A1]">
                    {riskReward !== null ? `1:${riskReward.toFixed(2)}` : '-'}
                  </td>
                  <td className="py-2 px-2 text-right text-[#A1A1A1]">
                    {position.duration_hours ? formatDuration(position.duration_hours) : '-'}
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
