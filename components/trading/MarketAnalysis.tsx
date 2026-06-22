'use client';

import { Sparkles } from 'lucide-react';

/**
 * Market Analysis panel.
 *
 * Previously rendered output from an external AI service (local Claude endpoint
 * at 127.0.0.1:8085). That dependency has been removed — the panel now shows a
 * static "AI Analysis Disabled" notice. Core ML trading signals, analytics,
 * and live trading metrics remain fully operational.
 */
export default function MarketAnalysis() {
  return (
    <div className="bg-gray-900 rounded-lg p-4 border border-gray-800">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-gray-400" />
          <h3 className="text-lg font-semibold text-white">AI Market Analysis</h3>
        </div>
        <span className="text-[10px] font-bold tracking-wider px-2 py-0.5 rounded bg-yellow-900/50 text-yellow-300 border border-yellow-800">
          DISABLED
        </span>
      </div>

      <div className="flex flex-col items-center justify-center py-6 text-center">
        <Sparkles className="w-8 h-8 text-gray-600 mb-3" />
        <p className="text-gray-400 text-sm font-semibold">
          AI analysis service is currently disabled. Core ML trading signals and analytics remain fully operational.
        </p>
        <p className="text-gray-600 text-xs mt-2">
          Signal generation, model validation, performance analytics, and live trading metrics are unaffected.
        </p>
      </div>
    </div>
  );
}
