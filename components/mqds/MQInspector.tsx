import React from 'react';
import { X } from 'lucide-react';
import { MQIconButton } from './MQIconButton';

interface MQInspectorProps {
  title: string;
  onClose?: () => void;
  children: React.ReactNode;
  className?: string;
}

export function MQInspector({ title, onClose, children, className = '' }: MQInspectorProps) {
  return (
    <div
      className={`bg-[var(--color-mq-bg-secondary)] border-l border-[var(--color-mq-border)] flex flex-col ${className}`}
    >
      <div className="flex items-center justify-between h-[var(--header-height)] px-[var(--panel-padding)] border-b border-[var(--color-mq-border)]">
        <h3 className="text-[var(--font-size-body)] font-medium text-[var(--color-mq-text-primary)]">
          {title}
        </h3>
        {onClose && (
          <MQIconButton
            icon={<X size={14} />}
            label="Close inspector"
            size="sm"
            onClick={onClose}
          />
        )}
      </div>
      <div className="flex-1 overflow-auto p-[var(--panel-padding)]">
        {children}
      </div>
    </div>
  );
}
