'use client';

import { useIsPrivacyMode } from '@/lib/stores/privacyStore';

interface PositionDetails {
  instrument: string;
  markPrice: number;
  priceChange: number;
  leverage: string;
  fundingRate: number;
  fundingNextIn: string;
  liquidationPrice: number;
  marginUsed: number;
  marginPercent: number;
}

interface SignalEntry {
  timestamp: string;
  signal: string;
}

interface InspectorPanelProps {
  position: PositionDetails;
  signals: SignalEntry[];
}

export default function InspectorPanel({ position, signals }: InspectorPanelProps) {
  const isPrivacyMode = useIsPrivacyMode();

  const formatPrice = (price: number) => {
    if (isPrivacyMode) return '•••••';
    return `$${price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const formatPercent = (percent: number) => {
    const sign = percent >= 0 ? '+' : '';
    return `${sign}${percent.toFixed(2)}%`;
  };

  return (
    <aside className="fixed top-12 right-0 bottom-8 w-[320px] bg-surface-container border-l border-outline-variant flex flex-col z-30">
      <div className="p-3 border-b border-outline-variant bg-surface-container-low">
        <div className="flex items-center justify-between mb-2">
          <span className="bg-primary-container text-on-primary-container text-[10px] font-bold px-2 py-0.5 rounded-sm">
            ACTIVE ASSET
          </span>
          <span className="material-symbols-outlined text-secondary cursor-pointer">close</span>
        </div>
        <h3 className="font-display-lg text-display-lg text-on-surface">{position.instrument}</h3>
        <div className="flex items-center gap-3 mt-2">
          <p className={`font-data-tabular text-header-md ${position.priceChange >= 0 ? 'text-[#00FF94]' : 'text-[#FF3B30]'}`}>
            {formatPrice(position.markPrice)}
          </p>
          <p className={`text-data-tabular ${position.priceChange >= 0 ? 'text-[#00FF94]' : 'text-[#FF3B30]'}`}>
            {formatPercent(position.priceChange)}
          </p>
        </div>
      </div>
      <div className="flex-1 overflow-y-auto">
        <div className="p-3 border-b border-outline-variant">
          <p className="font-label-caps text-label-caps text-secondary mb-3">CANDLE VISUALIZER (1M)</p>
          <div className="h-24 flex items-end gap-1 bg-surface-container-lowest p-2 border border-outline-variant">
            <div className="flex-1 bg-[#FF3B30] h-3/4 opacity-40"></div>
            <div className="flex-1 bg-[#00FF94] h-2/4"></div>
            <div className="flex-1 bg-[#00FF94] h-4/4"></div>
            <div className="flex-1 bg-[#FF3B30] h-1/4 opacity-40"></div>
            <div className="flex-1 bg-[#00FF94] h-3/4"></div>
            <div className="flex-1 bg-[#00FF94] h-5/6"></div>
            <div className="flex-1 bg-[#00FF94] h-4/6"></div>
          </div>
        </div>
        <div className="p-3 space-y-3">
          <div>
            <p className="font-label-caps text-label-caps text-secondary mb-1">LEVERAGE</p>
            <div className="flex items-center justify-between">
              <span className="font-data-tabular text-body-base text-on-surface">{position.leverage}</span>
              <span className="material-symbols-outlined text-[16px] text-primary">edit</span>
            </div>
          </div>
          <div>
            <p className="font-label-caps text-label-caps text-secondary mb-1">FUNDING RATE</p>
            <div className="flex items-center justify-between">
              <span className="font-data-tabular text-body-base text-on-surface">
                {position.fundingRate.toFixed(4)}%
              </span>
              <span className="text-data-tabular text-secondary">Next in {position.fundingNextIn}</span>
            </div>
          </div>
          <div>
            <p className="font-label-caps text-label-caps text-secondary mb-1">LIQUIDATION PRICE</p>
            <span className="font-data-tabular text-body-base text-error">
              {formatPrice(position.liquidationPrice)}
            </span>
          </div>
          <div>
            <p className="font-label-caps text-label-caps text-secondary mb-1">MARGIN USED</p>
            <div className="w-full bg-surface-container-lowest h-1.5 border border-outline-variant mt-1">
              <div className="bg-primary h-full" style={{ width: `${position.marginPercent}%` }}></div>
            </div>
            <div className="flex justify-between mt-1">
              <span className="text-[10px] text-secondary">
                {isPrivacyMode ? '•••••' : formatPrice(position.marginUsed)}
              </span>
              <span className="text-[10px] text-secondary">{position.marginPercent}%</span>
            </div>
          </div>
        </div>
        <div className="p-3 mt-3">
          <p className="font-label-caps text-label-caps text-secondary mb-3">ML SIGNAL TELEMETRY</p>
          <div className="space-y-2">
            {signals.map((entry, index) => (
              <div key={index} className="flex items-center gap-3 text-[11px] font-code-sm">
                <span className="text-primary">[{entry.timestamp}]</span>
                <span className="text-on-surface">{entry.signal}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
      <div className="p-3 bg-surface-container-low border-t border-outline-variant">
        <div className="grid grid-cols-2 gap-2">
          <button className="bg-[#00FF94] text-black font-bold py-3 text-[12px] hover:brightness-110">
            BUY / LONG
          </button>
          <button className="bg-[#FF3B30] text-white font-bold py-3 text-[12px] hover:brightness-110">
            SELL / SHORT
          </button>
        </div>
      </div>
    </aside>
  );
}
