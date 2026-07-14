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
              <img className="w-8 h-8 rounded-sm grayscale border border-outline-variant" src="https://lh3.googleusercontent.com/aida-public/AB6AXuBehrVY3GJoV55SrLHKd7d3VMGxk8Y2Op91_2yaJrmgwukQCQef8iCfnvQn5L6vPlXS1bftRBzvVeL0RiNCkJ83u3BnyK6ZmSGYgBQt_fLFU2dIvt_PN82ur4SUuaVTLbd28KiijQZdWIPI7G2BUg9QPQFDYdUtcwOUZOhBa7l0n6HTT2hnh4zeDzIByjAWJqy_e0XQrLZu_W0BdA-ggyEXBbAt7f1b7hoqlspJ33ITgSYKKZ9-IYxEQ7yMtu3nQZ6oIWRF4QA53p0" alt="A professional high-contrast portrait of a technical system operator profile, rendered in a sharp, minimalist corporate style with dark charcoal backgrounds and subtle orange accent lighting. The image is clean, sharp, and focused, echoing the institucional technical aesthetic of a high-end quantitative trading firm."/>
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
          <div className="flex-1 overflow-y-auto p-4 space-y-6">
            <section>
              <div className="text-[10px] font-mono-label text-outline uppercase mb-3 tracking-widest border-b border-outline-variant/30 pb-1">Position Details</div>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="font-mono-label text-mono-label text-on-surface-variant">ENTRY PRICE</span>
                  <span className="font-mono-data text-mono-data text-on-surface">3,492.15</span>
                </div>
                <div className="flex justify-between">
                  <span className="font-mono-label text-mono-label text-on-surface-variant">MARK PRICE</span>
                  <span className="font-mono-data text-mono-data text-on-surface">3,501.10</span>
                </div>
                <div className="flex justify-between">
                  <span className="font-mono-label text-mono-label text-on-surface-variant">LIQ PRICE</span>
                  <span className="font-mono-data text-mono-data text-error">2,912.45</span>
                </div>
                <div className="flex justify-between">
                  <span className="font-mono-label text-mono-label text-on-surface-variant">LEVERAGE</span>
                  <span className="font-mono-data text-mono-data text-on-surface">5.0x (ISOLATED)</span>
                </div>
                <div className="flex justify-between">
                  <span className="font-mono-label text-mono-label text-on-surface-variant">FUNDING RATE</span>
                  <span className="font-mono-data text-mono-data text-tertiary">0.01% / 8H</span>
                </div>
              </div>
            </section>
            <section>
              <div className="text-[10px] font-mono-label text-outline uppercase mb-3 tracking-widest border-b border-outline-variant/30 pb-1">Order Execution</div>
              <div className="grid grid-cols-2 gap-2 mb-4">
                <button className="bg-tertiary text-on-tertiary font-mono-label text-mono-label py-2 rounded-sm font-bold">CLOSE LONG</button>
                <button className="bg-primary text-on-primary font-mono-label text-mono-label py-2 rounded-sm font-bold">CLOSE SHORT</button>
              </div>
              <div className="bg-black border border-outline-variant p-2 space-y-3">
                <div>
                  <label className="text-[9px] font-mono-label text-outline uppercase block mb-1">Stop Loss</label>
                  <div className="flex gap-1">
                    <input className="flex-1 bg-surface-container border border-outline-variant text-mono-data text-on-surface px-2 py-1 focus:ring-1 focus:ring-primary focus:outline-none" type="text" value="3,410.00"/>
                    <button className="px-3 border border-outline-variant text-[10px] font-mono-label">SET</button>
                  </div>
                </div>
                <div>
                  <label className="text-[9px] font-mono-label text-outline uppercase block mb-1">Take Profit</label>
                  <div className="flex gap-1">
                    <input className="flex-1 bg-surface-container border border-outline-variant text-mono-data text-on-surface px-2 py-1 focus:ring-1 focus:ring-primary focus:outline-none" type="text" value="3,850.00"/>
                    <button className="px-3 border border-outline-variant text-[10px] font-mono-label">SET</button>
                  </div>
                </div>
              </div>
            </section>
            <section>
              <div className="text-[10px] font-mono-label text-outline uppercase mb-3 tracking-widest border-b border-outline-variant/30 pb-1">Visualizer</div>
              <div className="h-32 bg-black border border-outline-variant relative overflow-hidden">
                <div className="absolute inset-0 flex items-center justify-center">
                  <span className="text-[10px] font-mono-label text-outline opacity-30">CANDLE_ENGINE_V2</span>
                </div>
                <div className="absolute bottom-0 w-full h-1/2 bg-gradient-to-t from-primary/10 to-transparent"></div>
                <div className="absolute top-1/2 left-0 w-full h-px bg-primary/40 border-t border-dashed border-primary/60"></div>
                <div className="absolute bottom-1/4 left-0 w-full h-px bg-error/40 border-t border-dashed border-error/60"></div>
              </div>
            </section>
          </div>
        </aside>
      </div>

      <footer className="fixed bottom-0 left-0 right-0 z-50 flex items-center justify-between px-4 py-1 bg-surface-container-lowest border-t border-outline-variant h-8 flex-shrink-0">
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
