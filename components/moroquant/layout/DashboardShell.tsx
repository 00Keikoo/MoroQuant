import React, { ReactNode } from 'react';
import Sidebar from '@/components/layout/Sidebar';
import StatusBadge from '../ui/StatusBadge';

interface DashboardShellProps {
  title?: string;
  subtitle?: string;
  isRefreshing?: boolean;
  onRefresh?: () => void;
  lastUpdated?: string | null;
  children: ReactNode;
}

export default function DashboardShell({
  title = 'MoroQuant Terminal',
  subtitle = 'Institutional Quantitative Trading Interface',
  isRefreshing = false,
  onRefresh,
  lastUpdated,
  children,
}: DashboardShellProps) {
  return (
    <div className="flex h-screen bg-mq-bg text-white font-sans overflow-hidden">
      {/* Sidebar navigation */}
      <Sidebar />

      {/* Main content container */}
      <div className="flex-1 flex flex-col overflow-hidden">
        
        {/* Top Premium Header Bar */}
        <header className="h-16 border-b border-mq-panel-border bg-mq-panel/50 backdrop-blur-md px-6 flex items-center justify-between z-10 shrink-0">
          <div className="flex items-center gap-4">
            <div>
              <h2 className="text-lg font-bold tracking-wider text-white uppercase">{title}</h2>
              <p className="text-[10px] text-mq-muted font-medium mt-0.5">{subtitle}</p>
            </div>
            <div className="flex items-center">
              <StatusBadge status="LIVE" />
            </div>
          </div>

          <div className="flex items-center gap-4">
            {lastUpdated && (
              <span className="text-[10px] text-mq-muted font-mono hidden sm:inline">
                Last Sync: {lastUpdated}
              </span>
            )}
            
            {onRefresh && (
              <button
                onClick={onRefresh}
                disabled={isRefreshing}
                className="px-3 py-1.5 bg-neutral-900 border border-neutral-800 hover:border-mq-accent/40 text-xs font-semibold rounded-md hover:bg-neutral-800 transition-all duration-200 flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
              >
                <svg
                  className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin text-mq-accent' : 'text-neutral-400'}`}
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  viewBox="0 0 24 24"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99" />
                </svg>
                {isRefreshing ? 'Syncing...' : 'Refresh'}
              </button>
            )}
          </div>
        </header>

        {/* Content Area with scrollable inner content */}
        <main className="flex-1 overflow-y-auto p-6 bg-gradient-to-b from-black via-mq-bg to-black">
          <div className="max-w-7xl mx-auto space-y-6">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
