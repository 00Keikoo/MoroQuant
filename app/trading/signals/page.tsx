'use client';

import { useState } from 'react';
import { signalsData } from '@/lib/mock-data/signals';
import { TradingTopBar, TradingSidebar, TradingLayout, LiveIndicator } from '@/components/trading/shared';
import { SignalsTable } from '@/components/trading/signals/SignalsTable';
import { SignalFeatures } from '@/components/trading/signals/SignalFeatures';

export default function MLSignalsPage() {
  const [selectedTimeframe, setSelectedTimeframe] = useState<'1h' | '4h' | '1d'>('1h');
  const { signals } = signalsData;

  const filteredSignals = signals.filter(s => s.timeframe === selectedTimeframe);

  const navItems = [
    { icon: 'query_stats', label: 'Trading' },
    { icon: 'science', label: 'Signals', active: true }
  ];

  return (
    <TradingLayout
      topBar={<TradingTopBar searchPlaceholder="Search Symbols..." />}
      sidebar={
        <TradingSidebar
          items={navItems}
          footer={
            <button className="w-full bg-primary-container text-on-primary font-label-caps text-label-caps py-2 rounded-sm uppercase tracking-widest hover:brightness-110 active:scale-95 transition-all">
              New Strategy
            </button>
          }
        />
      }
    >
      <div className="flex items-center justify-between px-4 py-3 bg-surface-container-low border-b border-outline-variant">
        <div className="flex items-center gap-2">
          <span className="font-label-caps text-label-caps text-on-surface-variant">TIMEFRAME:</span>
          <div className="flex gap-2">
            {(['1h', '4h', '1d'] as const).map((tf) => (
              <button
                key={tf}
                onClick={() => setSelectedTimeframe(tf)}
                className={`px-3 py-1 font-label-caps text-label-caps ${
                  selectedTimeframe === tf
                    ? 'bg-primary-container text-on-primary-container'
                    : 'bg-surface-container text-on-surface-variant hover:bg-surface-container-high'
                }`}
              >
                {tf.toUpperCase()}
              </button>
            ))}
          </div>
        </div>
        <LiveIndicator />
      </div>

      <div className="flex-1 overflow-y-auto p-2">
        <SignalsTable signals={filteredSignals} />
        <SignalFeatures signals={filteredSignals} />
      </div>
    </TradingLayout>
  );
}
