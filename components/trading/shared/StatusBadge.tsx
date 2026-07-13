interface StatusBadgeProps {
  status: string;
  variant?: 'success' | 'warning' | 'error' | 'neutral';
  className?: string;
}

export function StatusBadge({ status, variant = 'neutral', className = '' }: StatusBadgeProps) {
  const variantClasses = {
    'success': 'bg-primary/20 text-primary',
    'warning': 'bg-tertiary-container/20 text-tertiary',
    'error': 'bg-error/20 text-error',
    'neutral': 'bg-on-surface-variant/20 text-on-surface-variant'
  };

  return (
    <span className={`font-mono-label text-mono-label px-2 py-1 ${variantClasses[variant]} ${className}`}>
      {status}
    </span>
  );
}
