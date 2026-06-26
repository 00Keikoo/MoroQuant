'use client';

import React from 'react';
import type { LiveMetrics } from '@/lib/services/performanceService';

import { useIsPrivacyMode } from '@/lib/stores/privacyStore';
import { maskOr, MASK_MONETARY, MASK_PERCENT } from '@/lib/format/privacy';

interface StatisticsGridProps {
  metrics: LiveMetrics;
}

interface StatItemProps {
  label: string;
  value: string;
  status: 'positive' | 'negative' | 'neutral';
}

function StatItem({ label, value, status }: StatItemProps) {
  const colorClass =
    status === 'positive'
      ? 'text-mq-long'
      : status === 'negative'
        ? 'text-mq-short'
        : 'text-white';

  return (
    <div className="flex flex-col gap-1 p-4 rounded-lg bg-black/30 border border-mq-panel-border">
      <span className="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">
        {label}
      </span>
      <span className={`text-lg font-bold ${colorClass}`}>{value}</span>
    </div>
  );
}

function fmtUsd(value: number | null | undefined): string {
  if (value === null || value === undefined) return 'N/A';
  const sign = value >= 0 ? '' : '-';
  return `${sign}$${Math.abs(value).toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

function fmtNum(value: number | null | undefined, digits = 2): string {
  if (value === null || value === undefined) return 'N/A';
  return value.toLocaleString(undefined, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

/**
 * Secondary trading statistics grid.
 * Displays gross profit/loss, average win/loss, counts, ROI, drawdown %.
 */
export default function StatisticsGrid({ metrics }: StatisticsGridProps) {
  const privacy = useIsPrivacyMode();
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
      <StatItem
        label="Gross Profit"
        value={maskOr(fmtUsd(metrics.gross_profit), MASK_MONETARY, privacy)}
        status={metrics.gross_profit > 0 ? 'positive' : 'neutral'}
      />
      <StatItem
        label="Gross Loss"
        value={maskOr(fmtUsd(metrics.gross_loss), MASK_MONETARY, privacy)}
        status={metrics.gross_loss < 0 ? 'negative' : 'neutral'}
      />
      <StatItem
        label="Average Win"
        value={maskOr(fmtUsd(metrics.avg_win), MASK_MONETARY, privacy)}
        status={metrics.avg_win > 0 ? 'positive' : 'neutral'}
      />
      <StatItem
        label="Average Loss"
        value={maskOr(fmtUsd(metrics.avg_loss), MASK_MONETARY, privacy)}
        status={metrics.avg_loss < 0 ? 'negative' : 'neutral'}
      />
      <StatItem
        label="Winning Trades"
        value={String(metrics.winning_trades)}
        status="positive"
      />
      <StatItem
        label="Losing Trades"
        value={String(metrics.losing_trades)}
        status="negative"
      />
      <StatItem
        label="ROI"
        value={maskOr(`${fmtNum(metrics.roi)}%`, MASK_PERCENT, privacy)}
        status={metrics.roi >= 0 ? 'positive' : 'negative'}
      />
      <StatItem
        label="Max Drawdown"
        value={maskOr(`${fmtNum(metrics.max_drawdown_pct)}%`, MASK_PERCENT, privacy)}
        status="negative"
      />
    </div>
  );
}
