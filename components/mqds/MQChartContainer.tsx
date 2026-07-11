import React from 'react';

interface MQChartContainerProps {
  title?: string;
  children: React.ReactNode;
  className?: string;
}

export function MQChartContainer({ title, children, className = '' }: MQChartContainerProps) {
  return (
    <div
      className={`bg-[var(--color-mq-bg-secondary)] border border-[var(--color-mq-border)] rounded-[var(--radius-minimal)] ${className}`}
    >
      {title && (
        <div className="h-[var(--header-height)] px-[var(--panel-padding)] border-b border-[var(--color-mq-border)] flex items-center">
          <h4 className="text-[var(--font-size-body)] font-medium text-[var(--color-mq-text-primary)]">
            {title}
          </h4>
        </div>
      )}
      <div className="p-[var(--panel-padding)]">
        {children}
      </div>
    </div>
  );
}
