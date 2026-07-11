import React from 'react';

interface MQMetricCardProps {
  label: string;
  value: string | number;
  delta?: {
    value: number;
    direction: 'up' | 'down';
  };
  sparkline?: React.ReactNode;
  className?: string;
}

export function MQMetricCard({ label, value, delta, sparkline, className = '' }: MQMetricCardProps) {
  const deltaColor = delta?.direction === 'up'
    ? 'text-[var(--color-mq-success)]'
    : 'text-[var(--color-mq-failure)]';

  return (
    <div
      className={`bg-[var(--color-mq-bg-secondary)] border border-[var(--color-mq-border)] rounded-[var(--radius-minimal)] p-[var(--panel-padding)] ${className}`}
    >
      <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)] mb-1">
        {label}
      </div>
      <div className="flex items-baseline justify-between">
        <div className="text-[20px] font-bold font-mono text-[var(--color-mq-text-primary)]">
          {value}
        </div>
        {delta && (
          <div className={`text-[var(--font-size-small)] font-mono ${deltaColor}`}>
            {delta.direction === 'up' ? '+' : ''}{delta.value}%
          </div>
        )}
      </div>
      {sparkline && (
        <div className="mt-2 h-8 opacity-50">
          {sparkline}
        </div>
      )}
    </div>
  );
}
