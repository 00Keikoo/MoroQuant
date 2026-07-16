'use client';

import TradingModeSwitch from '@/components/terminal/TradingModeSwitch';
import EmergencyStopButton from '@/components/terminal/EmergencyStopButton';
import InstitutionalHeader from '@/components/terminal/InstitutionalHeader';
import StatusBar from '@/components/terminal/StatusBar';
import EquityCurve from '@/components/terminal/EquityCurve';
import PortfolioOverview from '@/components/terminal/PortfolioOverview';
import OpenPositionsTable from '@/components/terminal/OpenPositionsTable';
import RecentTradesPanel from '@/components/terminal/RecentTradesPanel';
import ModelIntelligence from '@/components/terminal/ModelIntelligence';
import PerformanceStats from '@/components/terminal/PerformanceStats';

export default function InstitutionalTerminal() {
  return (
    <div className="flex flex-col h-screen bg-[#090909] text-white">
      {/* Top Navigation Bar */}
      <div className="flex items-center justify-between px-4 py-3 bg-[#141414] border-b border-[#262626]">
        <div className="flex items-center gap-4">
          <h1 className="text-lg font-bold text-white" style={{ fontFamily: 'IBM Plex Sans' }}>
            MoroQuant <span className="text-[#FF6B00]">V2</span> <span className="text-xs text-[#666666] font-normal">OS</span>
          </h1>
          <TradingModeSwitch />
        </div>
        <EmergencyStopButton />
      </div>

      {/* Institutional Header */}
      <InstitutionalHeader />

      {/* Main Content - 3 Column Layout */}
      <div className="flex-1 overflow-hidden">
        <div className="h-full grid grid-cols-12 gap-3 p-3">
          {/* Column 1: Portfolio & Positions */}
          <div className="col-span-3 flex flex-col gap-3 overflow-y-auto">
            <PortfolioOverview />
            <OpenPositionsTable />
            <RecentTradesPanel />
          </div>

          {/* Column 2: Equity Curve & Stats */}
          <div className="col-span-6 flex flex-col gap-3 overflow-y-auto">
            <EquityCurve />
            <div className="grid grid-cols-2 gap-3">
              <PerformanceStats />
              <div className="bg-[#141414] border border-[#262626] rounded-sm p-4">
                <div className="text-xs font-bold text-[#666666] tracking-wider mb-3">RISK MANAGEMENT</div>
                <div className="space-y-2.5">
                  <div className="flex justify-between items-center">
                    <span className="text-xs text-[#666666]">Total Exposure</span>
                    <span className="text-sm font-mono text-white">$0.00</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-xs text-[#666666]">Risk Score</span>
                    <span className="text-xs font-mono text-green-500">🟢 LOW</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-xs text-[#666666]">Open Risk</span>
                    <span className="text-sm font-mono text-[#A1A1A1]">$0.00</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-xs text-[#666666]">Emergency Status</span>
                    <span className="text-xs font-mono text-green-500">🟢 NORMAL</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Column 3: Model Intelligence */}
          <div className="col-span-3 flex flex-col gap-3 overflow-y-auto">
            <ModelIntelligence />

            {/* Active Signals */}
            <div className="bg-[#141414] border border-[#262626] rounded-sm p-4">
              <div className="text-xs font-bold text-[#666666] tracking-wider mb-3">ACTIVE SIGNALS</div>
              <div className="space-y-2">
                <div className="flex items-center justify-between p-2 bg-[#0e0e0e] border border-[#262626] rounded-sm">
                  <div className="flex items-center gap-2">
                    <span className="text-blue-500 text-lg">🔵</span>
                    <div>
                      <div className="text-xs font-mono text-white font-bold">BTCUSDT</div>
                      <div className="text-[10px] text-[#666666]">1H</div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-xs font-mono text-green-500">LONG</div>
                    <div className="text-[10px] text-[#666666]">82%</div>
                  </div>
                </div>

                <div className="text-xs text-[#666666] text-center py-4">No active signals</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Bloomberg-Style Status Bar */}
      <StatusBar />
    </div>
  );
}
