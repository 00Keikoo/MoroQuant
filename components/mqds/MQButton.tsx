import React from 'react';

interface MQButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger';
  size?: 'sm' | 'md' | 'lg';
}

export function MQButton({
  variant = 'primary',
  size = 'md',
  className = '',
  children,
  ...props
}: MQButtonProps) {
  const baseStyles = 'font-medium transition-colors focus-visible:outline focus-visible:outline-1 focus-visible:outline-offset-2 disabled:opacity-50 disabled:cursor-not-allowed';

  const variantStyles = {
    primary: 'bg-[var(--color-mq-accent)] text-white hover:opacity-90 focus-visible:outline-[var(--color-mq-accent)]',
    secondary: 'bg-[var(--color-mq-bg-secondary)] text-[var(--color-mq-text-primary)] border border-[var(--color-mq-border)] hover:border-[var(--color-mq-accent)] focus-visible:outline-[var(--color-mq-accent)]',
    danger: 'bg-[var(--color-mq-failure)] text-white hover:opacity-90 focus-visible:outline-[var(--color-mq-failure)]'
  };

  const sizeStyles = {
    sm: 'h-6 px-2 text-[var(--font-size-small)] rounded-[var(--radius-minimal)]',
    md: 'h-8 px-3 text-[var(--font-size-body)] rounded-[var(--radius-minimal)]',
    lg: 'h-10 px-4 text-[var(--font-size-header)] rounded-[var(--radius-minimal)]'
  };

  return (
    <button
      className={`${baseStyles} ${variantStyles[variant]} ${sizeStyles[size]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}
