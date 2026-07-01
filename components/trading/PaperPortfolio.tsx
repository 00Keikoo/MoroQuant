'use client';

import { useState, useEffect, useCallback } from 'react';
import { RefreshCw, Wallet } from 'lucide-react';
import { getLivePaperAccount } from '@/lib/api/ml-trading';
import type { LivePaperAccount } from '@/lib/types/ml';

const REFRESH_MS = 5_000; // 5 seconds for live updates

export default function PaperPortfolio() {
  const [account, setAccount] = useState<LivePaperAccount | null>(null);
  const [loading, setLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchAccount = useCallback(async (initial = false) => {
    if (initial) setLoading(true);
    else setIsRefreshing(true);
    try {
      const data = await getLivePaperAccount();
      setAccount(data);
      setError(null);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to load paper account';
      setError(msg);
    } finally {
      setLoading(false);
      setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchAccount(true);
    const interval = setInterval(() => fetchAccount(false), REFRESH_MS);
    return () => clearInterval(interval);
  }, [fetchAccount]);

  const fmtUsd = (v: number) =>
    `$${v.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

  if (loading) {
    return (
      <div className="glass-card p-4 flex items-center justify-center min-h-[200px]">
        <div className="w-6 h-6 border-2 border-mq-accent/20 border-t-mq-accent rounded-full animate-spin" />
      </div>
    );
  }

  if (error && !account) {
    return (
      <div className="glass-card p-4">
        <h3 className="text-sm font-semibold text-white tracking-wide uppercase mb-2">
          Paper Account
        </h3>
        <div className="text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">
          {error}
        </div>
      </div>
    );
  }

  const pnlPositive = (account?.unrealized_pnl ?? 0) >= 0;

  return (
    <div className="glass-card p-4 flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Wallet className="w-4 h-4 text-mq-accent" />
          <h3 className="text-sm font-semibold text-white tracking-wide uppercase">
            Paper Account
          </h3>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-neutral-600 font-mono">Live · 5s</span>
          <button
            onClick={() => fetchAccount(false)}
            disabled={isRefreshing}
            className="p-1.5 rounded-lg text-gray-400 hover:text-mq-accent hover:bg-mq-accent/10 transition-colors disabled:opacity-40"
            title="Refresh"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {error && (
        <div className="text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">
          {error}
        </div>
      )}

      {/* Account Metrics */}
      {account && (
        <div className="grid grid-cols-2 gap-3">
          <div className="flex flex-col gap-1">
            <span className="text-[10px] text-neutral-500 uppercase tracking-wider font-semibold">
              Balance
            </span>
            <span className="text-sm font-bold text-white font-mono">
              {fmtUsd(account.balance)}
            </span>
          </div>

          <div className="flex flex-col gap-1">
            <span className="text-[10px] text-neutral-500 uppercase tracking-wider font-semibold">
              Equity
            </span>
            <span className="text-sm font-bold text-white font-mono">
              {fmtUsd(account.equity)}
            </span>
          </div>

          <div className="flex flex-col gap-1">
            <span className="text-[10px] text-neutral-500 uppercase tracking-wider font-semibold">
              Unrealized PnL
            </span>
            <span className={`text-sm font-bold font-mono ${pnlPositive ? 'text-mq-long' : 'text-mq-short'}`}>
              {fmtUsd(account.unrealized_pnl)}
            </span>
          </div>

          <div className="flex flex-col gap-1">
            <span className="text-[10px] text-neutral-500 uppercase tracking-wider font-semibold">
              Available
            </span>
            <span className="text-sm font-bold text-white font-mono">
              {fmtUsd(account.available_balance)}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
