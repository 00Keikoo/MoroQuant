import React, { ReactNode } from 'react';

interface SectionPanelProps {
  title: string;
  subtitle?: string;
  loading?: boolean;
  error?: string | null;
  empty?: string;
  actions?: ReactNode;
  children: ReactNode;
}

export default function SectionPanel({
  title,
  subtitle,
  loading = false,
  error = null,
  empty,
  actions,
  children,
}: SectionPanelProps) {
  return (
    <div className="bg-mq-panel border border-mq-panel-border rounded-lg flex flex-col overflow-hidden relative group">
      {/* Accent strip on hover */}
      <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-mq-accent/40 via-mq-accent/10 to-transparent opacity-0 group-hover:opacity-100 transition-all duration-500" />
      
      {/* Header bar */}
      <div className="flex items-center justify-between p-4 border-b border-mq-panel-border bg-black/40">
        <div className="flex items-baseline gap-2">
          <h3 className="text-sm font-bold text-white tracking-wider uppercase">{title}</h3>
          {subtitle && (
            <span className="text-[10px] text-neutral-400 font-mono font-medium">{subtitle}</span>
          )}
        </div>
        {actions && <div className="flex items-center gap-2">{actions}</div>}
      </div>

      {/* Content Area */}
      <div className="flex-1 p-4 relative min-h-[120px]">
        {loading && (
          <div className="absolute inset-0 bg-mq-panel/85 flex flex-col items-center justify-center z-10">
            <div className="w-6 h-6 border-2 border-mq-accent/20 border-t-mq-accent rounded-full animate-spin mb-2" />
            <span className="text-xs text-neutral-400 font-medium">Loading data...</span>
          </div>
        )}

        {error && (
          <div className="absolute inset-0 bg-mq-panel/95 flex flex-col items-center justify-center p-4 z-10 text-center">
            <svg className="w-8 h-8 text-mq-short mb-2" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <span className="text-xs text-mq-short font-bold mb-1">Component Load Error</span>
            <span className="text-[10px] text-neutral-400 max-w-xs">{error}</span>
          </div>
        )}

        {!loading && !error && empty && (
          <div className="absolute inset-0 flex flex-col items-center justify-center p-4 text-center">
            <svg className="w-8 h-8 text-neutral-600 mb-2" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 13.5h3.86a2.25 2.25 0 012.008 1.24l.885 1.77a2.25 2.25 0 002.007 1.24h1.98a2.25 2.25 0 002.007-1.24l.885-1.77a2.25 2.25 0 012.007-1.24h3.86m-18 0h18" />
            </svg>
            <span className="text-xs text-neutral-400 font-medium">{empty}</span>
          </div>
        )}

        {/* Regular slot content */}
        <div className={loading || error ? 'invisible opacity-0' : 'visible opacity-100 transition-opacity duration-300'}>
          {children}
        </div>
      </div>
    </div>
  );
}
