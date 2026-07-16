'use client';

import { useTradingMode } from '@/lib/hooks/useTradingMode';
import { setTradingMode } from '@/lib/api/ml-trading';
import { TradingMode } from '@/lib/types/ml';

export default function TradingModeSwitch() {
  const { mode, loading, refresh } = useTradingMode();

  const handleModeChange = async (newMode: TradingMode) => {
    if (newMode === mode) return;
    try {
      await setTradingMode(newMode);
      await refresh();
    } catch (error) {
      console.error('Failed to change trading mode:', error);
    }
  };

  const modeConfig: Record<'LIVE' | 'PAPER' | 'OFF', {
    label: string;
    color: string;
    bgActive: string;
    borderActive: string;
    desc: string;
  }> = {
    LIVE: {
      label: 'LIVE',
      color: 'text-red-500',
      bgActive: 'bg-red-500/20',
      borderActive: 'border-red-500',
      desc: 'Real trading',
    },
    PAPER: {
      label: 'PAPER',
      color: 'text-green-500',
      bgActive: 'bg-green-500/20',
      borderActive: 'border-green-500',
      desc: 'Paper trading',
    },
    OFF: {
      label: 'OFF',
      color: 'text-gray-500',
      bgActive: 'bg-gray-500/20',
      borderActive: 'border-gray-500',
      desc: 'Trading disabled',
    },
  };

  return (
    <div className="flex items-center gap-1 bg-[#141414] border border-[#262626] rounded-sm p-1">
      {(['LIVE', 'PAPER', 'OFF'] as const).map((m) => {
        const config = modeConfig[m];
        const isActive = mode === m;

        return (
          <button
            key={m}
            onClick={() => handleModeChange(m)}
            disabled={loading}
            className={`
              relative px-4 py-1.5 text-xs font-bold tracking-wider transition-all
              ${isActive ? config.color : 'text-[#666666]'}
              ${isActive ? config.bgActive : 'hover:bg-[#1C1C1C]'}
              ${isActive ? `border ${config.borderActive}` : 'border border-transparent'}
              rounded-sm font-mono
              disabled:opacity-50 disabled:cursor-not-allowed
            `}
            title={config.desc}
          >
            {isActive && (
              <span className="absolute left-2 top-1/2 -translate-y-1/2 w-1.5 h-1.5 rounded-full bg-current animate-pulse" />
            )}
            <span className={isActive ? 'ml-2' : ''}>{config.label}</span>
          </button>
        );
      })}
    </div>
  );
}
