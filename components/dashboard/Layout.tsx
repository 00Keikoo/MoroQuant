'use client';

export default function DashboardLayout() {
  return (
    <div className="flex-1 grid grid-cols-12 gap-px bg-outline-variant overflow-y-auto">
      <div className="col-span-12 lg:col-span-8 bg-surface-container-lowest p-container-padding flex flex-col">
        <div className="flex justify-between items-center mb-2">
          <div className="font-mono-label text-mono-label uppercase tracking-widest text-outline">Equity Curve // Net Liq</div>
          <div className="flex gap-4">
            <span className="text-mono-data text-primary font-bold">7D: +4.2%</span>
            <span className="text-mono-data text-tertiary">30D: +12.8%</span>
          </div>
        </div>
        <div className="flex-1 min-h-[220px] relative border border-outline-variant bg-black flex items-center justify-center group">
          <div className="absolute inset-0 opacity-10 pointer-events-none">
            <div className="h-full w-full" style={{ backgroundImage: 'radial-gradient(circle at 2px 2px, #2D2D2D 1px, transparent 0)', backgroundSize: '16px 16px' }}></div>
          </div>
          <div className="z-10 text-center">
            <div className="font-mono-data text-mono-data text-outline mb-1">EQUITY_MARK_LATEST</div>
            <div className="font-mono-data text-[32px] leading-tight text-on-surface font-bold">$12,482,912.04</div>
          </div>
        </div>
      </div>

      <div className="col-span-12 lg:col-span-4 bg-surface-container-lowest p-container-padding">
        <div className="font-mono-label text-mono-label uppercase tracking-widest text-outline mb-2">Daily Performance</div>
        <div className="flex flex-col h-full justify-between gap-4">
          <div className="bg-black border border-outline-variant p-4 flex flex-col justify-center">
            <span className="font-mono-label text-[10px] text-tertiary mb-1">REALIZED PNL (24H)</span>
            <span className="font-mono-data text-[28px] text-tertiary font-bold">+$142,403.20</span>
            <div className="h-1 bg-tertiary/20 mt-2 rounded-full overflow-hidden">
              <div className="h-full bg-tertiary w-[75%]"></div>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div className="bg-black border border-outline-variant p-3">
              <span className="font-mono-label text-[10px] text-outline block mb-1">GROSS EXPOSURE</span>
              <span className="font-mono-data text-on-surface text-lg font-bold">$42.4M</span>
            </div>
            <div className="bg-black border border-outline-variant p-3">
              <span className="font-mono-label text-[10px] text-outline block mb-1">NET DELTA</span>
              <span className="font-mono-data text-primary text-lg font-bold">+12,402</span>
            </div>
            <div className="bg-black border border-outline-variant p-3">
              <span className="font-mono-label text-[10px] text-outline block mb-1">VAR (95%)</span>
              <span className="font-mono-data text-on-surface text-lg font-bold">$1.2M</span>
            </div>
            <div className="bg-black border border-outline-variant p-3">
              <span className="font-mono-label text-[10px] text-outline block mb-1">SHARPE (1Y)</span>
              <span className="font-mono-data text-tertiary text-lg font-bold">3.24</span>
            </div>
          </div>
        </div>
      </div>

      <div className="col-span-12 bg-surface-container-lowest">
        <div className="px-container-padding py-2 border-b border-outline-variant flex justify-between items-center bg-surface-container">
          <div className="font-mono-label text-mono-label uppercase tracking-widest text-on-surface font-bold">Active Inventory / Open Positions</div>
          <div className="flex gap-4">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-tertiary animate-pulse"></div>
              <span className="text-[10px] font-mono-label text-on-surface-variant">WS_LIVE_FEED</span>
            </div>
          </div>
        </div>
        <div className="w-full overflow-x-auto">
          <div className="min-h-[200px] flex items-center justify-center bg-surface-container-lowest">
            <span className="text-outline font-mono-label text-mono-label">POSITIONS TABLE</span>
          </div>
        </div>
      </div>

      <div className="col-span-12 lg:col-span-4 bg-surface-container-lowest p-container-padding border-r border-outline-variant">
        <div className="font-mono-label text-mono-label uppercase tracking-widest text-outline mb-4">Risk Exposure Matrix</div>
        <div className="space-y-4">
          <div>
            <div className="flex justify-between text-mono-label text-[10px] mb-1">
              <span className="text-on-surface-variant">DELTA SENSITIVITY</span>
              <span className="text-tertiary">OK</span>
            </div>
            <div className="h-6 bg-black border border-outline-variant flex items-center px-1">
              <div className="h-4 bg-tertiary w-[82%]"></div>
            </div>
          </div>
          <div>
            <div className="flex justify-between text-mono-label text-[10px] mb-1">
              <span className="text-on-surface-variant">GAMMA SKEW</span>
              <span className="text-tertiary">STABLE</span>
            </div>
            <div className="h-6 bg-black border border-outline-variant flex items-center px-1">
              <div className="h-4 bg-primary w-[34%]"></div>
            </div>
          </div>
          <div className="pt-2">
            <div className="bg-surface-container p-3 border border-outline-variant">
              <div className="font-mono-label text-[9px] text-outline mb-2">DRAWDOWN RECOVERY (30D)</div>
              <div className="h-16 relative"></div>
              <div className="mt-2 text-right font-mono-data text-mono-data text-error">-2.14% MAX DD</div>
            </div>
          </div>
        </div>
      </div>

      <div className="col-span-12 lg:col-span-8 bg-surface-container-lowest p-container-padding">
        <div className="grid grid-cols-2 h-full gap-4">
          <div className="flex flex-col">
            <div className="font-mono-label text-mono-label uppercase tracking-widest text-outline mb-2">Live Signals Feed</div>
            <div className="flex-1 bg-black border border-outline-variant overflow-y-auto scrollbar-hide font-mono-code text-[11px] leading-relaxed p-2">
              <div className="h-full flex items-center justify-center">
                <span className="text-outline">SIGNAL LOG</span>
              </div>
            </div>
          </div>
          <div className="flex flex-col">
            <div className="font-mono-label text-mono-label uppercase tracking-widest text-outline mb-2">Model Health Grid</div>
            <div className="grid grid-cols-2 gap-2 flex-1">
              <div className="bg-surface-container-low border border-outline-variant p-2 flex items-center gap-3">
                <div className="w-3 h-3 bg-tertiary rounded-sm"></div>
                <div className="flex flex-col">
                  <span className="font-mono-label text-[10px] text-on-surface">ARB-BOT-X1</span>
                  <span className="text-[9px] text-tertiary">UPTIME: 99.9%</span>
                </div>
              </div>
              <div className="bg-surface-container-low border border-outline-variant p-2 flex items-center gap-3">
                <div className="w-3 h-3 bg-tertiary rounded-sm"></div>
                <div className="flex flex-col">
                  <span className="font-mono-label text-[10px] text-on-surface">ALPHA-GEN-7</span>
                  <span className="text-[9px] text-tertiary">SYNCED</span>
                </div>
              </div>
              <div className="bg-surface-container-low border border-outline-variant p-2 flex items-center gap-3">
                <div className="w-3 h-3 bg-primary rounded-sm animate-pulse"></div>
                <div className="flex flex-col">
                  <span className="font-mono-label text-[10px] text-on-surface">RISK-ENGINE</span>
                  <span className="text-[9px] text-primary">PROCESSING</span>
                </div>
              </div>
              <div className="bg-surface-container-low border border-outline-variant p-2 flex items-center gap-3">
                <div className="w-3 h-3 bg-outline rounded-sm"></div>
                <div className="flex flex-col">
                  <span className="font-mono-label text-[10px] text-on-surface">BACKFILL-3</span>
                  <span className="text-[9px] text-outline">IDLE</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
