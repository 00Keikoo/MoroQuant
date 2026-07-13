'use client';

import { portfolioData } from '@/lib/mock-data/portfolio';
import { TradingTopBar, TradingSidebar, MetricCard } from '@/components/trading/shared';
import { PortfolioPositionsTable } from '@/components/trading/portfolio/PortfolioPositionsTable';

export default function PortfolioPage() {
  const { summary, positions, targetWeights } = portfolioData;

  const navItems = [
    { icon: 'pie_chart', label: 'Portfolio', active: true },
    { icon: 'dashboard', label: 'Dashboard' },
    { icon: 'monitoring', label: 'Live Analytics' },
    { icon: 'sensors', label: 'Signals' },
    { icon: 'swap_horiz', label: 'Trades' },
    { icon: 'security', label: 'Risk' }
  ];

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-background">
      <TradingTopBar
        title="MoroQuant"
        searchPlaceholder="TICKER OR ISIN..."
        showKillSwitch={true}
      />

      <div className="flex flex-1 overflow-hidden mt-12">
        <TradingSidebar
          items={navItems}
          footer={
            <div className="text-on-surface-variant hover:bg-surface-variant hover:text-primary px-3 py-2 flex items-center gap-3 cursor-pointer transition-colors duration-75">
              <span className="material-symbols-outlined">settings</span>
              <span className="hidden md:block font-mono-label text-mono-label">Settings</span>
            </div>
          }
        />

        <main className="flex-1 flex flex-col overflow-hidden bg-background ml-16 md:ml-56">
          <div className="grid grid-cols-4 border-b border-outline-variant bg-surface-container-lowest">
            <MetricCard
              label="TOTAL EQUITY"
              value={`$${summary.totalEquity.toLocaleString()}`}
              valueColor="primary"
              className="border-r border-outline-variant"
            />
            <MetricCard
              label="UNREALIZED PNL"
              value={`${summary.unrealizedPnl >= 0 ? '+' : ''}$${summary.unrealizedPnl.toLocaleString()}`}
              valueColor={summary.unrealizedPnl >= 0 ? 'primary' : 'error'}
              className="border-r border-outline-variant"
            />
            <MetricCard
              label="DAILY PNL"
              value={`${summary.dailyPnl >= 0 ? '+' : ''}$${summary.dailyPnl.toLocaleString()}`}
              valueColor={summary.dailyPnl >= 0 ? 'primary' : 'error'}
              className="border-r border-outline-variant"
            />
            <MetricCard
              label="DAILY RETURN"
              value={`${summary.dailyReturn >= 0 ? '+' : ''}${summary.dailyReturn}%`}
              valueColor={summary.dailyReturn >= 0 ? 'primary' : 'error'}
            />
          </div>

          <div className="flex-1 overflow-y-auto p-4">
            <PortfolioPositionsTable positions={positions} />

            {/* Target Weights */}
            <div className="mt-4 bg-surface border border-outline-variant">
              <div className="px-4 py-2 border-b border-outline-variant bg-surface-container-low">
                <span className="font-mono-label text-mono-label text-on-surface uppercase">Target Weights</span>
              </div>
              <div className="p-4 grid grid-cols-4 gap-3">
                {Object.entries(targetWeights).map(([instrument, weight]) => (
                  <div key={instrument} className="bg-surface-container-low border border-outline-variant p-3">
                    <div className="font-mono-label text-mono-label text-on-surface-variant mb-1">{instrument}</div>
                    <div className="font-mono-data text-xl text-primary">{(weight * 100).toFixed(0)}%</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
