'use client';

import { executionData } from '@/lib/mock-data/execution';
import { TradingTopBar, TradingSidebar, LiveIndicator, MetricCard } from '@/components/trading/shared';
import { OrdersTable } from '@/components/trading/execution/OrdersTable';

export default function ExecutionPage() {
  const { latency, activeOrders, orderFlow, slippage } = executionData;

  const navItems = [
    { icon: 'dashboard', label: 'Dashboard' },
    { icon: 'monitoring', label: 'Live Analytics' },
    { icon: 'sensors', label: 'Signals' },
    { icon: 'swap_horiz', label: 'Trades' },
    { icon: 'pie_chart', label: 'Portfolio' },
    { icon: 'security', label: 'Risk' },
    { icon: 'play_circle', label: 'Execution', active: true }
  ];

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-background">
      <TradingTopBar
        title="MoroQuant"
        searchPlaceholder="Search Tickers, Order IDs..."
      />

      <div className="flex flex-1 overflow-hidden mt-12">
        <TradingSidebar
          items={navItems}
          footer={
            <div className="text-on-surface-variant hover:bg-surface-variant transition-colors font-mono-label text-mono-label px-4 py-3 cursor-pointer flex items-center gap-3">
              <span className="material-symbols-outlined text-[18px]">settings</span>
              <span className="hidden md:block">Settings</span>
            </div>
          }
        />

        <main className="flex flex-col flex-1 overflow-hidden bg-background ml-16 md:ml-56">
          <div className="flex items-center justify-between px-4 py-2 bg-surface-container-low border-b border-outline-variant">
            <div className="flex items-center gap-6">
              <MetricCard label="Active Orders" value={orderFlow.totalOrders.toLocaleString()} valueColor="primary" className="p-0" />
              <MetricCard label="Fill Rate" value={`${(orderFlow.fillRate * 100).toFixed(1)}%`} valueColor="primary" className="p-0" />
              <MetricCard label="Avg Latency" value={`${latency.totalRoundtrip.toFixed(1)}ms`} valueColor="primary" className="p-0" />
            </div>
            <LiveIndicator />
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            <div className="bg-surface border border-outline-variant">
              <div className="px-4 py-2 border-b border-outline-variant bg-surface-container-low">
                <span className="font-mono-label text-mono-label text-on-surface uppercase">Latency Metrics</span>
              </div>
              <div className="grid grid-cols-4 gap-4 p-4">
                <MetricCard label="ORDER TO EXCHANGE" value={`${latency.orderToExchange.toFixed(1)}ms`} valueColor="primary" />
                <MetricCard label="MARKET DATA FEED" value={`${latency.marketDataFeed.toFixed(1)}ms`} valueColor="primary" />
                <MetricCard label="SIGNAL TO ORDER" value={`${latency.signalToOrder.toFixed(1)}ms`} valueColor="on-surface" />
                <MetricCard label="TOTAL ROUNDTRIP" value={`${latency.totalRoundtrip.toFixed(1)}ms`} valueColor="on-surface" />
              </div>
            </div>

            <OrdersTable orders={activeOrders} />

            {/* Order Flow Stats */}
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-surface border border-outline-variant p-4">
                <h3 className="font-headline-sm text-headline-sm text-primary mb-4">ORDER FLOW</h3>
                <div className="space-y-3">
                  <div className="flex justify-between">
                    <span className="font-mono-label text-mono-label text-on-surface-variant">EXECUTED</span>
                    <span className="font-mono-data text-mono-data text-primary">{orderFlow.executed.toLocaleString()}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="font-mono-label text-mono-label text-on-surface-variant">PENDING</span>
                    <span className="font-mono-data text-mono-data text-on-surface">{orderFlow.pending.toLocaleString()}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="font-mono-label text-mono-label text-on-surface-variant">CANCELLED</span>
                    <span className="font-mono-data text-mono-data text-error">{orderFlow.cancelled.toLocaleString()}</span>
                  </div>
                </div>
              </div>

              <div className="bg-surface border border-outline-variant p-4">
                <h3 className="font-headline-sm text-headline-sm text-primary mb-4">SLIPPAGE</h3>
                <div className="space-y-3">
                  <div className="flex justify-between">
                    <span className="font-mono-label text-mono-label text-on-surface-variant">AVERAGE</span>
                    <span className="font-mono-data text-mono-data text-on-surface">{(slippage.average * 100).toFixed(2)}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="font-mono-label text-mono-label text-on-surface-variant">MAX</span>
                    <span className="font-mono-data text-mono-data text-error">{(slippage.max * 100).toFixed(2)}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="font-mono-label text-mono-label text-on-surface-variant">MIN</span>
                    <span className="font-mono-data text-mono-data text-primary">{(slippage.min * 100).toFixed(2)}%</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
