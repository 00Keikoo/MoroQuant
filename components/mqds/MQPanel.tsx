import React from 'react';

interface MQPanelProps extends React.HTMLAttributes<HTMLDivElement> {
  title?: string;
  actions?: React.ReactNode;
  children: React.ReactNode;
}

export function MQPanel({ title, actions, children, className = '', ...props }: MQPanelProps) {
  return (
    <div
      className={`bg-[var(--color-mq-bg-secondary)] border border-[var(--color-mq-border)] rounded-[var(--radius-minimal)] ${className}`}
      {...props}
    >
      {title && (
        <div className="flex items-center justify-between h-[var(--header-height)] px-[var(--panel-padding)] border-b border-[var(--color-mq-border)]">
          <h3 className="text-[var(--font-size-body)] font-medium text-[var(--color-mq-text-primary)]">
            {title}
          </h3>
          {actions && (
            <div className="flex items-center gap-1">
              {actions}
            </div>
          )}
        </div>
      )}
      <div className="p-[var(--panel-padding)]">
        {children}
      </div>
    </div>
  );
}
