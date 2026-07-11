import React from 'react';

interface MQProgressBarProps {
  value: number;
  max?: number;
  className?: string;
  color?: string;
  showLabel?: boolean;
}

export function MQProgressBar({
  value,
  max = 100,
  className = '',
  color = 'var(--color-mq-accent)',
  showLabel = false
}: MQProgressBarProps) {
  const percentage = Math.min(100, Math.max(0, (value / max) * 100));

  return (
    <div className={`w-full ${className}`}>
      <div className="h-1 bg-[var(--color-mq-bg-primary)] rounded-full overflow-hidden">
        <div
          className="h-full transition-all duration-300"
          style={{
            width: `${percentage}%`,
            backgroundColor: color
          }}
        />
      </div>
      {showLabel && (
        <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)] mt-1 font-mono">
          {value} / {max}
        </div>
      )}
    </div>
  );
}
