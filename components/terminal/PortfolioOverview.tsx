'use client';

import { useQuery } from '@tanstack/react-query';
import { getAccount } from '@/lib/services/terminalService';
import { useTradingMode } from '@/lib/hooks/useTradingMode';

export default function PortfolioOverview() {
  const { mode } = useTradingMode();

  const { data: account, isLoading } = useQuery({
    queryKey: ['terminal-account', mode],
    queryFn: () => getAccount(mode || 'OFF'),
    enabled: mode !== null && mode !== 'OFF',
    refetchInterval: 2000,
  });

  const marginUsed = account?.margin_used || 0;
  const freeMargin = account?.free_margin || 0;
  const totalExposure = account?.exposure || 0;
  const accountHealth = account?.equity ? Math.min(100, (freeMargin / account.equity) * 100) : 0;

  const formatCurrency = (value: number) => {
    return `$${value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const formatPnL = (value: number) => {
    const sign = value >= 0 ? '+' : '';
    return `${sign}${formatCurrency(value)}`;
  };

  if (isLoading) {
    return (
      <div className="bg-[#141414] border border-[#262626] rounded-sm p-4">
        <div className="text-xs font-bold text-[#666666] tracking-wider mb-3">PORTFOLIO OVERVIEW</div>
        <div className="text-[#666666] text-xs">Loading...</div>
      </div>
    );
  }

  return (
    <div className="bg-[#141414] border border-[#262626] rounded-sm p-4">
      <div className="text-xs font-bold text-[#666666] tracking-wider mb-3">PORTFOLIO OVERVIEW</div>

      <div className="space-y-2.5">
        <div className="flex justify-between items-center">
          <span className="text-xs text-[#666666]">Current Equity</span>
          <span className="text-sm font-mono font-bold text-white">{formatCurrency(account?.equity || 0)}</span>
        </div>

        <div className="flex justify-between items-center">
          <span className="text-xs text-[#666666]">Daily PnL</span>
          <span className={`text-sm font-mono font-bold ${(account?.daily_pnl || 0) >= 0 ? 'text-green-500' : 'text-red-500'}`}>
            {formatPnL(account?.daily_pnl || 0)}
          </span>
        </div>

        <div className="flex justify-between items-center">
          <span className="text-xs text-[#666666]">Unrealized PnL</span>
          <span className={`text-sm font-mono font-bold ${(account?.unrealized_pnl || 0) >= 0 ? 'text-green-500' : 'text-red-500'}`}>
            {formatPnL(account?.unrealized_pnl || 0)}
          </span>
        </div>

        <div className="flex justify-between items-center">
          <span className="text-xs text-[#666666]">Margin Used</span>
          <span className="text-sm font-mono text-[#A1A1A1]">{formatCurrency(marginUsed)}</span>
        </div>

        <div className="flex justify-between items-center">
          <span className="text-xs text-[#666666]">Free Margin</span>
          <span className="text-sm font-mono text-[#A1A1A1]">{formatCurrency(freeMargin)}</span>
        </div>

        <div className="flex justify-between items-center">
          <span className="text-xs text-[#666666]">Total Exposure</span>
          <span className="text-sm font-mono text-[#A1A1A1]">{formatCurrency(totalExposure)}</span>
        </div>

        <div className="pt-2 border-t border-[#262626]">
          <div className="flex justify-between items-center mb-1">
            <span className="text-xs text-[#666666]">Account Health</span>
            <span className="text-xs font-mono text-white">{accountHealth.toFixed(0)}%</span>
          </div>
          <div className="w-full h-2 bg-[#0e0e0e] rounded-sm overflow-hidden">
            <div
              className={`h-full transition-all ${accountHealth > 70 ? 'bg-green-500' : accountHealth > 40 ? 'bg-yellow-500' : 'bg-red-500'}`}
              style={{ width: `${accountHealth}%` }}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
