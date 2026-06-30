'use client';

import { useState, useEffect, useCallback } from 'react';
import { AlertTriangle, Save, Power } from 'lucide-react';
import { getTradingMode, setTradingMode, emergencyStop } from '@/lib/api/ml-trading';
import type { TradingMode, TradingModeResponse } from '@/lib/types/ml';
import { useTradingModeStore } from '@/lib/stores/tradingModeStore';

const MODE_OPTIONS: { value: TradingMode; label: string; description: string }[] = [
  { value: 'OFF', label: 'OFF', description: 'No new trades, no execution' },
  { value: 'PAPER', label: 'PAPER', description: 'Paper trades only, no live orders' },
  { value: 'LIVE', label: 'LIVE', description: 'Real Binance execution' },
  { value: 'MAINTENANCE', label: 'MAINTENANCE', description: 'Monitoring only, no new trades' },
];

const MODE_COLORS: Record<TradingMode, string> = {
  OFF: 'bg-neutral-500/20 text-neutral-400 border-neutral-600/50',
  PAPER: 'bg-mq-accent/20 text-mq-accent border-mq-accent/40',
  LIVE: 'bg-mq-long/20 text-mq-long border-mq-long/40',
  MAINTENANCE: 'bg-mq-warning/20 text-mq-warning border-mq-warning/40',
};

const MODE_DOT_COLORS: Record<TradingMode, string> = {
  OFF: 'bg-neutral-500',
  PAPER: 'bg-mq-accent',
  LIVE: 'bg-mq-long animate-pulse',
  MAINTENANCE: 'bg-mq-warning',
};

export default function TradingModeManager() {
  const [currentMode, setCurrentMode] = useState<TradingModeResponse | null>(null);
  const [selectedMode, setSelectedMode] = useState<TradingMode>('OFF');
  const [saving, setSaving] = useState(false);
  const [emergencyStopping, setEmergencyStopping] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const fetchMode = useCallback(async () => {
    try {
      const data = await getTradingMode();
      setCurrentMode(data);
      setSelectedMode(data.mode);
      // Sync global store immediately
      useTradingModeStore.getState().setModeState(data.mode);
      setError(null);
    } catch {
      setError('Failed to load trading mode');
    }
  }, []);

  useEffect(() => {
    fetchMode();
  }, [fetchMode]);

  const handleSaveMode = async () => {
    if (!currentMode || selectedMode === currentMode.mode) return;

    setSaving(true);
    setError(null);
    setSuccessMsg(null);
    try {
      const result = await setTradingMode(selectedMode);
      if (result.success) {
        setSuccessMsg(`Mode changed: ${result.old_mode} → ${result.new_mode}`);
        await fetchMode();
      } else {
        setError(result.message || 'Failed to update mode');
      }
    } catch {
      setError('Failed to save trading mode');
    } finally {
      setSaving(false);
    }
  };

  const handleEmergencyStop = async () => {
    setEmergencyStopping(true);
    setError(null);
    setSuccessMsg(null);
    try {
      const result = await emergencyStop();
      if (result.success) {
        setSuccessMsg(`EMERGENCY STOP: ${result.old_mode} → OFF`);
        await fetchMode();
      } else {
        setError('Emergency stop failed');
      }
    } catch {
      setError('Emergency stop failed');
    } finally {
      setEmergencyStopping(false);
    }
  };

  return (
    <div className="glass-card p-4 flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-white tracking-wide uppercase">
          Autonomous Trading
        </h3>
        {currentMode && (
          <span
            className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[10px] font-bold tracking-wider border ${MODE_COLORS[currentMode.mode]}`}
          >
            <span className={`h-1.5 w-1.5 rounded-full ${MODE_DOT_COLORS[currentMode.mode]}`} />
            {currentMode.mode}
          </span>
        )}
      </div>

      {/* Current mode info */}
      {currentMode && (
        <div className="text-xs text-gray-500">
          Last updated: {currentMode.updated_at || 'N/A'}
        </div>
      )}

      {/* Dropdown */}
      <div className="flex flex-col gap-1.5">
        <label htmlFor="trading-mode-select" className="text-xs text-gray-400 font-medium">
          Trading Mode
        </label>
        <select
          id="trading-mode-select"
          value={selectedMode}
          onChange={(e) => setSelectedMode(e.target.value as TradingMode)}
          className="w-full px-3 py-2 bg-gray-800/80 border border-gray-700 rounded-lg text-sm text-white focus:outline-none focus:border-mq-accent/50 transition-colors"
        >
          {MODE_OPTIONS.map(({ value, label, description }) => (
            <option key={value} value={value}>
              {label} – {description}
            </option>
          ))}
        </select>
      </div>

      {/* Save Mode button */}
      <button
        onClick={handleSaveMode}
        disabled={saving || !currentMode || selectedMode === currentMode.mode}
        className="flex items-center justify-center gap-2 w-full px-4 py-2 rounded-lg text-xs font-semibold transition-all duration-200
          bg-mq-accent/20 text-mq-accent border border-mq-accent/40
          hover:bg-mq-accent/30 disabled:opacity-40 disabled:cursor-not-allowed"
      >
        <Save className="w-3.5 h-3.5" />
        {saving ? 'Saving...' : 'Save Mode'}
      </button>

      {/* Emergency Stop */}
      <button
        onClick={handleEmergencyStop}
        disabled={emergencyStopping || (currentMode?.mode === 'OFF')}
        className="flex items-center justify-center gap-2 w-full px-4 py-2 rounded-lg text-xs font-bold transition-all duration-200
          bg-red-600/20 text-red-400 border border-red-500/40
          hover:bg-red-600/40 disabled:opacity-40 disabled:cursor-not-allowed"
      >
        <Power className="w-3.5 h-3.5" />
        <AlertTriangle className="w-3 h-3" />
        {emergencyStopping ? 'Stopping...' : 'EMERGENCY STOP'}
      </button>

      {/* Feedback messages */}
      {successMsg && (
        <div className="text-xs text-mq-accent bg-mq-accent/10 border border-mq-accent/20 rounded-lg px-3 py-2">
          {successMsg}
        </div>
      )}
      {error && (
        <div className="text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">
          {error}
        </div>
      )}

      {/* Permission matrix */}
      <div className="mt-1 border-t border-gray-800 pt-3">
        <div className="text-[10px] text-gray-500 font-semibold uppercase tracking-wider mb-2">
          Permission Matrix
        </div>
        <div className="grid grid-cols-2 gap-2 text-xs">
          <PermissionRow
            label="Open New Positions"
            allowed={
              currentMode?.mode === 'PAPER' || currentMode?.mode === 'LIVE'
            }
          />
          <PermissionRow
            label="Live Execution"
            allowed={currentMode?.mode === 'LIVE'}
          />
        </div>
      </div>
    </div>
  );
}

function PermissionRow({ label, allowed }: { label: string; allowed: boolean }) {
  return (
    <div className="flex items-center justify-between bg-gray-900/40 rounded-md px-2.5 py-1.5">
      <span className="text-gray-400">{label}</span>
      <span className={`text-[10px] font-bold ${allowed ? 'text-mq-long' : 'text-red-400/70'}`}>
        {allowed ? 'ALLOWED' : 'BLOCKED'}
      </span>
    </div>
  );
}
