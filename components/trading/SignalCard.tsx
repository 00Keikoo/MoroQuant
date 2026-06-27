'use client';

import { MLSignal } from '@/lib/types/ml';
import { getDisplayName, getDisplayDescription } from '@/lib/api/ml-trading';
import { useState, useEffect } from 'react';

const directionConfig = {
  long: {
    bg: 'bg-green-500/20',
    text: 'text-green-400',
    border: 'border-green-500',
    borderGradient: 'from-green-500 via-green-400 to-green-500',
    glowColor: 'shadow-green-500/50',
    gradient: 'from-green-500 via-green-400 to-green-500',
    icon: '↑',
  },
  short: {
    bg: 'bg-red-500/20',
    text: 'text-red-400',
    border: 'border-red-500',
    borderGradient: 'from-red-500 via-red-400 to-red-500',
    glowColor: 'shadow-red-500/50',
    gradient: 'from-red-500 via-red-400 to-red-500',
    icon: '↓',
  },
  neutral: {
    bg: 'bg-gray-500/20',
    text: 'text-gray-400',
    border: 'border-gray-500',
    borderGradient: 'from-gray-500 via-gray-400 to-gray-500',
    glowColor: 'shadow-gray-500/50',
    gradient: 'from-gray-500 via-gray-400 to-gray-500',
    icon: '→',
  },
};

const statusConfig = {
  ACTIVE: {
    label: 'ACTIVE',
    bg: 'bg-emerald-500/15',
    text: 'text-emerald-400',
    border: 'border-emerald-500/40',
    icon: '●',
  },
  TP_HIT: {
    label: 'TP HIT',
    bg: 'bg-green-500/15',
    text: 'text-green-400',
    border: 'border-green-500/40',
    icon: '✓',
  },
  SL_HIT: {
    label: 'SL HIT',
    bg: 'bg-red-500/15',
    text: 'text-red-400',
    border: 'border-red-500/40',
    icon: '✕',
  },
  EXPIRED: {
    label: 'EXPIRED',
    bg: 'bg-gray-500/15',
    text: 'text-gray-400',
    border: 'border-gray-500/40',
    icon: '◷',
  },
};

const MiniSparkline = ({ data }: { data: number[] }) => {
  if (!data || data.length === 0) return null;

  const width = 100;
  const height = 30;
  const padding = 2;

  const max = Math.max(...data);
  const min = Math.min(...data);
  const range = max - min || 1;

  const points = data.map((value, index) => {
    const x = (index / (data.length - 1)) * (width - 2 * padding) + padding;
    const y = height - padding - ((value - min) / range) * (height - 2 * padding);
    return `${x},${y}`;
  }).join(' ');

  const isPositive = data[data.length - 1] >= data[0];

  return (
    <svg width={width} height={height} className="opacity-60">
      <polyline
        points={points}
        fill="none"
        stroke={isPositive ? '#22c55e' : '#ef4444'}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
};

interface SignalCardProps {
  signal: MLSignal;
}

export default function SignalCard({ signal }: SignalCardProps) {
  const displayName = getDisplayName(signal.symbol);
  const displayDescription = getDisplayDescription(signal.symbol);
  const [sparklineData, setSparklineData] = useState<number[]>([]);

  useEffect(() => {
    const generateSparkline = () => {
      const basePrice = signal.price;
      const volatility = basePrice * 0.02;
      const data = Array.from({ length: 24 }, (_, i) => {
        const trend = (i - 12) * (basePrice * 0.001);
        const noise = (Math.random() - 0.5) * volatility;
        return basePrice + trend + noise;
      });
      setSparklineData(data);
    };

    generateSparkline();
  }, [signal.price]);

  if (signal.error) {
    // Handle signal_inactive error from API
    if (signal.error === 'signal_inactive') {
      return (
        <div className="bg-gray-900/60 rounded-xl p-4 sm:p-5 border border-gray-800/50 transition-all duration-300 opacity-50">
          <div className="flex items-center justify-between mb-3">
            <div className="min-w-0 flex-1">
              <h3 className="text-base sm:text-lg font-semibold text-gray-500 truncate">{displayName}</h3>
              <span className="text-xs text-gray-600">{signal.timeframe}</span>
            </div>
            <span className="text-xs font-bold text-gray-500 bg-gray-800 px-2 py-1 rounded border border-gray-700">
              {signal.signal_status || 'INACTIVE'}
            </span>
          </div>
          <p className="text-xs text-gray-600">{signal.status_reason || signal.message}</p>
        </div>
      );
    }
    return (
      <div className="bg-gray-900 rounded-lg p-4 border border-gray-800 transition-all duration-300 hover:border-gray-700 animate-fade-in">
        <div className="flex items-center justify-between mb-3">
          <div className="min-w-0 flex-1">
            <h3 className="text-base sm:text-lg font-semibold text-white truncate">{displayName}</h3>
            {displayDescription && (
              <p className="text-xs text-gray-500 mt-1 line-clamp-2">{displayDescription}</p>
            )}
            <span className="text-xs text-gray-500">{signal.timeframe}</span>
          </div>
        </div>
        <div className="bg-red-500/10 border border-red-500/30 rounded p-3">
          <p className="text-xs sm:text-sm text-red-400">{signal.message || 'No model trained'}</p>
        </div>
      </div>
    );
  }

  const topFeatures = Object.entries(signal.top_features || {}).slice(0, 5);
  const config = directionConfig[signal.direction];
  const signalStatus = signal.signal_status || 'ACTIVE';
  const statusCfg = statusConfig[signalStatus];
  const isInactive = signalStatus !== 'ACTIVE';

  return (
    <div
      className={`relative bg-gray-900 rounded-xl p-4 sm:p-5 transition-all duration-300 hover:scale-[1.02] space-y-3 sm:space-y-4 animate-fade-in group
        before:absolute before:inset-0 before:rounded-xl before:p-[2px] before:bg-gradient-to-r before:${config.borderGradient} before:-z-10
        hover:shadow-2xl hover:${config.glowColor}
        ${isInactive ? 'opacity-40 grayscale-[30%]' : ''}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h3 className="text-lg sm:text-xl font-extrabold text-white truncate">{displayName}</h3>
            <MiniSparkline data={sparklineData} />
          </div>
          {displayDescription && (
            <p className="text-xs text-gray-500 mb-1 line-clamp-2 font-medium">{displayDescription}</p>
          )}
          <span className="text-xs text-gray-500 uppercase tracking-wider font-semibold">{signal.timeframe}</span>
        </div>
        <div className="flex flex-col items-end gap-1.5 flex-shrink-0">
          <span className={`flex items-center gap-1.5 px-2 sm:px-3 py-1.5 sm:py-2 rounded-lg ${config.bg} border-2 ${config.border}`}>
            <span className={`text-2xl sm:text-3xl ${config.text} font-bold`}>{config.icon}</span>
            <span className={`text-xs sm:text-sm font-extrabold ${config.text} uppercase tracking-wide`}>
              {signal.direction}
            </span>
          </span>
          {/* Status badge */}
          <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] sm:text-xs font-bold uppercase tracking-wider border ${statusCfg.bg} ${statusCfg.text} ${statusCfg.border}`}>
            <span>{statusCfg.icon}</span>
            {statusCfg.label}
          </span>
        </div>
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-xs text-gray-500 uppercase tracking-wider font-semibold">Confidence</span>
          <span className={`text-lg sm:text-xl font-extrabold ${config.text}`}>{signal.confidence}%</span>
        </div>
        <div className="relative w-full bg-gray-800/50 rounded-full h-3 overflow-hidden border border-gray-700">
          <div
            className={`h-full bg-gradient-to-r ${config.gradient} transition-all duration-1000 ease-out animate-pulse-slow`}
            style={{ width: `${signal.confidence}%` }}
          />
          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent animate-shimmer" />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:gap-4 py-2">
        <div>
          <div className="flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-2 mb-1">
            <span className="text-xs text-gray-500 font-semibold">Price</span>
            {signal.price_live !== undefined && (
              <span className={`flex items-center gap-1 text-xs font-bold ${signal.price_live ? 'text-green-400' : 'text-gray-500'}`}>
                <span className={`w-1.5 h-1.5 rounded-full ${signal.price_live ? 'bg-green-400 animate-pulse' : 'bg-gray-500'}`}></span>
                {signal.price_live ? 'LIVE' : (signal.symbol.endsWith('_proxy') ? 'ETF Data' : 'Delayed')}
              </span>
            )}
          </div>
          <div className="text-sm sm:text-base font-extrabold text-white">
            ${signal.price.toLocaleString()}
          </div>
        </div>
        <div>
          <span className="text-xs text-gray-500 font-semibold">Model</span>
          <div className="text-sm sm:text-base font-bold text-white capitalize mt-1 truncate">
            {signal.model_type}
          </div>
        </div>
      </div>

      {signal.direction !== 'neutral' && signal.take_profit && signal.stop_loss && (
        <div className="space-y-3 py-3 border-t border-gray-800">
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-500 uppercase tracking-wider">TP/SL Levels</span>
            <div className="flex items-center gap-2">
              {signal.tp_sl_source === 'optimized' ? (
                <span className="text-xs font-semibold text-green-400 bg-green-500/10 px-2 py-0.5 rounded border border-green-500/30">
                  📊 Data-driven
                </span>
              ) : (
                <span className="text-xs font-semibold text-gray-400 bg-gray-500/10 px-2 py-0.5 rounded border border-gray-500/30">
                  📐 Default
                </span>
              )}
              {signal.risk_reward && (
                <span className="text-xs font-semibold text-blue-400 bg-blue-500/10 px-2 py-0.5 rounded">
                  R:R {signal.risk_reward}
                </span>
              )}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="bg-green-500/10 border border-green-500/30 rounded-lg p-3 relative overflow-hidden">
              <div className="absolute top-1 right-1 text-2xl">↗</div>
              <div className="flex items-center gap-1 mb-1">
                <span className="text-xs text-green-400 font-bold">Take Profit</span>
              </div>
              <div className="text-sm font-extrabold text-green-400">
                ${signal.take_profit.toLocaleString()}
              </div>
              <div className="inline-block mt-1.5 px-2 py-0.5 bg-green-500/20 rounded-full border border-green-500/40">
                <span className="text-xs text-green-300 font-bold">
                  {signal.direction === 'long'
                    ? `+${(((signal.take_profit - signal.price) / signal.price) * 100).toFixed(2)}%`
                    : `+${(((signal.price - signal.take_profit) / signal.price) * 100).toFixed(2)}%`
                  }
                </span>
              </div>
            </div>

            <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 relative overflow-hidden">
              <div className="absolute top-1 right-1 text-2xl">↘</div>
              <div className="flex items-center gap-1 mb-1">
                <span className="text-xs text-red-400 font-bold">Stop Loss</span>
              </div>
              <div className="text-sm font-extrabold text-red-400">
                ${signal.stop_loss.toLocaleString()}
              </div>
              <div className="inline-block mt-1.5 px-2 py-0.5 bg-red-500/20 rounded-full border border-red-500/40">
                <span className="text-xs text-red-300 font-bold">
                  {signal.direction === 'long'
                    ? `-${(((signal.price - signal.stop_loss) / signal.price) * 100).toFixed(2)}%`
                    : `-${(((signal.stop_loss - signal.price) / signal.price) * 100).toFixed(2)}%`
                  }
                </span>
              </div>
            </div>
          </div>

          {signal.atr && (
            <div className="text-xs text-gray-500">
              ATR: ${signal.atr.toLocaleString()} (TP: 3×ATR, SL: 1.5×ATR)
            </div>
          )}

          {signal.valid_until && (
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-yellow-400 bg-yellow-500/10 px-2 py-1 rounded border border-yellow-500/30">
                Valid for ~{signal.max_hold_candles || 12}h
              </span>
              <span className="text-xs text-gray-600">
                Until {new Date(signal.valid_until).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </span>
            </div>
          )}
        </div>
      )}

      <div>
        <span className="text-xs text-gray-500">Market Regime</span>
        <div className="text-xs sm:text-sm font-medium text-gray-300 mt-1 bg-gray-800/50 rounded px-2 py-1 inline-block">
          {signal.regime}
        </div>
      </div>

      {topFeatures.length > 0 && (
        <div className="pt-3 border-t border-gray-800">
          <h4 className="text-xs text-gray-500 uppercase tracking-wider mb-2 sm:mb-3">Top Features</h4>
          <div className="space-y-1.5 sm:space-y-2">
            {topFeatures.slice(0, 3).map(([name, value]) => {
              const maxValue = Math.max(...topFeatures.map(([, v]) => Math.abs(v as number)));
              const width = (Math.abs(value as number) / maxValue) * 100;
              const isPositive = (value as number) >= 0;

              return (
                <div key={name} className="space-y-1">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-gray-400 truncate flex-1 mr-2">{name}</span>
                    <span className={`font-mono font-semibold ${isPositive ? 'text-green-400' : 'text-red-400'} flex-shrink-0`}>
                      {(value as number).toFixed(3)}
                    </span>
                  </div>
                  <div className="w-full bg-gray-800 rounded-full h-1 sm:h-1.5 overflow-hidden">
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

      <div className="pt-2 border-t border-gray-800 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-1 sm:gap-0">
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
