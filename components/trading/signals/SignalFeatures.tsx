import { Signal } from '@/lib/mock-data/signals';

interface SignalFeaturesProps {
  signals: Signal[];
}

export function SignalFeatures({ signals }: SignalFeaturesProps) {
  return (
    <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-2">
      {signals.map((signal) => (
        <div key={`features-${signal.id}`} className="bg-surface-container border border-outline-variant p-3">
          <div className="font-label-caps text-label-caps text-on-surface-variant mb-2">{signal.symbol}</div>
          <div className="flex flex-wrap gap-1">
            {signal.features.map((feature, idx) => (
              <span
                key={idx}
                className="px-2 py-1 bg-surface-container-highest text-on-surface font-data-tabular text-[10px] border border-outline-variant"
              >
                {feature}
              </span>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
