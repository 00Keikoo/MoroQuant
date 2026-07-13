'use client';

import { useState } from 'react';
import { useIsPrivacyMode } from '@/lib/stores/privacyStore';
import EquityCurvePanel from '@/components/dashboard/EquityCurvePanel';
import ActiveInventoryTable from '@/components/dashboard/ActiveInventoryTable';
import InspectorPanel from '@/components/dashboard/InspectorPanel';
import { dashboardMock } from '@/lib/mock-data/dashboard-mock';

export default function TradingDashboardPage() {
  const isPrivacyMode = useIsPrivacyMode();
  const [selectedPosition, setSelectedPosition] = useState(0);

  const { portfolioSummary, equityCurve, activeInventory, mlSignalTelemetry } = dashboardMock;
  const currentPosition = activeInventory[selectedPosition];

  const formatValue = (value: number, prefix = '') => {
    if (isPrivacyMode) return '•••••';
    return `${prefix}${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const formatPercent = (percent: number) => {
    const sign = percent >= 0 ? '+' : '';
    return `${sign}${percent.toFixed(1)}%`;
  };

  return (
    <div className="flex h-screen bg-surface-dim text-on-surface font-body-base overflow-hidden">
      {/* Main content area */}
      <main className="flex-1 flex flex-col overflow-hidden ml-[320px] mr-[320px]">
        {/* Top header bar */}
        <header className="h-12 px-4 flex items-center justify-between border-b border-outline-variant bg-surface-container-low">
          <div className="flex items-center gap-4">
            <div className="relative">
              <input
                className="bg-surface-container-lowest border border-outline-variant text-body-base px-4 py-1 w-64 focus:border-primary-container outline-none placeholder:text-secondary/50"
                placeholder="Search Markets (⌘K)"
                type="text"
              />
            </div>
            <nav className="hidden md:flex items-center gap-3">
              <a className="text-secondary hover:text-on-surface text-[12px] font-medium" href="#">
                System Health
              </a>
              <a className="text-secondary hover:text-on-surface text-[12px] font-medium" href="#">
                Network
              </a>
              <a className="text-secondary hover:text-on-surface text-[12px] font-medium" href="#">
                Latency
              </a>
            </nav>
          </div>
          <div className="flex items-center gap-3">
            <button className="bg-surface-container border border-outline-variant px-3 py-1 text-[11px] font-bold text-secondary hover:text-on-surface transition-colors flex items-center gap-1">
              <span className="material-symbols-outlined text-[16px]">terminal</span>
              Deploy
            </button>
            <button className="bg-[#93000a] text-white px-3 py-1 text-[11px] font-bold hover:bg-red-700 transition-colors flex items-center gap-1">
              <span className="material-symbols-outlined text-[16px]">bolt</span>
              Kill Switch
            </button>
            <div className="h-6 w-px bg-outline-variant mx-1"></div>
            <span className="material-symbols-outlined text-secondary cursor-pointer hover:text-on-surface">
              settings_input_component
            </span>
          </div>
        </header>

        {/* Dashboard content */}
        <div className="flex-1 overflow-y-auto p-3">
          {/* Dashboard header stats */}
          <div className="grid grid-cols-4 gap-3 mb-3">
            <div className="bg-surface-container p-3 border border-outline-variant flex flex-col justify-between">
              <p className="font-label-caps text-label-caps text-secondary">NET PNL (DAILY)</p>
              <div className="flex items-end justify-between mt-2">
                <p className="font-data-tabular text-display-lg text-[#00FF94]">
                  {isPrivacyMode ? '•••••' : `+${portfolioSummary.netPnlDaily.toLocaleString()}`}
                </p>
                <span className="text-data-tabular text-[#00FF94]">
                  {formatPercent(portfolioSummary.netPnlDailyPercent)}
                </span>
              </div>
            </div>
            <div className="bg-surface-container p-3 border border-outline-variant flex flex-col justify-between">
              <p className="font-label-caps text-label-caps text-secondary">GROSS EXPOSURE</p>
              <div className="flex items-end justify-between mt-2">
                <p className="font-data-tabular text-display-lg text-on-surface">
                  {isPrivacyMode ? '•••••' : `$${portfolioSummary.grossExposure.toLocaleString()}`}
                </p>
                <span className="text-data-tabular text-secondary">{portfolioSummary.exposureLimit}% Limit</span>
              </div>
            </div>
            <div className="bg-surface-container p-3 border border-outline-variant flex flex-col justify-between">
              <p className="font-label-caps text-label-caps text-secondary">ACTIVE ORDERS</p>
              <div className="flex items-end justify-between mt-2">
                <p className="font-data-tabular text-display-lg text-primary">
                  {portfolioSummary.activeOrders.toLocaleString()}
                </p>
                <span className="text-data-tabular text-secondary">
                  {portfolioSummary.executedOrders} Executed
                </span>
              </div>
            </div>
            <div className="bg-surface-container p-3 border border-outline-variant flex flex-col justify-between">
              <p className="font-label-caps text-label-caps text-secondary">SHARPE RATIO (30D)</p>
              <div className="flex items-end justify-between mt-2">
                <p className="font-data-tabular text-display-lg text-on-surface">
                  {portfolioSummary.sharpeRatio30d}
                </p>
                <span className="text-data-tabular text-[#00FF94]">{portfolioSummary.sharpeStatus}</span>
              </div>
            </div>
          </div>

          {/* Central workspace (chart & table) */}
          <div className="flex-1 grid grid-rows-2 gap-3" style={{ height: 'calc(100vh - 240px)' }}>
            {/* Equity Curve Section */}
            <EquityCurvePanel data={equityCurve} />

            {/* Active Inventory Table */}
            <ActiveInventoryTable positions={activeInventory} />
          </div>
        </div>
      </main>

      {/* Right Inspector Panel */}
      <InspectorPanel
        position={{
          instrument: currentPosition.instrument,
          markPrice: currentPosition.markPrice,
          priceChange: 2.41,
          leverage: currentPosition.leverage,
          fundingRate: currentPosition.fundingRate,
          fundingNextIn: currentPosition.fundingNextIn,
          liquidationPrice: currentPosition.liquidationPrice,
          marginUsed: currentPosition.marginUsed,
          marginPercent: currentPosition.marginPercent,
        }}
        signals={mlSignalTelemetry}
      />

      {/* Footer */}
      <footer className="fixed bottom-0 left-0 w-full h-8 flex items-center justify-between z-50 bg-surface-container-lowest border-t border-outline-variant px-4 font-code-sm text-code-sm">
        <div className="flex items-center gap-4">
          <span className="text-secondary">
            System Status: <span className="text-[#00FF94]">Operational</span>
          </span>
          <span className="text-secondary">
            Latency: <span className="text-primary">1.2ms</span>
          </span>
          <span className="text-secondary">
            Environment: <span className="text-on-surface">Production</span>
          </span>
        </div>
        <div className="flex items-center gap-4">
          <a className="text-secondary hover:text-on-surface transition-colors" href="#">
            Logs
          </a>
          <a className="text-secondary hover:text-on-surface transition-colors" href="#">
            Metrics
          </a>
          <a className="text-secondary hover:text-on-surface transition-colors" href="#">
            Security
          </a>
        </div>
      </footer>
    </div>
  );
}
