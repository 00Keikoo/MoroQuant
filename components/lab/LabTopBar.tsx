'use client';

import React from 'react';
import { usePathname } from 'next/navigation';
import { Settings, Command } from 'lucide-react';
import { MQSearch } from '../mqds/MQSearch';
import { MQIconButton } from '../mqds/MQIconButton';

interface LabTopBarProps {
  onOpenCommandPalette: () => void;
}

const routeTitles: Record<string, string> = {
  '/lab': 'MoroQuant Lab',
  '/lab/command-center': 'Research Command Center',
  '/lab/chronicle': 'Research Chronicle',
  '/lab/experiments': 'Experiments',
  '/lab/datasets': 'Datasets',
  '/lab/features': 'Features',
  '/lab/validation': 'Validation',
  '/lab/calibration': 'Calibration',
  '/lab/models': 'Models',
  '/lab/promotion': 'Promotion',
  '/lab/trade-forensics': 'Trade Forensics'
};

export function LabTopBar({ onOpenCommandPalette }: LabTopBarProps) {
  const pathname = usePathname();
  const title = routeTitles[pathname] || 'MoroQuant Lab';

  return (
    <header className="h-[var(--header-height)] border-b border-[var(--color-mq-border)] bg-[var(--color-mq-bg-secondary)] flex items-center px-4 gap-4">
      <h1 className="text-[var(--font-size-body)] font-medium text-[var(--color-mq-text-primary)] min-w-[200px]">
        {title}
      </h1>
      <div className="flex-1 max-w-md">
        <MQSearch
          placeholder="Search / Ctrl+K"
          onClick={onOpenCommandPalette}
          readOnly
          className="cursor-pointer"
        />
      </div>
      <div className="ml-auto flex items-center gap-2">
        <MQIconButton
          icon={<Command size={16} />}
          label="Command palette (Ctrl+K)"
          onClick={onOpenCommandPalette}
        />
        <MQIconButton
          icon={<Settings size={16} />}
          label="Settings"
          onClick={() => {}}
        />
      </div>
    </header>
  );
}
