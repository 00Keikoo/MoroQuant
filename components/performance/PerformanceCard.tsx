'use client';

import React from 'react';

export type CardStatus = 'positive' | 'negative' | 'neutral';

interface PerformanceCardProps {
  label: string;
  value: string | number;
  sublabel?: string;
  status?: CardStatus;
  loading?: boolean;
}

const STATUS_COLORS: Record<CardStatus, string> = {
  positive: 'text-mq-long',
  negative: 'text-mq-short',
  neutral: 'text-white',
};

const STATUS_GLOW: Record<CardStatus, string> = {
  positive: 'from-mq-long/10',
  negative: 'from-mq-short/10',
  neutral: 'from-mq-accent/5',
};

/**
 * Glassmorphism KPI card for performance metrics.
 * - Green for positive values (profit, expectancy > 0)
 * - Red for negative values (loss, drawdown)
 * - White for neutral values (count, ratio)
 */
export default function PerformanceCard({
  label,
  value,
  sublabel,
  status = 'neutral',
  loading = false,
}: PerformanceCardProps) {
  if (loading) {
    return (
      <div className="glass-card p-5 animate-pulse">
        <div className="h-3 bg-neutral-800 rounded w-2/3 mb-3" />
        <div className="h-7 bg-neutral-800 rounded w-1/2 mb-2" />
        <div className="h-2 bg-neutral-900 rounded w-1/3" />
      </div>
    );
  }

  return (
    <div className="glass-card p-5 relative overflow-hidden group transition-all duration-300 hover:border-mq-accent/30">
      {/* Gradient glow strip on top */}
      <div
        className={`absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r ${STATUS_GLOW[status]} via-transparent to-transparent opacity-60 group-hover:opacity-100 transition-opacity duration-300`}
      />

      <div className="flex items-start justify-between mb-2">
        <span className="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">
          {label}
        </span>
      </div>

      <div className={`text-2xl font-bold tracking-tight ${STATUS_COLORS[status]}`}>
        {value}
      </div>

      {sublabel && (
        <div className="text-[10px] text-neutral-500 font-mono mt-1">{sublabel}</div>
      )}
    </div>
  );
}
