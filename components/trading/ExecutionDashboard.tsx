'use client';

import { useState, useEffect } from 'react';
import { Activity, TrendingUp, TrendingDown, Target } from 'lucide-react';
import { getExecutionAnalytics } from '@/lib/api/ml-trading';
import type { ExecutionAnalytics } from '@/lib/types/ml';

export default function ExecutionDashboard() {
  const [analytics, setAnalytics] = useState<ExecutionAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        const response = await getExecutionAnalytics();
        setAnalytics(response.execution);
        setError(null);
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Failed to load execution analytics';
        setError(msg);
      } finally {
        setLoading(false);
      }
    };

    fetchAnalytics();
    const interval = setInterval(fetchAnalytics, 30000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="glass-card p-4 flex items-center justify-center min-h-[200px]">
        <div className="w-6 h-6 border-2 border-mq-accent/20 border-t-mq-accent rounded-full animate-spin" />
      </div>
    );
  }

  if (error || !analytics) {
    return (
      <div className="glass-card p-4">
        <h3 className="text-sm font-semibold text-white tracking-wide uppercase mb-2">
          Execution Quality
        </h3>
        <div className="text-xs text-neutral-500">
          {error || 'No execution data available'}
        </div>
      </div>
    );
  }

  const eqsColor = analytics.avg_eqs >= 70 ? 'text-mq-long' : analytics.avg_eqs >= 50 ? 'text-yellow-400' : 'text-mq-short';

  return (
    <div className="glass-card p-4 flex flex-col gap-4">
      <div className="flex items-center gap-2">
        <Activity className="w-4 h-4 text-mq-accent" />
        <h3 className="text-sm font-semibold text-white tracking-wide uppercase">
          Execution Quality
        </h3>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="flex flex-col gap-1">
          <span className="text-[10px] text-neutral-500 uppercase tracking-wider font-semibold">
            Avg EQS
          </span>
          <span className={`text-lg font-bold font-mono ${eqsColor}`}>
            {analytics.avg_eqs.toFixed(0)}
          </span>
        </div>

        <div className="flex flex-col gap-1">
          <span className="text-[10px] text-neutral-500 uppercase tracking-wider font-semibold">
            Profit Capture
          </span>
          <span className="text-lg font-bold text-white font-mono">
            {analytics.avg_profit_capture.toFixed(1)}%
          </span>
        </div>

        <div className="flex flex-col gap-1">
          <span className="text-[10px] text-neutral-500 uppercase tracking-wider font-semibold flex items-center gap-1">
            <TrendingDown className="w-3 h-3 text-mq-short" />
            Avg MAE
          </span>
          <span className="text-sm font-bold text-mq-short font-mono">
            {analytics.avg_mae.toFixed(2)}%
          </span>
        </div>

        <div className="flex flex-col gap-1">
          <span className="text-[10px] text-neutral-500 uppercase tracking-wider font-semibold flex items-center gap-1">
            <TrendingUp className="w-3 h-3 text-mq-long" />
            Avg MFE
          </span>
          <span className="text-sm font-bold text-mq-long font-mono">
            {analytics.avg_mfe.toFixed(2)}%
          </span>
        </div>

        <div className="flex flex-col gap-1">
          <span className="text-[10px] text-neutral-500 uppercase tracking-wider font-semibold">
            Lost Opportunity
          </span>
          <span className="text-sm font-bold text-yellow-400 font-mono">
            {analytics.avg_lost_opportunity.toFixed(2)}%
          </span>
        </div>

        <div className="flex flex-col gap-1">
          <span className="text-[10px] text-neutral-500 uppercase tracking-wider font-semibold">
            Trailing Activated
          </span>
          <span className="text-sm font-bold text-white font-mono">
            {analytics.trailing_activated}
          </span>
        </div>
      </div>

      {(analytics.trailing_activated > 0 || analytics.break_even_saves > 0) && (
        <div className="flex flex-col gap-2 pt-2 border-t border-neutral-800">
          <span className="text-[10px] text-neutral-500 uppercase tracking-wider font-semibold">
            Trailing Analytics
          </span>
          <div className="grid grid-cols-3 gap-2">
            <div className="flex flex-col gap-1">
              <span className="text-xs text-neutral-400">BE Saves</span>
              <span className="text-sm font-mono text-white">{analytics.break_even_saves}</span>
            </div>
            <div className="flex flex-col gap-1">
              <span className="text-xs text-neutral-400">Avg SL Moves</span>
              <span className="text-sm font-mono text-white">{analytics.avg_sl_moves.toFixed(2)}</span>
            </div>
            <div className="flex flex-col gap-1">
              <span className="text-xs text-neutral-400">Extra Profit</span>
              <span className="text-sm font-mono text-mq-long">${analytics.additional_profit_saved.toFixed(2)}</span>
            </div>
          </div>
        </div>
      )}

      {Object.keys(analytics.exit_reasons).length > 0 && (
        <div className="flex flex-col gap-2 pt-2 border-t border-neutral-800">
          <span className="text-[10px] text-neutral-500 uppercase tracking-wider font-semibold">
            Exit Reasons
          </span>
          <div className="grid grid-cols-2 gap-2">
            {Object.entries(analytics.exit_reasons).map(([reason, count]) => (
              <div key={reason} className="flex justify-between items-center">
                <span className="text-xs text-neutral-400">{reason}</span>
                <span className="text-xs font-mono text-white">{count}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
