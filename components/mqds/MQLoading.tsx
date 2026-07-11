import React from 'react';

interface MQLoadingProps {
  size?: 'sm' | 'md' | 'lg';
  text?: string;
  className?: string;
}

export function MQLoading({ size = 'md', text, className = '' }: MQLoadingProps) {
  const sizeStyles = {
    sm: 'w-4 h-4 border-2',
    md: 'w-6 h-6 border-2',
    lg: 'w-8 h-8 border-3'
  };

  return (
    <div className={`flex flex-col items-center justify-center gap-3 ${className}`}>
      <div
        className={`${sizeStyles[size]} border-[var(--color-mq-border)] border-t-[var(--color-mq-accent)] rounded-full animate-spin`}
      />
      {text && (
        <p className="text-[var(--font-size-small)] text-[var(--color-mq-text-secondary)]">
          {text}
        </p>
      )}
    </div>
  );
}
