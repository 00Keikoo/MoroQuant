import React from 'react';

type StatusType = 'success' | 'failure' | 'warning' | 'running' | 'pending';

interface MQStatusBadgeProps {
  status: StatusType;
  label: string;
  className?: string;
}

export function MQStatusBadge({ status, label, className = '' }: MQStatusBadgeProps) {
  const statusStyles = {
    success: 'text-[var(--color-mq-success)] bg-[var(--color-mq-success-dim)]',
    failure: 'text-[var(--color-mq-failure)] bg-[var(--color-mq-failure-dim)]',
    warning: 'text-[var(--color-mq-warning)] bg-[var(--color-mq-warning-dim)]',
    running: 'text-[var(--color-mq-running)] bg-[var(--color-mq-running-dim)]',
    pending: 'text-[var(--color-mq-text-secondary)] bg-[var(--color-mq-bg-primary)]'
  };

  return (
    <span
      className={`inline-flex items-center px-2 h-5 text-[var(--font-size-caption)] font-medium rounded-[var(--radius-minimal)] ${statusStyles[status]} ${className}`}
    >
      {label}
    </span>
  );
}
