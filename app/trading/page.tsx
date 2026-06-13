'use client';

import { useState, useEffect } from 'react';
import Sidebar from '@/components/layout/Sidebar';
import SignalGrid from '@/components/trading/SignalGrid';

export default function TradingPage() {
  const [timeframe, setTimeframe] = useState<'1h' | '4h'>('1h');
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [currentTime, setCurrentTime] = useState<string>('');
  const [currentDate, setCurrentDate] = useState<string>('');

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setCurrentTime(now.toLocaleTimeString());
      setCurrentDate(now.toLocaleDateString());
    };

    updateTime();
    const interval = setInterval(updateTime, 1000);

    return () => clearInterval(interval);
  }, []);

  const handleTimeframeChange = (newTimeframe: '1h' | '4h') => {
    if (newTimeframe !== timeframe) {
      setIsTransitioning(true);
      setTimeframe(newTimeframe);
      setTimeout(() => setIsTransitioning(false), 300);
    }
  };

  return (
    <div className="flex h-screen bg-black text-white">
      <Sidebar />

      <div className="flex-1 flex flex-col overflow-hidden relative">
        <div
          className="absolute inset-0 opacity-[0.015]"
          style={{
            backgroundImage: `
              linear-gradient(rgba(59, 130, 246, 0.1) 1px, transparent 1px),
              linear-gradient(90deg, rgba(59, 130, 246, 0.1) 1px, transparent 1px)
            `,
            backgroundSize: '50px 50px'
          }}
        />
        <div className="flex-1 p-4 sm:p-6 overflow-y-auto relative z-10">
          <div className="max-w-7xl mx-auto space-y-6">
            <div className="bg-gradient-to-r from-blue-900/30 via-purple-900/20 to-blue-900/30 rounded-2xl p-6 sm:p-8 border border-blue-800/30 shadow-2xl">
              <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <h1 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
                      ML Trading Intelligence
                    </h1>
                    <div className="flex items-center gap-2 px-3 py-1 bg-green-500/10 rounded-full border border-green-500/30">
                      <div className="w-2.5 h-2.5 bg-green-400 rounded-full animate-pulse shadow-lg shadow-green-500/50"></div>
                      <span className="text-xs text-green-400 font-extrabold uppercase tracking-wider">
                        Live
                      </span>
                    </div>
                  </div>
                  <p className="text-base sm:text-lg text-gray-300 mb-1 font-medium">
                    Real-time trading signals powered by XGBoost & LightGBM
                  </p>
                  {currentTime && (
                    <p className="text-xs text-gray-500 font-medium">
                      Last updated: {currentTime} • {currentDate}
                    </p>
                  )}
                </div>

                <div className="flex gap-2">
                  <button
                    onClick={() => handleTimeframeChange('1h')}
                    className={`px-6 py-3 rounded-lg text-sm font-bold transition-all duration-300 ${
                      timeframe === '1h'
                        ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/50 scale-105'
                        : 'bg-gray-900 text-gray-400 border border-gray-800 hover:bg-gray-800 hover:border-gray-700'
                    }`}
                  >
                    1h
                  </button>
                  <button
                    onClick={() => handleTimeframeChange('4h')}
                    className={`px-6 py-3 rounded-lg text-sm font-bold transition-all duration-300 ${
                      timeframe === '4h'
                        ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/50 scale-105'
                        : 'bg-gray-900 text-gray-400 border border-gray-800 hover:bg-gray-800 hover:border-gray-700'
                    }`}
                  >
                    4h
                  </button>
                </div>
              </div>
            </div>

            <div className={`transition-opacity duration-300 ${isTransitioning ? 'opacity-0' : 'opacity-100'}`}>
              <SignalGrid timeframe={timeframe} />
            </div>

            <div className="pt-4 border-t border-gray-800">
              <p className="text-xs text-gray-600 italic text-center">
                Signals are generated using XGBoost/LightGBM models trained on historical data.
                This is for educational purposes only, not financial advice.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
