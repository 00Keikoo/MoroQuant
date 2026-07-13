interface DirectionBadgeProps {
  direction: 'LONG' | 'SHORT' | 'BUY' | 'SELL';
  className?: string;
}

export function DirectionBadge({ direction, className = '' }: DirectionBadgeProps) {
  const isPositive = direction === 'LONG' || direction === 'BUY';

  return (
    <span className={`font-mono-label text-mono-label px-2 py-1 ${
      isPositive ? 'bg-primary/20 text-primary' : 'bg-error/20 text-error'
    } ${className}`}>
      {direction}
    </span>
  );
}
