'use client';

import { useQuery } from '@tanstack/react-query';
import { getExecutionAnalytics, getResearchSummary } from '@/lib/services/terminalService';
import { useTradingMode } from '@/lib/hooks/useTradingMode';

export default function ModelIntelligence() {
  const { mode } = useTradingMode();

  const { data: executionData } = useQuery({
    queryKey: ['terminal-execution-analytics', mode],
    queryFn: () => getExecutionAnalytics(mode || 'OFF'),
    enabled: mode !== null && mode !== 'OFF',
    refetchInterval: 30000,
  });

  const { data: researchSummary } = useQuery({
    queryKey: ['terminal-research-summary', mode],
    queryFn: () => getResearchSummary(mode || 'OFF'),
    enabled: mode !== null && mode !== 'OFF',
    refetchInterval: 30000,
  });

  const getStatusColor = (value: number, goodThreshold: number, warningThreshold: number) => {
    if (value >= goodThreshold) return 'text-green-500';
    if (value >= warningThreshold) return 'text-yellow-500';
    return 'text-red-500';
  };

  const getStatusIcon = (value: number, goodThreshold: number, warningThreshold: number) => {
    if (value >= goodThreshold) return '🟢';
    if (value >= warningThreshold) return '🟡';
    return '🔴';
  };

  const confidenceAvg = researchSummary?.confidence_avg || 0;
  const activeSignals = researchSummary?.active_signals || 0;
  const eqs = executionData?.avg_eqs || 0;

  return (
    <div className="bg-[#141414] border border-[#262626] rounded-sm p-4">
      <div className="text-xs font-bold text-[#666666] tracking-wider mb-3">MODEL INTELLIGENCE</div>

      <div className="space-y-3">
        <div className="pb-3 border-b border-[#262626]">
          <div className="text-xs text-[#666666] mb-1">Current Model</div>
          <div className="text-sm font-mono text-white font-bold">BTCUSDT_1H_XGB_v1.3</div>
        </div>

        <div>
          <div className="flex justify-between items-center mb-1">
            <span className="text-xs text-[#666666]">Prediction Confidence</span>
            <span className={`text-sm font-mono font-bold ${getStatusColor(confidenceAvg * 100, 60, 50)}`}>
              {(confidenceAvg * 100).toFixed(1)}%
            </span>
          </div>
          <div className="w-full h-1.5 bg-[#0e0e0e] rounded-sm overflow-hidden">
            <div
              className={`h-full transition-all ${confidenceAvg >= 0.6 ? 'bg-green-500' : confidenceAvg >= 0.5 ? 'bg-yellow-500' : 'bg-red-500'}`}
              style={{ width: `${Math.min(100, confidenceAvg * 100)}%` }}
            />
          </div>
        </div>

        <div>
          <div className="flex justify-between items-center mb-1">
            <span className="text-xs text-[#666666]">Active Signals</span>
            <span className="text-sm font-mono text-white">{activeSignals}</span>
          </div>
          <div className="w-full h-1.5 bg-[#0e0e0e] rounded-sm overflow-hidden">
            <div
              className="h-full bg-[#FF6B00] transition-all"
              style={{ width: `${Math.min(100, (activeSignals / 10) * 100)}%` }}
            />
          </div>
        </div>

        <div className="flex justify-between items-center">
          <span className="text-xs text-[#666666]">Market Regime</span>
          <span className="text-xs font-mono px-2 py-1 bg-green-500/20 text-green-500 border border-green-500/30 rounded">
            🟢 TRENDING_UP
          </span>
        </div>

        <div className="flex justify-between items-center">
          <span className="text-xs text-[#666666]">Model Drift</span>
          <span className="text-xs font-mono text-green-500">
            {getStatusIcon(95, 90, 80)} LOW (0.12)
          </span>
        </div>

        <div>
          <div className="flex justify-between items-center mb-1">
            <span className="text-xs text-[#666666]">Execution Quality</span>
            <span className={`text-sm font-mono font-bold ${getStatusColor(eqs * 100, 70, 50)}`}>
              {(eqs * 100).toFixed(0)}%
            </span>
          </div>
          <div className="w-full h-1.5 bg-[#0e0e0e] rounded-sm overflow-hidden">
            <div
              className={`h-full transition-all ${eqs >= 0.7 ? 'bg-green-500' : eqs >= 0.5 ? 'bg-yellow-500' : 'bg-red-500'}`}
              style={{ width: `${Math.min(100, eqs * 100)}%` }}
            />
          </div>
        </div>

        <div className="flex justify-between items-center">
          <span className="text-xs text-[#666666]">Risk Score</span>
          <span className="text-xs font-mono text-yellow-500">
            🟡 MEDIUM (0.45)
          </span>
        </div>

        <div className="pt-2 border-t border-[#262626]">
          <div className="text-xs text-[#666666] mb-2">Model Health</div>
          <div className="text-sm font-mono text-white">{researchSummary?.model_health || 'unknown'}</div>
        </div>
      </div>
    </div>
  );
}
