'use client';

import React from 'react';

interface PerformanceHeaderProps {
  lastUpdated: string | null;
  isRefreshing: boolean;
  onRefresh: () => void;
  autoRefreshSeconds?: number;
}

/**
 * Top header bar for the performance page.
 * Shows last updated timestamp, auto-refresh cadence, LIVE badge, and manual refresh button.
 */
export default function PerformanceHeader({
  lastUpdated,
  isRefreshing,
  onRefresh,
  autoRefreshSeconds = 30,
}: PerformanceHeaderProps) {
  const formattedTime = lastUpdated
    ? new Date(lastUpdated).toLocaleTimeString(undefined, {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false,
      })
    : '—';

  return (
    <header className="h-16 border-b border-mq-panel-border bg-mq-panel/50 backdrop-blur-md px-6 flex items-center justify-between z-10 shrink-0">
      <div className="flex items-center gap-4">
        <div>
          <h2 className="text-lg font-bold tracking-wider text-white uppercase">
            Live Trading Performance
          </h2>
          <p className="text-[10px] text-mq-muted font-medium mt-0.5">
            Real-time analytics · Production metrics
          </p>
        </div>
      </div>

      <div className="flex items-center gap-4">
        {/* Last updated */}
        <div className="hidden md:flex flex-col items-end">
          <span className="text-[10px] text-neutral-500 uppercase tracking-wider">
            Last Updated
          </span>
          <span className="text-xs text-neutral-300 font-mono">
            {formattedTime}
            {lastUpdated && (
              <span className="text-neutral-600 ml-1">UTC</span>
            )}
          </span>
        </div>

        {/* Auto refresh indicator */}
        <div className="hidden lg:flex flex-col items-end">
          <span className="text-[10px] text-neutral-500 uppercase tracking-wider">
            Auto Refresh
          </span>
          <span className="text-xs text-neutral-300 font-mono">
            {autoRefreshSeconds}s
          </span>
        </div>

        {/* LIVE badge */}
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-[10px] font-bold tracking-wider bg-mq-long-dim/10 text-mq-long border border-mq-long/30">
          <span className="h-1.5 w-1.5 rounded-full bg-mq-long animate-pulse" />
          LIVE
        </span>

        {/* Refresh button */}
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
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99"
            />
          </svg>
          {isRefreshing ? 'Syncing...' : 'Refresh'}
        </button>
      </div>
    </header>
  );
}
