'use client';

import { useState } from 'react';
import { useEquityHistory } from '@/lib/hooks/usePerformanceData';
import SkeletonChart from '@/components/shared/widgets/SkeletonChart';
import WidgetEmpty from '@/components/shared/widgets/WidgetEmpty';
import WidgetError from '@/components/shared/widgets/WidgetError';
import type { EquityRange } from '@/lib/services/performanceService';

type TimeframeButton = '7D' | '30D' | 'ALL';

const TIMEFRAME_TO_RANGE: Record<TimeframeButton, EquityRange> = {
  '7D': '7d',
  '30D': '30d',
  'ALL': 'all',
};

export default function EquityCurvePanel() {
  const [selectedTimeframe, setSelectedTimeframe] = useState<TimeframeButton>('7D');
  const range = TIMEFRAME_TO_RANGE[selectedTimeframe];
  const { data: equityData = [], isLoading, error, refetch, isFetching } = useEquityHistory(range);

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
              onClick={() => setSelectedTimeframe('ALL')}
              className={`px-2 py-1 text-[10px] font-bold ${
                selectedTimeframe === 'ALL'
                  ? 'bg-primary text-on-primary'
                  : 'text-secondary hover:text-on-surface'
              }`}
            >
              ALL
            </button>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-primary"></div>
            <span className="text-label-caps text-secondary">ACCOUNT EQUITY</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-secondary"></div>
            <span className="text-label-caps text-secondary">BENCHMARK</span>
          </div>
        </div>
      </div>
      <div className="flex-1 relative bg-surface-container-lowest">
        {isLoading || isFetching ? (
          <SkeletonChart message="Loading equity data..." />
        ) : error ? (
          <div className="absolute inset-0 flex items-center justify-center">
            <WidgetError error={error} onRetry={refetch} />
          </div>
        ) : equityData.length === 0 ? (
          <div className="absolute inset-0 flex items-center justify-center">
            <WidgetEmpty
              message="No equity data available"
              description="Data will appear once trades are executed"
            />
          </div>
        ) : (
          <>
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
              <div className="w-full h-px bg-outline-variant/30 top-1/4 absolute"></div>
              <div className="w-full h-px bg-outline-variant/30 top-2/4 absolute"></div>
              <div className="w-full h-px bg-outline-variant/30 top-3/4 absolute"></div>
            </div>
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="text-xs text-secondary/50">
                {equityData.length} data points | Latest: ${equityData[equityData.length - 1]?.equity.toFixed(2) || '0.00'}
              </span>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
