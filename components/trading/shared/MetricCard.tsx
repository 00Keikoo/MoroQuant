interface MetricCardProps {
  label: string;
  value: string | number;
  valueColor?: 'primary' | 'error' | 'on-surface' | 'tertiary';
  className?: string;
}

export function MetricCard({ label, value, valueColor = 'on-surface', className = '' }: MetricCardProps) {
  const colorClasses = {
    'primary': 'text-primary',
    'error': 'text-error',
    'on-surface': 'text-on-surface',
    'tertiary': 'text-tertiary'
  };

  return (
    <div className={`p-4 ${className}`}>
      <span className="font-mono-label text-mono-label text-on-surface-variant">{label}</span>
      <p className={`font-mono-data text-xl mt-1 ${colorClasses[valueColor]}`}>{value}</p>
    </div>
  );
}
