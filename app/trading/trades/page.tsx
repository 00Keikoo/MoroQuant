'use client';

import { useState } from 'react';
import { tradesData } from '@/lib/mock-data/trades';
import { TradingTopBar, TradingSidebar, TradingLayout, LiveIndicator } from '@/components/trading/shared';
import { PositionsTable } from '@/components/trading/trades/PositionsTable';
import { TradeHistoryTable } from '@/components/trading/trades/TradeHistoryTable';
import { MetricsBar } from '@/components/trading/trades/MetricsBar';

export default function TradesPage() {
  const [activeTab, setActiveTab] = useState<'positions' | 'history'>('positions');
  const { activePositions, tradeHistory } = tradesData;

  const navItems = [
    { icon: 'query_stats', label: 'Trading' },
    { icon: 'swap_horiz', label: 'Trades', active: true }
  ];

  const metrics = [
    { label: 'DAILY PNL', value: '+$142,408.00', valueColor: 'primary' as const },
    { label: 'DAILY RETURN', value: '+1.24%', valueColor: 'primary' as const },
    { label: 'DRAWDOWN', value: '-2.14%', valueColor: 'error' as const },
    { label: 'SHARPE RATIO', value: '3.24', valueColor: 'on-surface' as const },
    { label: 'TOTAL EXPOSURE', value: '$42.4M', valueColor: 'on-surface' as const }
  ];

  return (
    <TradingLayout
      topBar={
        <TradingTopBar>
          <LiveIndicator label="Engine Live" />
        </TradingTopBar>
      }
      sidebar={<TradingSidebar items={navItems} />}
    >
      <MetricsBar metrics={metrics} />

      <div className="flex-1 overflow-y-auto p-2">
        <div className="flex gap-2 mb-2 border-b border-outline-variant">
          <button
            onClick={() => setActiveTab('positions')}
            className={`px-4 py-2 font-label-caps text-label-caps ${
              activeTab === 'positions'
                ? 'text-primary border-b-2 border-primary'
                : 'text-on-surface-variant hover:text-primary'
            }`}
          >
            ACTIVE POSITIONS
          </button>
          <button
            onClick={() => setActiveTab('history')}
            className={`px-4 py-2 font-label-caps text-label-caps ${
              activeTab === 'history'
                ? 'text-primary border-b-2 border-primary'
                : 'text-on-surface-variant hover:text-primary'
            }`}
          >
            TRADE HISTORY
          </button>
        </div>

        {activeTab === 'positions' && <PositionsTable positions={activePositions} />}
        {activeTab === 'history' && <TradeHistoryTable trades={tradeHistory} />}
      </div>
    </TradingLayout>
  );
}
