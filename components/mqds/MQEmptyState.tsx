import React from 'react';

interface MQEmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
}

export function MQEmptyState({ icon, title, description, action, className = '' }: MQEmptyStateProps) {
  return (
    <div className={`flex flex-col items-center justify-center p-8 text-center ${className}`}>
      {icon && (
        <div className="text-[var(--color-mq-text-muted)] mb-4">
          {icon}
        </div>
      )}
      <h3 className="text-[var(--font-size-header)] font-medium text-[var(--color-mq-text-primary)] mb-2">
        {title}
      </h3>
      {description && (
        <p className="text-[var(--font-size-body)] text-[var(--color-mq-text-secondary)] mb-4 max-w-md">
          {description}
        </p>
      )}
      {action && (
        <div className="mt-2">
          {action}
        </div>
      )}
    </div>
  );
}
