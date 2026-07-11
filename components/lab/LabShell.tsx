'use client';

import React, { useState } from 'react';
import { LabSidebar } from './LabSidebar';
import { LabTopBar } from './LabTopBar';
import { MQCommandPalette, type MQCommand } from '../mqds/MQCommandPalette';

interface LabShellProps {
  children: React.ReactNode;
}

export function LabShell({ children }: LabShellProps) {
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false);

  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setCommandPaletteOpen(true);
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, []);

  const commands: MQCommand[] = [
    {
      id: 'nav-command-center',
      label: 'Go to Command Center',
      description: 'Research command center workspace',
      keywords: ['command', 'center', 'research'],
      onExecute: () => {
        window.location.href = '/lab/command-center';
      }
    },
    {
      id: 'nav-chronicle',
      label: 'Go to Chronicle',
      description: 'Research timeline and events',
      keywords: ['chronicle', 'timeline', 'history'],
      onExecute: () => {
        window.location.href = '/lab/chronicle';
      }
    },
    {
      id: 'nav-experiments',
      label: 'Go to Experiments',
      description: 'Experiment registry and runs',
      keywords: ['experiments', 'runs', 'training'],
      onExecute: () => {
        window.location.href = '/lab/experiments';
      }
    },
    {
      id: 'nav-datasets',
      label: 'Go to Datasets',
      description: 'Dataset management',
      keywords: ['datasets', 'data'],
      onExecute: () => {
        window.location.href = '/lab/datasets';
      }
    },
    {
      id: 'nav-features',
      label: 'Go to Features',
      description: 'Feature store',
      keywords: ['features', 'store'],
      onExecute: () => {
        window.location.href = '/lab/features';
      }
    },
    {
      id: 'nav-validation',
      label: 'Go to Validation',
      description: 'Model validation workspace',
      keywords: ['validation', 'test'],
      onExecute: () => {
        window.location.href = '/lab/validation';
      }
    },
    {
      id: 'nav-calibration',
      label: 'Go to Calibration',
      description: 'Model calibration workspace',
      keywords: ['calibration', 'reliability'],
      onExecute: () => {
        window.location.href = '/lab/calibration';
      }
    },
    {
      id: 'nav-models',
      label: 'Go to Models',
      description: 'Model registry',
      keywords: ['models', 'registry'],
      onExecute: () => {
        window.location.href = '/lab/models';
      }
    },
    {
      id: 'nav-promotion',
      label: 'Go to Promotion',
      description: 'Model promotion pipeline',
      keywords: ['promotion', 'deploy'],
      onExecute: () => {
        window.location.href = '/lab/promotion';
      }
    },
    {
      id: 'nav-forensics',
      label: 'Go to Trade Forensics',
      description: 'Trade forensics workspace',
      keywords: ['forensics', 'trades', 'replay'],
      onExecute: () => {
        window.location.href = '/lab/trade-forensics';
      }
    }
  ];

  return (
    <div className="flex h-screen bg-[var(--color-mq-bg-primary)] overflow-hidden">
      <LabSidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <LabTopBar onOpenCommandPalette={() => setCommandPaletteOpen(true)} />
        <main className="flex-1 overflow-auto">
          {children}
        </main>
      </div>
      <MQCommandPalette
        isOpen={commandPaletteOpen}
        onClose={() => setCommandPaletteOpen(false)}
        commands={commands}
      />
    </div>
  );
}
