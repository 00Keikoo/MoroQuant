'use client';

import { useState } from 'react';

interface EquityCurveData {
  strategyName: string;
  timeframe: string;
  dataPoints: Array<{ timestamp: string; value: number }>;
  benchmark: Array<{ timestamp: string; value: number }>;
}

interface EquityCurvePanelProps {
  data: EquityCurveData;
}

export default function EquityCurvePanel({ data }: EquityCurvePanelProps) {
  const [selectedTimeframe, setSelectedTimeframe] = useState<'7D' | '30D' | '90D'>('7D');

  return (
    <div className="bg-surface-container-low border border-outline-variant flex flex-col overflow-hidden">
      <div className="flex items-center justify-between px-3 py-2 border-b border-outline-variant">
        <div className="flex items-center gap-3">
          <p className="font-header-md text-header-md text-on-surface">Equity Curve</p>
          <div className="flex bg-surface-container-lowest p-1 gap-1 border border-outline-variant">
            <button
              onClick={() => setSelectedTimeframe('7D')}
              className={`px-2 py-1 text-[10px] font-bold ${
                selectedTimeframe === '7D'
                  ? 'bg-primary text-on-primary'
                  : 'text-secondary hover:text-on-surface'
              }`}
            >
              7D
            </button>
            <button
              onClick={() => setSelectedTimeframe('30D')}
              className={`px-2 py-1 text-[10px] font-bold ${
                selectedTimeframe === '30D'
                  ? 'bg-primary text-on-primary'
                  : 'text-secondary hover:text-on-surface'
              }`}
            >
              30D
            </button>
            <button
              onClick={() => setSelectedTimeframe('90D')}
              className={`px-2 py-1 text-[10px] font-bold ${
                selectedTimeframe === '90D'
                  ? 'bg-primary text-on-primary'
                  : 'text-secondary hover:text-on-surface'
              }`}
            >
              90D
            </button>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-primary"></div>
            <span className="text-label-caps text-secondary">{data.strategyName}</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-secondary"></div>
            <span className="text-label-caps text-secondary">BENCHMARK</span>
          </div>
        </div>
      </div>
      <div className="flex-1 relative bg-surface-container-lowest">
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div className="w-full h-px bg-outline-variant/30 top-1/4 absolute"></div>
          <div className="w-full h-px bg-outline-variant/30 top-2/4 absolute"></div>
          <div className="w-full h-px bg-outline-variant/30 top-3/4 absolute"></div>
        </div>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-xs text-secondary/50">Chart visualization placeholder</span>
        </div>
      </div>
    </div>
  );
}
