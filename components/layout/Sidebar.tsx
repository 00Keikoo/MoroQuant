'use client';

import { useState } from 'react';
import { useMarketStore } from '@/lib/stores/marketStore';
import { usePrivacy } from '@/lib/stores/privacyStore';
import { TOP_FUTURES_PAIRS } from '@/lib/api/binance';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

interface NavItem {
  href: string;
  label: string;
  icon: React.ReactNode;
}

const NAV_ITEMS: NavItem[] = [
  {
    href: '/dashboard',
    label: 'Dashboard',
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
      </svg>
    ),
  },
  {
    href: '/trading',
    label: 'ML Signals',
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
      </svg>
    ),
  },
  {
    href: '/lab',
    label: 'Research Lab',
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
      </svg>
    ),
  },
  {
    href: '/trades',
    label: 'My Trades',
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
      </svg>
    ),
  },
  {
    href: '/dashboard/performance',
    label: 'Live Analytics',
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
      </svg>
    ),
  },
];

/**
 * Global Privacy Mode toggle pill.
 *
 * When enabled, sensitive monetary values across the dashboard are masked so
 * the app is safe to screen-share, screenshot, present, or stream. State
 * persists across refreshes via the privacy store.
 */
function PrivacyToggle() {
  const { isPrivacyMode, togglePrivacyMode } = usePrivacy();

  return (
    <button
      type="button"
      onClick={togglePrivacyMode}
      aria-pressed={isPrivacyMode}
      title={
        isPrivacyMode
          ? 'Privacy Mode is ON — balances and PnL are hidden. Click to show values.'
          : 'Privacy Mode is OFF — values are visible. Click to hide balances and PnL.'
      }
      className={`w-full flex items-center justify-center gap-2 px-3 py-2 rounded-md border text-[10px] font-bold tracking-wider uppercase transition-colors cursor-pointer ${
        isPrivacyMode
          ? 'border-mq-accent/40 bg-mq-accent/10 text-mq-accent'
          : 'border-mq-panel-border bg-black/20 text-neutral-400 hover:text-white hover:border-white/10'
      }`}
    >
      <span className="text-sm leading-none">{isPrivacyMode ? '🙈' : '👁'}</span>
      <span>{isPrivacyMode ? 'Privacy: On' : 'Visible'}</span>
    </button>
  );
}

/**
 * Reusable sidebar body: branding, navigation, watchlist, footer.
 * Shared by both the desktop bar and the mobile drawer so they never drift.
 *
 * `onNavigate` is invoked after a link/button is tapped, so the mobile
 * drawer can close itself.
 */
function SidebarContent({ onNavigate }: { onNavigate?: () => void }) {
  const { pairs, selectedPair, setSelectedPair } = useMarketStore();
  const pathname = usePathname();

  return (
    <div className="flex flex-col h-full">
      {/* Logo / branding header */}
      <div className="px-5 py-4 border-b border-mq-panel-border shrink-0">
        <div className="flex items-center gap-3">
          <svg width="32" height="32" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg" className="shrink-0">
            <path d="M16 4L4 10L16 16L28 10L16 4Z" fill="#00f0ff" opacity="0.8" />
            <path d="M4 16L16 22L28 16" stroke="#00f0ff" strokeWidth="2" strokeLinecap="round" opacity="0.6" />
            <path d="M4 22L16 28L28 22" stroke="#00f0ff" strokeWidth="2" strokeLinecap="round" opacity="0.4" />
            <circle cx="16" cy="10" r="2" fill="#ffffff" />
          </svg>
          <div className="min-w-0">
            <h1 className="text-base font-extrabold text-white tracking-tight leading-none">
              MoroQuant
            </h1>
            <p className="text-[10px] text-mq-accent font-semibold tracking-wider uppercase mt-1">
              Trading Intelligence
            </p>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        {/* Navigation */}
        <div className="px-3 py-4 border-b border-mq-panel-border">
          <h2 className="text-[10px] font-bold text-neutral-500 uppercase tracking-wider mb-3 px-2">
            Navigation
          </h2>
          <nav className="space-y-1">
            {NAV_ITEMS.map((item) => {
              const isActive = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={onNavigate}
                  className={`flex items-center gap-3 px-3 py-2 rounded-md transition-all duration-200 text-sm font-semibold ${
                    isActive
                      ? 'bg-mq-accent-dim/20 text-mq-accent border border-mq-accent/30'
                      : 'text-neutral-400 hover:bg-white/[0.03] hover:text-white border border-transparent'
                  }`}
                >
                  <span className={isActive ? 'text-mq-accent' : 'text-neutral-500'}>
                    {item.icon}
                  </span>
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </nav>
        </div>

        {/* Watchlist */}
        <div className="px-3 py-4">
          <h2 className="text-[10px] font-bold text-neutral-500 uppercase tracking-wider mb-3 px-2">
            Watchlist
          </h2>
          <div className="space-y-0.5">
            {TOP_FUTURES_PAIRS.map((symbol) => {
              const pair = pairs.get(symbol);
              const isSelected = selectedPair === symbol;

              return (
                <button
                  key={symbol}
                  onClick={() => {
                    setSelectedPair(symbol);
                    onNavigate?.();
                  }}
                  className={`w-full text-left px-3 py-2 rounded-md transition-colors ${
                    isSelected
                      ? 'bg-mq-accent-dim/20 text-white border border-mq-accent/20'
                      : 'hover:bg-white/[0.03] text-neutral-400 border border-transparent'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold">
                      {symbol.replace('USDT', '/USDT')}
                    </span>
                    {pair && (
                      <span
                        className={`text-[10px] font-mono font-semibold ${
                          pair.change24h >= 0 ? 'text-mq-long' : 'text-mq-short'
                        }`}
                      >
                        {pair.change24h >= 0 ? '+' : ''}
                        {pair.change24h.toFixed(2)}%
                      </span>
                    )}
                  </div>
                  {pair && (
                    <div className="text-[10px] text-neutral-500 mt-1 font-mono">
                      ${pair.price.toLocaleString(undefined, { maximumFractionDigits: 2 })}
                    </div>
                  )}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="px-5 py-3 border-t border-mq-panel-border shrink-0 space-y-3">
        <PrivacyToggle />
        <div className="flex items-center justify-between">
          <span className="text-[10px] text-neutral-600 font-medium tracking-wider uppercase">
            MoroQuant
          </span>
          <span className="text-[10px] font-bold text-mq-accent bg-mq-accent-dim/10 px-2 py-0.5 rounded border border-mq-accent/30">
            v1.0
          </span>
        </div>
      </div>
    </div>
  );
}

export default function Sidebar() {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <>
      {/* Desktop sidebar: fixed-width bar, always visible on md+ */}
      <aside className="hidden md:flex w-[220px] bg-mq-panel border-r border-mq-panel-border shrink-0">
        <SidebarContent />
      </aside>

      {/* Mobile hamburger trigger */}
      <button
        type="button"
        aria-label="Open navigation menu"
        onClick={() => setMobileOpen(true)}
        className="md:hidden fixed top-3 left-3 z-50 p-2 rounded-md bg-mq-panel/80 backdrop-blur border border-mq-panel-border text-white hover:bg-mq-panel transition-colors"
      >
        <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
        </svg>
      </button>

      {/* Mobile drawer + backdrop */}
      {mobileOpen && (
        <div className="md:hidden fixed inset-0 z-50">
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-black/70 backdrop-blur-sm"
            onClick={() => setMobileOpen(false)}
          />
          {/* Drawer */}
          <div className="absolute inset-y-0 left-0 w-64 max-w-[80vw] bg-mq-panel border-r border-mq-panel-border shadow-2xl animate-fade-in">
            <button
              type="button"
              aria-label="Close navigation menu"
              onClick={() => setMobileOpen(false)}
              className="absolute top-3 right-3 z-10 p-1.5 rounded-md text-neutral-400 hover:text-white hover:bg-white/[0.06] transition-colors"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
            <SidebarContent onNavigate={() => setMobileOpen(false)} />
          </div>
        </div>
      )}
    </>
  );
}
