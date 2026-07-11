'use client';

import React, { useEffect, useRef } from 'react';
import { X } from 'lucide-react';
import { MQIconButton } from './MQIconButton';

interface MQDialogProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
  className?: string;
}

export function MQDialog({ isOpen, onClose, title, children, footer, className = '' }: MQDialogProps) {
  const dialogRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isOpen) return;

    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };

    const handleClickOutside = (e: MouseEvent) => {
      if (dialogRef.current && !dialogRef.current.contains(e.target as Node)) {
        onClose();
      }
    };

    document.addEventListener('keydown', handleEscape);
    document.addEventListener('mousedown', handleClickOutside);

    return () => {
      document.removeEventListener('keydown', handleEscape);
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80">
      <div
        ref={dialogRef}
        className={`bg-[var(--color-mq-bg-secondary)] border border-[var(--color-mq-border)] rounded-[var(--radius-minimal)] shadow-xl max-w-2xl w-full max-h-[80vh] flex flex-col ${className}`}
      >
        <div className="flex items-center justify-between h-[var(--header-height)] px-[var(--panel-padding)] border-b border-[var(--color-mq-border)]">
          <h2 className="text-[var(--font-size-header)] font-medium text-[var(--color-mq-text-primary)]">
            {title}
          </h2>
          <MQIconButton
            icon={<X size={16} />}
            label="Close dialog"
            onClick={onClose}
          />
        </div>
        <div className="flex-1 overflow-auto p-[var(--spacing-4)]">
          {children}
        </div>
        {footer && (
          <div className="px-[var(--spacing-4)] py-[var(--spacing-3)] border-t border-[var(--color-mq-border)] flex justify-end gap-2">
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}
