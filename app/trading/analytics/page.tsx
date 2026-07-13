'use client';

import { analyticsData } from '@/lib/mock-data/analytics';
import { TradingTopBar, TradingSidebar, MetricCard } from '@/components/trading/shared';

export default function LiveAnalyticsPage() {
  const { performance, tradeStats } = analyticsData;

  const navItems = [
    { icon: 'query_stats', label: 'Trading' },
    { icon: 'monitoring', label: 'Analytics', active: true }
  ];

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <TradingTopBar />
      <TradingSidebar
        items={navItems}
        footer={
          <button className="w-full bg-primary-container text-on-primary-container py-2 rounded-sm font-label-caps text-label-caps flex items-center justify-center gap-2 active:scale-95 transition-transform">
            <span className="material-symbols-outlined text-sm">add</span>
            <span className="hidden md:block">New Strategy</span>
          </button>
        }
      />

      <main className="ml-16 md:ml-56 mt-12 flex-1 flex flex-col overflow-hidden">
        <div className="grid grid-cols-6 border-b border-outline-variant bg-[#090909]">
          <MetricCard label="GROSS PROFIT" value={`$${performance.grossProfit.toLocaleString()}`} valueColor="primary" className="border-r border-outline-variant p-3" />
          <MetricCard label="GROSS LOSS" value={`$${performance.grossLoss.toLocaleString()}`} valueColor="error" className="border-r border-outline-variant p-3" />
          <MetricCard label="AVERAGE WIN" value={`$${performance.averageWin.toLocaleString()}`} valueColor="on-surface" className="border-r border-outline-variant p-3" />
          <MetricCard label="AVERAGE LOSS" value={`$${performance.averageLoss.toLocaleString()}`} valueColor="on-surface" className="border-r border-outline-variant p-3" />
          <MetricCard label="WIN RATE" value={`${(performance.winRate * 100).toFixed(1)}%`} valueColor="primary" className="border-r border-outline-variant p-3" />
          <MetricCard label="PROFIT FACTOR" value={performance.profitFactor.toFixed(2)} valueColor="primary" className="p-3" />
        </div>

        {/* Content Area */}
        <div className="flex-1 overflow-y-auto p-4">
          <div className="grid grid-cols-2 gap-4">
            {/* Performance Metrics */}
            <div className="bg-surface-dim border border-outline-variant p-4">
              <h3 className="font-header-md text-header-md text-primary mb-4">PERFORMANCE METRICS</h3>
              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="font-label-caps text-label-caps text-on-surface-variant">NET PROFIT</span>
                  <span className="font-data-tabular text-data-tabular text-primary">${performance.netProfit.toLocaleString()}</span>
                </div>
                <div className="flex justify-between">
                  <span className="font-label-caps text-label-caps text-on-surface-variant">SHARPE RATIO</span>
                  <span className="font-data-tabular text-data-tabular text-on-surface">{performance.sharpeRatio.toFixed(2)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="font-label-caps text-label-caps text-on-surface-variant">MAX DRAWDOWN</span>
                  <span className="font-data-tabular text-data-tabular text-error">{(performance.maxDrawdown * 100).toFixed(2)}%</span>
                </div>
              </div>
            </div>

            {/* Trade Statistics */}
            <div className="bg-surface-dim border border-outline-variant p-4">
              <h3 className="font-header-md text-header-md text-primary mb-4">TRADE STATISTICS</h3>
              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="font-label-caps text-label-caps text-on-surface-variant">TOTAL TRADES</span>
                  <span className="font-data-tabular text-data-tabular text-on-surface">{tradeStats.totalTrades.toLocaleString()}</span>
                </div>
                <div className="flex justify-between">
                  <span className="font-label-caps text-label-caps text-on-surface-variant">WINNING TRADES</span>
                  <span className="font-data-tabular text-data-tabular text-primary">{tradeStats.winningTrades.toLocaleString()}</span>
                </div>
                <div className="flex justify-between">
                  <span className="font-label-caps text-label-caps text-on-surface-variant">LOSING TRADES</span>
                  <span className="font-data-tabular text-data-tabular text-error">{tradeStats.losingTrades.toLocaleString()}</span>
                </div>
                <div className="flex justify-between">
                  <span className="font-label-caps text-label-caps text-on-surface-variant">AVG TRADE LENGTH</span>
                  <span className="font-data-tabular text-data-tabular text-on-surface">{tradeStats.averageTradeLength}</span>
                </div>
              </div>
            </div>

            {/* Best/Worst Trades */}
            <div className="bg-surface-dim border border-outline-variant p-4 col-span-2">
              <h3 className="font-header-md text-header-md text-primary mb-4">EXTREME TRADES</h3>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <span className="font-label-caps text-label-caps text-on-surface-variant">BEST TRADE</span>
                  <div className="font-data-tabular text-display-lg text-primary mt-2">+${tradeStats.bestTrade.toLocaleString()}</div>
                </div>
                <div>
                  <span className="font-label-caps text-label-caps text-on-surface-variant">WORST TRADE</span>
                  <div className="font-data-tabular text-display-lg text-error mt-2">${tradeStats.worstTrade.toLocaleString()}</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
