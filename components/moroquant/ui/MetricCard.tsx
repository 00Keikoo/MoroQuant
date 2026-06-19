import React from 'react';
import TrendIndicator from './TrendIndicator';
import StatusBadge from './StatusBadge';

interface MetricCardProps {
  label: string;
  value: string | number;
  delta?: number;
  status?: 'positive' | 'negative' | 'neutral' | 'warning';
  loading?: boolean;
  stub?: boolean;
  trendFormat?: 'percent' | 'dollar' | 'raw';
  trendInverse?: boolean;
}

export default function MetricCard({
  label,
  value,
  delta,
  status = 'neutral',
  loading = false,
  stub = false,
  trendFormat = 'percent',
  trendInverse = false,
}: MetricCardProps) {
  if (loading) {
    return (
      <div className="bg-mq-panel border border-mq-panel-border rounded-lg p-4 animate-pulse">
        <div className="h-4 bg-neutral-800 rounded w-2/3 mb-3" />
        <div className="h-8 bg-neutral-800 rounded w-1/2" />
      </div>
    );
  }

  // Get matching text color for main value depending on status
  const statusColors = {
    positive: 'text-mq-long',
    negative: 'text-mq-short',
    warning: 'text-mq-warning',
    neutral: 'text-white',
  };

  return (
    <div className="bg-mq-panel border border-mq-panel-border hover:border-mq-accent/20 transition-all duration-300 rounded-lg p-4 relative overflow-hidden group">
      {/* Top light glow on hover */}
      <div className="absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-mq-accent/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
      
      <div className="flex justify-between items-start">
        <span className="text-neutral-400 text-xs font-semibold uppercase tracking-wider">{label}</span>
        {stub && <StatusBadge status="STUB" />}
      </div>
      
      <div className="flex items-baseline justify-between mt-2">
        <span className={`text-2xl font-bold tracking-tight ${statusColors[status]}`}>
          {value}
        </span>
        {delta !== undefined && (
          <TrendIndicator value={delta} format={trendFormat} inverse={trendInverse} />
        )}
      </div>
    </div>
  );
}
