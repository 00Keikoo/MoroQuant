import { MetricCard } from '@/components/trading/shared';

interface MetricsBarProps {
  metrics: Array<{
    label: string;
    value: string;
    valueColor?: 'primary' | 'error' | 'on-surface';
  }>;
}

export function MetricsBar({ metrics }: MetricsBarProps) {
  return (
    <div className="grid grid-cols-5 gap-px bg-outline-variant border-b border-outline-variant">
      {metrics.map((metric, idx) => (
        <div key={idx} className="bg-surface">
          <MetricCard
            label={metric.label}
            value={metric.value}
            valueColor={metric.valueColor}
          />
        </div>
      ))}
    </div>
  );
}
