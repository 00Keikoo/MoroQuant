'use client';

import { useEffect, useState } from 'react';
import { Activity } from 'lucide-react';
import { getPaperResearchSummary } from '@/lib/api/ml-trading';

export default function ResearchSummaryCard() {
  const [summary, setSummary] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchSummary = async () => {
      try {
        const data = await getPaperResearchSummary();
        setSummary(data);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load');
      } finally {
        setLoading(false);
      }
    };

    fetchSummary();
    const interval = setInterval(fetchSummary, 30_000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="glass-card p-4 flex items-center justify-center">
        <div className="w-4 h-4 border-2 border-mq-accent/20 border-t-mq-accent rounded-full animate-spin" />
      </div>
    );
  }

  if (error || !summary) {
    return (
      <div className="glass-card p-4">
        <div className="text-xs text-red-400">Failed to load research summary</div>
      </div>
    );
  }

  const metrics = [
    { label: 'Trades', value: summary.trades, format: (v: number) => v.toString() },
    { label: 'Win Rate', value: summary.win_rate, format: (v: number) => `${v.toFixed(1)}%` },
    { label: 'Profit Factor', value: summary.profit_factor, format: (v: number) => v.toFixed(2) },
    { label: 'Sharpe', value: summary.sharpe, format: (v: number | null | undefined) => (v !== null && v !== undefined) ? v.toFixed(2) : 'Calculating...' },
    { label: 'Expectancy', value: summary.expectancy, format: (v: number) => `$${v.toFixed(2)}` },
    { label: 'Avg Hold', value: summary.avg_hold_hours, format: (v: number) => `${v.toFixed(1)}h` },
  ];

  return (
    <div className="glass-card p-4 flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-mq-accent" />
          <h3 className="text-sm font-semibold text-white tracking-wide uppercase">
            Research Health
          </h3>
        </div>
        <span className="text-[10px] text-neutral-500 font-mono">
          {summary.open_positions} open
        </span>
      </div>

      <div className="grid grid-cols-2 gap-3">
        {metrics.map((metric) => (
          <div key={metric.label} className="flex flex-col gap-1">
            <span className="text-[10px] text-neutral-500 uppercase tracking-wider font-semibold">
              {metric.label}
            </span>
            <span className="text-sm font-bold text-white font-mono">
              {metric.format(metric.value)}
            </span>
          </div>
        ))}
      </div>

      <div className="text-[10px] text-neutral-600 pt-2 border-t border-gray-800">
        Last updated: {new Date(summary.last_updated).toLocaleTimeString()}
      </div>
    </div>
  );
}
