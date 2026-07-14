'use client';

import { ReactNode } from 'react';
import Link from 'next/link';

interface TradingTopBarProps {
  title?: string;
  children?: ReactNode;
  showSearch?: boolean;
  searchPlaceholder?: string;
  showKillSwitch?: boolean;
}

export function TradingTopBar({
  title = 'MoroQuant OS',
  children,
  showSearch = true,
  searchPlaceholder = 'Search...',
  showKillSwitch = true
}: TradingTopBarProps) {
  return (
    <header className="fixed top-0 left-0 right-0 h-12 w-full border-b border-outline-variant bg-surface-dim flex justify-between items-center px-4 z-50">
      <div className="flex items-center gap-6">
        <Link
          href="/dashboard"
          className="text-on-surface-variant hover:text-primary transition-colors"
          title="Back to Dashboard"
        >
          <span className="material-symbols-outlined text-[20px]">arrow_back</span>
        </Link>
        <span className="font-header-md text-header-md font-black text-primary uppercase tracking-tighter">{title}</span>
        {showSearch && (
          <div className="flex items-center bg-surface-container-low px-2 py-1 rounded-sm border border-outline-variant">
            <span className="material-symbols-outlined text-on-surface-variant text-[16px] mr-2">search</span>
            <input
              className="bg-transparent border-none focus:ring-0 text-mono-data font-mono-data w-64 placeholder:text-on-surface-variant/40"
              placeholder={searchPlaceholder}
              type="text"
            />
          </div>
        )}
        {children}
      </div>
      <div className="flex items-center gap-4">
        {showKillSwitch && (
          <button className="bg-error-container text-on-error-container font-label-caps text-label-caps px-3 py-1 rounded-sm border border-error hover:opacity-80 transition-opacity">
            KILL SWITCH
          </button>
        )}
      </div>
    </header>
  );
}
