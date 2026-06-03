'use client';

import { MLSignal } from '@/lib/types/ml';
import { getDisplayName, getDisplayDescription } from '@/lib/api/ml-trading';

const directionConfig = {
  long: {
    bg: 'bg-green-500/20',
    text: 'text-green-400',
    border: 'border-green-500',
    gradient: 'from-green-500/50 via-green-500/20 to-transparent',
    icon: '↑',
  },
  short: {
    bg: 'bg-red-500/20',
    text: 'text-red-400',
    border: 'border-red-500',
    gradient: 'from-red-500/50 via-red-500/20 to-transparent',
    icon: '↓',
  },
  neutral: {
    bg: 'bg-gray-500/20',
    text: 'text-gray-400',
    border: 'border-gray-500',
    gradient: 'from-gray-500/50 via-gray-500/20 to-transparent',
    icon: '→',
  },
};

interface SignalCardProps {
  signal: MLSignal;
}

export default function SignalCard({ signal }: SignalCardProps) {
  const displayName = getDisplayName(signal.symbol);
  const displayDescription = getDisplayDescription(signal.symbol);

  if (signal.error) {
    return (
      <div className="bg-gray-900 rounded-lg p-4 border border-gray-800 transition-all duration-300 hover:border-gray-700">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h3 className="text-lg font-semibold text-white">{displayName}</h3>
            {displayDescription && (
              <p className="text-xs text-gray-500 mt-1">{displayDescription}</p>
            )}
            <span className="text-xs text-gray-500">{signal.timeframe}</span>
          </div>
        </div>
        <div className="bg-red-500/10 border border-red-500/30 rounded p-3">
          <p className="text-sm text-red-400">{signal.message || 'No model trained'}</p>
        </div>
      </div>
    );
  }

  const topFeatures = Object.entries(signal.top_features || {}).slice(0, 5);
  const config = directionConfig[signal.direction];
  const confidenceOpacity = Math.max(0.3, signal.confidence / 100);
  const borderStyle = {
    borderColor: `rgba(${
      signal.direction === 'long' ? '34, 197, 94' :
      signal.direction === 'short' ? '239, 68, 68' :
      '107, 114, 128'
    }, ${confidenceOpacity})`,
  };

  return (
    <div
      className={`bg-gray-900 rounded-lg p-5 border-2 transition-all duration-300 hover:scale-[1.02] hover:shadow-xl space-y-4 ${config.border}`}
      style={borderStyle}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <h3 className="text-xl font-bold text-white mb-1">{displayName}</h3>
          {displayDescription && (
            <p className="text-xs text-gray-500 mb-1">{displayDescription}</p>
          )}
          <span className="text-xs text-gray-500 uppercase tracking-wider">{signal.timeframe}</span>
        </div>
        <div className={`flex items-center gap-2 px-3 py-2 rounded-lg ${config.bg} border ${config.border}`}>
          <span className={`text-3xl ${config.text}`}>{config.icon}</span>
          <span className={`text-sm font-bold ${config.text} uppercase`}>
            {signal.direction}
          </span>
        </div>
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-xs text-gray-500 uppercase tracking-wider">Confidence</span>
          <span className={`text-xl font-bold ${config.text}`}>{signal.confidence}%</span>
        </div>
        <div className="w-full bg-gray-800 rounded-full h-2.5 overflow-hidden">
          <div
            className={`h-full bg-gradient-to-r ${config.gradient} transition-all duration-500`}
            style={{ width: `${signal.confidence}%` }}
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 py-2">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs text-gray-500">Price</span>
            {signal.price_live !== undefined && (
              <span className={`flex items-center gap-1 text-xs font-semibold ${signal.price_live ? 'text-green-400' : 'text-gray-500'}`}>
                <span className={`w-1.5 h-1.5 rounded-full ${signal.price_live ? 'bg-green-400' : 'bg-gray-500'}`}></span>
                {signal.price_live ? 'LIVE' : 'Delayed'}
              </span>
            )}
          </div>
          <div className="text-base font-bold text-white">
            ${signal.price.toLocaleString()}
          </div>
        </div>
        <div>
          <span className="text-xs text-gray-500">Model</span>
          <div className="text-base font-semibold text-white capitalize mt-1">
            {signal.model_type}
          </div>
        </div>
      </div>

      <div>
        <span className="text-xs text-gray-500">Market Regime</span>
        <div className="text-sm font-medium text-gray-300 mt-1 bg-gray-800/50 rounded px-2 py-1 inline-block">
          {signal.regime}
        </div>
      </div>

      {topFeatures.length > 0 && (
        <div className="pt-3 border-t border-gray-800">
          <h4 className="text-xs text-gray-500 uppercase tracking-wider mb-3">Feature Importance</h4>
          <div className="space-y-2">
            {topFeatures.map(([name, value]) => {
              const maxValue = Math.max(...topFeatures.map(([, v]) => Math.abs(v as number)));
              const width = (Math.abs(value as number) / maxValue) * 100;
              const isPositive = (value as number) >= 0;

              return (
                <div key={name} className="space-y-1">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-gray-400 truncate">{name}</span>
                    <span className={`font-mono font-semibold ml-2 ${isPositive ? 'text-green-400' : 'text-red-400'}`}>
                      {(value as number).toFixed(4)}
                    </span>
                  </div>
                  <div className="w-full bg-gray-800 rounded-full h-1.5 overflow-hidden">
                    <div
                      className={`h-full transition-all duration-300 ${isPositive ? 'bg-green-500' : 'bg-red-500'}`}
                      style={{ width: `${width}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      <div className="pt-2 border-t border-gray-800 flex items-center justify-between">
        <span className="text-xs text-gray-600">
          {new Date(signal.generated_at).toLocaleTimeString()}
        </span>
        <span className="text-xs text-gray-600">
          {new Date(signal.generated_at).toLocaleDateString()}
        </span>
      </div>
    </div>
  );
}
