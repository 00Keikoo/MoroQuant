'use client';

export default function DashboardPageShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="h-screen flex flex-col">
      <header className="flex items-center justify-between px-container-padding w-full border-b border-outline-variant bg-surface h-12 flex-shrink-0">
        <div className="flex items-center gap-6">
          <div className="font-headline-sm text-headline-sm font-bold text-primary">MoroQuant</div>
          <div className="hidden md:flex items-center gap-4">
            <div className="relative group h-full flex items-center">
              <span className="font-mono-data text-mono-data text-primary cursor-pointer">Nominal</span>
              <div className="absolute bottom-0 left-0 w-full h-0.5 bg-primary"></div>
            </div>
            <div className="h-4 w-px bg-outline-variant"></div>
            <div className="flex items-center gap-3">
              <span className="font-mono-label text-mono-label text-on-surface-variant uppercase">Market:</span>
              <span className="font-mono-data text-mono-data text-on-surface">BTC/USD $64,231.12</span>
              <span className="font-mono-data text-mono-data text-tertiary">+1.24%</span>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center bg-surface-container-low border border-outline-variant px-3 py-1 rounded">
            <span className="material-symbols-outlined text-on-surface-variant text-sm mr-2">search</span>
            <input className="bg-transparent border-none focus:ring-0 text-mono-data text-on-surface w-48 placeholder:text-on-surface-variant" placeholder="CMD+K TO SEARCH" type="text"/>
          </div>
          <button className="bg-primary-container text-on-primary-container font-mono-label text-mono-label px-4 py-1.5 rounded-sm hover:opacity-90 transition-opacity">Deploy</button>
          <button className="border border-error text-error font-mono-label text-mono-label px-4 py-1.5 rounded-sm hover:bg-error/10 transition-colors">Emergency Kill Switch</button>
          <span className="material-symbols-outlined text-on-surface cursor-pointer">account_circle</span>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        <nav className="flex flex-col h-full border-r border-outline-variant bg-background w-64 flex-shrink-0">
          <div className="flex-1 overflow-y-auto scrollbar-hide py-2">
            <div className="flex flex-col">
              <div className="text-primary font-bold border-l-2 border-primary bg-surface-container-high px-4 py-2 flex items-center gap-3 transition-colors duration-75">
                <span className="material-symbols-outlined text-[18px]">dashboard</span>
                <span className="font-mono-label text-mono-label">Dashboard</span>
              </div>
              <div className="text-on-surface-variant hover:bg-surface-variant hover:text-primary px-4 py-2 flex items-center gap-3 cursor-pointer transition-colors duration-75">
                <span className="material-symbols-outlined text-[18px]">monitoring</span>
                <span className="font-mono-label text-mono-label">Live Analytics</span>
              </div>
              <div className="text-on-surface-variant hover:bg-surface-variant hover:text-primary px-4 py-2 flex items-center gap-3 cursor-pointer transition-colors duration-75">
                <span className="material-symbols-outlined text-[18px]">sensors</span>
                <span className="font-mono-label text-mono-label">Signals</span>
              </div>
              <div className="text-on-surface-variant hover:bg-surface-variant hover:text-primary px-4 py-2 flex items-center gap-3 cursor-pointer transition-colors duration-75">
                <span className="material-symbols-outlined text-[18px]">swap_horiz</span>
                <span className="font-mono-label text-mono-label">Trades</span>
              </div>
              <div className="text-on-surface-variant hover:bg-surface-variant hover:text-primary px-4 py-2 flex items-center gap-3 cursor-pointer transition-colors duration-75">
                <span className="material-symbols-outlined text-[18px]">pie_chart</span>
                <span className="font-mono-label text-mono-label">Portfolio</span>
              </div>
              <div className="text-on-surface-variant hover:bg-surface-variant hover:text-primary px-4 py-2 flex items-center gap-3 cursor-pointer transition-colors duration-75">
                <span className="material-symbols-outlined text-[18px]">security</span>
                <span className="font-mono-label text-mono-label">Risk</span>
              </div>
              <div className="mt-4 px-4 py-1 text-[10px] text-outline uppercase font-bold tracking-widest">Infrastructure</div>
              <div className="text-on-surface-variant hover:bg-surface-variant hover:text-primary px-4 py-2 flex items-center gap-3 cursor-pointer transition-colors duration-75">
                <span className="material-symbols-outlined text-[18px]">terminal</span>
                <span className="font-mono-label text-mono-label">Command Center</span>
              </div>
              <div className="text-on-surface-variant hover:bg-surface-variant hover:text-primary px-4 py-2 flex items-center gap-3 cursor-pointer transition-colors duration-75">
                <span className="material-symbols-outlined text-[18px]">database</span>
                <span className="font-mono-label text-mono-label">Datasets</span>
              </div>
              <div className="text-on-surface-variant hover:bg-surface-variant hover:text-primary px-4 py-2 flex items-center gap-3 cursor-pointer transition-colors duration-75">
                <span className="material-symbols-outlined text-[18px]">view_in_ar</span>
                <span className="font-mono-label text-mono-label">Model Registry</span>
              </div>
            </div>
          </div>
          <div className="p-4 border-t border-outline-variant bg-surface-container-low">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-8 h-8 rounded-sm grayscale border border-outline-variant bg-surface-container"></div>
              <div className="flex flex-col">
                <span className="font-mono-label text-mono-label text-on-surface">Worker ID 742</span>
                <span className="text-[9px] text-tertiary">LVL 4 ACCESS</span>
              </div>
            </div>
            <div className="text-on-surface-variant hover:text-primary flex items-center gap-2 cursor-pointer transition-colors">
              <span className="material-symbols-outlined text-[16px]">settings</span>
              <span className="font-mono-label text-mono-label">Settings</span>
            </div>
          </div>
        </nav>

        <main className="flex-1 flex flex-col overflow-hidden bg-background">
          {children}
        </main>

        <aside className="hidden xl:flex w-80 border-l border-outline-variant bg-surface flex-col flex-shrink-0">
          <div className="p-4 border-b border-outline-variant bg-surface-container">
            <div className="flex justify-between items-center mb-1">
              <span className="font-mono-label text-mono-label uppercase text-on-surface font-bold">Inspector</span>
              <span className="material-symbols-outlined text-on-surface-variant cursor-pointer text-sm">close</span>
            </div>
            <div className="font-mono-data text-mono-data text-tertiary">ETH-USDT-PERP</div>
          </div>
          <div className="flex-1 overflow-y-auto p-4">
            <div className="h-full bg-surface-container border border-outline-variant flex items-center justify-center">
              <span className="text-outline font-mono-label text-mono-label">INSPECTOR CONTENT</span>
            </div>
          </div>
        </aside>
      </div>

      <footer className="flex items-center justify-between px-4 py-1 bg-surface-container-lowest border-t border-outline-variant h-8 flex-shrink-0">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-tertiary"></div>
            <span className="font-mono-label text-mono-label text-tertiary">Real-time Telemetry: GPU 42% | Latency 1.2ms | System Nominal</span>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-4">
            <span className="font-mono-label text-mono-label text-on-surface-variant hover:text-primary cursor-pointer transition-opacity">Logs</span>
            <span className="font-mono-label text-mono-label text-on-surface-variant hover:text-primary cursor-pointer transition-opacity">Workers</span>
            <span className="font-mono-label text-mono-label text-on-surface-variant hover:text-primary cursor-pointer transition-opacity">Scheduler</span>
          </div>
          <div className="h-4 w-px bg-outline-variant"></div>
          <span className="font-mono-label text-mono-label text-on-surface-variant">V2.4.0-STABLE</span>
        </div>
      </footer>
    </div>
  );
}
