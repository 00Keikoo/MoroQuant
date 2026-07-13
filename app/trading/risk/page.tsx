'use client';

import { riskData } from '@/lib/mock-data/risk';
import { TradingTopBar, TradingSidebar, MetricCard } from '@/components/trading/shared';
import { StressTestTable } from '@/components/trading/risk/StressTestTable';

export default function RiskCenterPage() {
  const { analytics, stressTests, exposureBreakdown, concentrationRisk } = riskData;

  const navItems = [
    { icon: 'dashboard', label: 'Dashboard' },
    { icon: 'security', label: 'Risk', active: true },
    { icon: 'swap_horiz', label: 'Trades' },
    { icon: 'monitoring', label: 'Live Analytics' },
    { icon: 'pie_chart', label: 'Portfolio' }
  ];

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-background">
      <TradingTopBar
        title="MoroQuant"
        searchPlaceholder="Search Risk Nodes..."
      />

      <div className="flex flex-1 overflow-hidden mt-12">
        <TradingSidebar
          items={navItems}
          footer={
            <div className="flex items-center gap-3 px-2 py-2 text-on-surface-variant hover:text-primary transition-colors cursor-pointer">
              <span className="material-symbols-outlined">settings</span>
              <span className="hidden md:block font-mono-label text-mono-label">Settings</span>
            </div>
          }
        />

        <main className="flex-1 flex overflow-hidden bg-background ml-16 md:ml-56">
          <div className="flex-1 flex flex-col overflow-y-auto">
            <div className="grid grid-cols-4 border-b border-outline-variant bg-surface-container-lowest">
              <MetricCard label="VAR 95%" value={`$${analytics.var95.toLocaleString()}`} valueColor="error" className="border-r border-outline-variant" />
              <MetricCard label="EXPECTED SHORTFALL" value={`$${analytics.expectedShortfall.toLocaleString()}`} valueColor="error" className="border-r border-outline-variant" />
              <MetricCard label="MAX DRAWDOWN" value={`${(analytics.maxDrawdown * 100).toFixed(2)}%`} valueColor="error" className="border-r border-outline-variant" />
              <MetricCard label="VOLATILITY" value={`${(analytics.volatility * 100).toFixed(2)}%`} valueColor="on-surface" />
            </div>

            <div className="p-4 space-y-4">
              <div className="bg-surface border border-outline-variant p-4">
                <h3 className="font-headline-sm text-headline-sm text-primary mb-4">RISK ANALYTICS</h3>
                <div className="grid grid-cols-3 gap-4">
                  <MetricCard label="SHARPE RATIO" value={analytics.sharpeRatio.toFixed(2)} valueColor="primary" className="p-0" />
                  <MetricCard label="BETA" value={analytics.beta.toFixed(2)} valueColor="on-surface" className="p-0" />
                  <MetricCard label="BTC CORRELATION" value={analytics.correlationBTC.toFixed(2)} valueColor="on-surface" className="p-0" />
                </div>
              </div>

              <StressTestTable tests={stressTests} />

              {/* Exposure & Concentration */}
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-surface border border-outline-variant p-4">
                  <h3 className="font-headline-sm text-headline-sm text-primary mb-4">EXPOSURE BREAKDOWN</h3>
                  <div className="space-y-3">
                    <div className="flex justify-between">
                      <span className="font-mono-label text-mono-label text-on-surface-variant">CRYPTO</span>
                      <span className="font-mono-data text-mono-data text-on-surface">{(exposureBreakdown.crypto * 100).toFixed(0)}%</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="font-mono-label text-mono-label text-on-surface-variant">COMMODITIES</span>
                      <span className="font-mono-data text-mono-data text-on-surface">{(exposureBreakdown.commodities * 100).toFixed(0)}%</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="font-mono-label text-mono-label text-on-surface-variant">EQUITIES</span>
                      <span className="font-mono-data text-mono-data text-on-surface">{(exposureBreakdown.equities * 100).toFixed(0)}%</span>
                    </div>
                  </div>
                </div>

                <div className="bg-surface border border-outline-variant p-4">
                  <h3 className="font-headline-sm text-headline-sm text-primary mb-4">CONCENTRATION RISK</h3>
                  <div className="space-y-3">
                    <div className="flex justify-between">
                      <span className="font-mono-label text-mono-label text-on-surface-variant">BTC EXPOSURE</span>
                      <span className="font-mono-data text-mono-data text-error">{(concentrationRisk.btcExposure * 100).toFixed(0)}%</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="font-mono-label text-mono-label text-on-surface-variant">ETH EXPOSURE</span>
                      <span className="font-mono-data text-mono-data text-on-surface">{(concentrationRisk.ethExposure * 100).toFixed(0)}%</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="font-mono-label text-mono-label text-on-surface-variant">TOP 3 CONCENTRATION</span>
                      <span className="font-mono-data text-mono-data text-error">{(concentrationRisk.topThreeConcentration * 100).toFixed(0)}%</span>
                    </div>
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
