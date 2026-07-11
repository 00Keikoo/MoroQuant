import React from 'react';

interface MQCardProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
}

export function MQCard({ children, className = '', ...props }: MQCardProps) {
  return (
    <div
      className={`bg-[var(--color-mq-bg-secondary)] border border-[var(--color-mq-border)] rounded-[var(--radius-minimal)] p-[var(--panel-padding)] ${className}`}
      {...props}
    >
      {children}
    </div>
  );
}
