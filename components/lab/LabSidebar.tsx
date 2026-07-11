'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  Beaker,
  Database,
  Cpu,
  Target,
  TrendingUp,
  Clock,
  ArrowUpCircle,
  Zap,
  LayoutDashboard,
  Table
} from 'lucide-react';

interface NavItem {
  id: string;
  label: string;
  icon: React.ReactNode;
  href: string;
  shortcut?: string;
}

const navItems: NavItem[] = [
  {
    id: 'command-center',
    label: 'Command Center',
    icon: <LayoutDashboard size={20} />,
    href: '/lab/command-center',
    shortcut: 'G+C'
  },
  {
    id: 'chronicle',
    label: 'Chronicle',
    icon: <Table size={20} />,
    href: '/lab/chronicle',
    shortcut: 'G+H'
  },
  {
    id: 'experiments',
    label: 'Experiments',
    icon: <Beaker size={20} />,
    href: '/lab/experiments',
    shortcut: 'G+E'
  },
  {
    id: 'datasets',
    label: 'Datasets',
    icon: <Database size={20} />,
    href: '/lab/datasets',
    shortcut: 'G+D'
  },
  {
    id: 'features',
    label: 'Features',
    icon: <Cpu size={20} />,
    href: '/lab/features',
    shortcut: 'G+F'
  },
  {
    id: 'validation',
    label: 'Validation',
    icon: <Target size={20} />,
    href: '/lab/validation',
    shortcut: 'G+V'
  },
  {
    id: 'calibration',
    label: 'Calibration',
    icon: <TrendingUp size={20} />,
    href: '/lab/calibration',
    shortcut: 'G+L'
  },
  {
    id: 'models',
    label: 'Models',
    icon: <Clock size={20} />,
    href: '/lab/models',
    shortcut: 'G+M'
  },
  {
    id: 'promotion',
    label: 'Promotion',
    icon: <ArrowUpCircle size={20} />,
    href: '/lab/promotion',
    shortcut: 'G+P'
  },
  {
    id: 'forensics',
    label: 'Trade Forensics',
    icon: <Zap size={20} />,
    href: '/lab/trade-forensics',
    shortcut: 'G+T'
  }
];

export function LabSidebar() {
  const pathname = usePathname();

  return (
    <nav
      className="w-[var(--rail-width)] bg-[var(--color-mq-bg-secondary)] border-r border-[var(--color-mq-border)] flex flex-col"
      aria-label="Lab navigation"
    >
      <div className="flex items-center justify-center h-[var(--header-height)] border-b border-[var(--color-mq-border)]">
        <span className="text-[var(--font-size-header)] font-bold text-[var(--color-mq-accent)]">
          MQ
        </span>
      </div>
      <div className="flex-1 overflow-y-auto py-2">
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.id}
              href={item.href}
              className={`flex items-center justify-center h-12 transition-colors group relative ${
                isActive
                  ? 'text-[var(--color-mq-accent)] bg-[var(--color-mq-accent-dim)]'
                  : 'text-[var(--color-mq-text-secondary)] hover:text-[var(--color-mq-accent)] hover:bg-[var(--color-mq-accent-dim)]'
              }`}
              aria-label={item.label}
              title={`${item.label}${item.shortcut ? ` (${item.shortcut})` : ''}`}
            >
              {item.icon}
              {isActive && (
                <div className="absolute left-0 top-0 bottom-0 w-1 bg-[var(--color-mq-accent)]" />
              )}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
