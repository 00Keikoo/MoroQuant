'use client';

import { useIsPrivacyMode } from '@/lib/stores/privacyStore';

interface Position {
  symbol: string;
  side: string;
  entry_price: number;
  mark_price: number;
  quantity: number;
  unrealized_pnl: number;
  take_profit: number | null;
  stop_loss: number | null;
}

interface InspectorPanelProps {
  position: Position;
  onClose: () => void;
}

export default function InspectorPanel({ position, onClose }: InspectorPanelProps) {
  const isPrivacyMode = useIsPrivacyMode();

  const formatPrice = (price: number) => {
    if (isPrivacyMode) return '•••••';
    return `$${price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const priceChange = ((position.mark_price - position.entry_price) / position.entry_price) * 100;
  const priceChangeFormatted = `${priceChange >= 0 ? '+' : ''}${priceChange.toFixed(2)}%`;

  return (
    <aside className="fixed top-12 right-0 bottom-8 w-[320px] bg-surface-container border-l border-outline-variant flex flex-col z-30">
      <div className="p-3 border-b border-outline-variant bg-surface-container-low">
        <div className="flex items-center justify-between mb-2">
          <span className="bg-primary-container text-on-primary-container text-[10px] font-bold px-2 py-0.5 rounded-sm">
            POSITION DETAILS
          </span>
          <span onClick={onClose} className="material-symbols-outlined text-secondary cursor-pointer hover:text-on-surface">close</span>
        </div>
        <h3 className="font-display-lg text-display-lg text-on-surface">{position.symbol}</h3>
        <div className="flex items-center gap-3 mt-2">
          <p className={`font-data-tabular text-header-md ${priceChange >= 0 ? 'text-tertiary' : 'text-error'}`}>
            {formatPrice(position.mark_price)}
          </p>
          <p className={`text-data-tabular ${priceChange >= 0 ? 'text-tertiary' : 'text-error'}`}>
            {priceChangeFormatted}
          </p>
        </div>
      </div>
      <div className="flex-1 overflow-y-auto">
        <div className="p-3 space-y-4">
          <div>
            <p className="font-mono-label text-[10px] text-outline uppercase tracking-widest mb-1">ENTRY PRICE</p>
            <span className="font-mono-data text-on-surface">
              {formatPrice(position.entry_price)}
            </span>
          </div>
          <div>
            <p className="font-mono-label text-[10px] text-outline uppercase tracking-widest mb-1">MARK PRICE</p>
            <span className="font-mono-data text-on-surface">
              {formatPrice(position.mark_price)}
            </span>
          </div>
          <div>
            <p className="font-mono-label text-[10px] text-outline uppercase tracking-widest mb-1">UNREALIZED PNL</p>
            <span className={`font-mono-data ${position.unrealized_pnl >= 0 ? 'text-tertiary' : 'text-error'} font-bold`}>
              {position.unrealized_pnl >= 0 ? '+' : ''}{formatPrice(position.unrealized_pnl)}
            </span>
          </div>
          <div>
            <p className="font-mono-label text-[10px] text-outline uppercase tracking-widest mb-1">POSITION SIZE</p>
            <span className="font-mono-data text-on-surface">
              {isPrivacyMode ? '•••••' : position.quantity.toFixed(4)}
            </span>
          </div>
          <div>
            <p className="font-mono-label text-[10px] text-outline uppercase tracking-widest mb-1">TAKE PROFIT</p>
            <span className="font-mono-data text-on-surface">
              {position.take_profit ? formatPrice(position.take_profit) : 'Not set'}
            </span>
          </div>
          <div>
            <p className="font-mono-label text-[10px] text-outline uppercase tracking-widest mb-1">STOP LOSS</p>
            <span className="font-mono-data text-on-surface">
              {position.stop_loss ? formatPrice(position.stop_loss) : 'Not set'}
            </span>
          </div>
        </div>
      </div>
    </aside>
  );
}
