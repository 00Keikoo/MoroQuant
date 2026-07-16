'use client';

import { useTradingMode } from '@/lib/hooks/useTradingMode';
import { useQuery } from '@tanstack/react-query';
import { getAccount } from '@/lib/services/terminalService';

export default function InstitutionalHeader() {
  const { mode, isPaper, isLive } = useTradingMode();

  const { data: account } = useQuery({
    queryKey: ['terminal-account', mode],
    queryFn: () => getAccount(mode || 'OFF'),
    enabled: mode !== null && mode !== 'OFF',
    refetchInterval: 2000,
  });

  const formatCurrency = (value: number | undefined) => {
    if (value === undefined) return '-';
    return `$${value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const formatPnL = (value: number) => {
    const sign = value >= 0 ? '+' : '';
    return `${sign}${formatCurrency(value)}`;
  };

  const formatPnLPercent = (value: number, base: number) => {
    if (!base) return '0.00%';
    const pct = (value / base) * 100;
    const sign = pct >= 0 ? '+' : '';
    return `${sign}${pct.toFixed(2)}%`;
  };

  const getModeColor = () => {
    if (isLive) return 'text-red-500';
    if (isPaper) return 'text-green-500';
    return 'text-gray-500';
  };

  const getConnectionStatus = () => {
    if (mode === 'OFF') return { icon: '⭘', text: 'OFFLINE', color: 'text-gray-500' };
    return { icon: '⚡', text: 'CONNECTED', color: 'text-green-500' };
  };

  const connection = getConnectionStatus();

  return (
    <div className="bg-[#141414] border-b border-[#262626] px-4 py-2.5">
      <div className="flex items-center justify-between gap-6 text-xs font-mono">
        {/* Left section: Mode & Account */}
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2">
            <span className="text-[#666666]">MODE:</span>
            <span className={`font-bold ${getModeColor()}`}>{mode}</span>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-[#666666]">EQUITY:</span>
            <span className="text-white font-bold">{formatCurrency(account?.equity)}</span>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-[#666666]">BAL:</span>
            <span className="text-[#A1A1A1]">{formatCurrency(account?.balance)}</span>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-[#666666]">MARGIN:</span>
            <span className="text-[#A1A1A1]">
              {formatCurrency(account?.margin_used || 0)}
            </span>
          </div>
        </div>

        {/* Center section: PnL */}
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2">
            <span className="text-[#666666]">UNREALIZED:</span>
            <span className={(account?.unrealized_pnl || 0) >= 0 ? 'text-green-500' : 'text-red-500'}>
              {formatPnL(account?.unrealized_pnl || 0)} (
              {formatPnLPercent(account?.unrealized_pnl || 0, account?.balance || 1)})
            </span>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-[#666666]">DAILY:</span>
            <span className={(account?.daily_pnl || 0) >= 0 ? 'text-green-500' : 'text-red-500'}>
              {formatPnL(account?.daily_pnl || 0)}
            </span>
          </div>
        </div>

        {/* Right section: Status */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <span className="text-[#666666]">UPDATED:</span>
            <span className="text-[#A1A1A1]">{new Date().toLocaleTimeString('en-US', { hour12: false })}</span>
          </div>

          <div className="flex items-center gap-2">
            <span className={connection.color}>{connection.icon}</span>
            <span className={connection.color}>{connection.text}</span>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-green-500">🔄</span>
            <span className="text-[#A1A1A1]">AUTO-REFRESH</span>
          </div>
        </div>
      </div>
    </div>
  );
}
