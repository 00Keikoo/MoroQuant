import React from 'react';

export type StatusType = 'LIVE' | 'PAUSED' | 'DEGRADED' | 'STUB' | 'PENDING' | 'OK';

interface StatusBadgeProps {
  status: StatusType;
}

export default function StatusBadge({ status }: StatusBadgeProps) {
  const normalized = status.toUpperCase() as StatusType;

  const styles: Record<StatusType, string> = {
    LIVE: 'bg-mq-accent-dim/10 text-mq-accent border border-mq-accent/30',
    OK: 'bg-mq-long-dim/10 text-mq-long border border-mq-long/30',
    PAUSED: 'bg-mq-warning-dim/10 text-mq-warning border border-mq-warning/30',
    DEGRADED: 'bg-mq-short-dim/10 text-mq-short border border-mq-short/30',
    STUB: 'bg-neutral-900/50 text-neutral-500 border border-dashed border-neutral-800',
    PENDING: 'bg-mq-warning-dim/10 text-mq-warning border border-mq-warning/30 animate-pulse',
  };

  const labels: Record<StatusType, string> = {
    LIVE: 'LIVE',
    OK: 'OK',
    PAUSED: 'PAUSED',
    DEGRADED: 'DEGRADED',
    STUB: 'PARTIAL',
    PENDING: 'PENDING',
  };

  return (
    <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-bold tracking-wider ${styles[normalized] || styles.STUB}`}>
      {normalized === 'PENDING' && (
        <svg className="animate-spin h-2.5 w-2.5 text-mq-warning" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
        </svg>
      )}
      {normalized === 'LIVE' && (
        <span className="h-1.5 w-1.5 rounded-full bg-mq-accent animate-pulse" />
      )}
      {normalized === 'OK' && (
        <span className="h-1.5 w-1.5 rounded-full bg-mq-long" />
      )}
      {labels[normalized] || normalized}
    </span>
  );
}
