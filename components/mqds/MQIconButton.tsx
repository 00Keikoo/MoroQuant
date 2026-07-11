import React from 'react';

interface MQIconButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  icon: React.ReactNode;
  label: string;
  size?: 'sm' | 'md' | 'lg';
}

export function MQIconButton({
  icon,
  label,
  size = 'md',
  className = '',
  ...props
}: MQIconButtonProps) {
  const baseStyles = 'inline-flex items-center justify-center text-[var(--color-mq-text-secondary)] hover:text-[var(--color-mq-accent)] hover:bg-[var(--color-mq-accent-dim)] transition-colors focus-visible:outline focus-visible:outline-1 focus-visible:outline-[var(--color-mq-accent)] focus-visible:outline-offset-2 disabled:opacity-50 disabled:cursor-not-allowed rounded-[var(--radius-minimal)]';

  const sizeStyles = {
    sm: 'w-6 h-6',
    md: 'w-8 h-8',
    lg: 'w-10 h-10'
  };

  return (
    <button
      className={`${baseStyles} ${sizeStyles[size]} ${className}`}
      aria-label={label}
      title={label}
      {...props}
    >
      {icon}
    </button>
  );
}
