'use client';

import { useEffect, useRef, useState } from 'react';
import { useMarketStore } from '@/lib/stores/marketStore';
import { Candlestick, Timeframe } from '@/lib/types';

const timeframes: Timeframe[] = ['1m', '5m', '15m', '1h', '4h', '1D'];

export default function TradingChart() {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<any>(null);
  const candlestickSeriesRef = useRef<any>(null);
  const [isChartReady, setIsChartReady] = useState(false);

  const { selectedPair, timeframe, setTimeframe, candlesticks, indicators } = useMarketStore();
  const currentCandles = candlesticks.get(selectedPair) || [];
  const currentIndicators = indicators.get(selectedPair);

  useEffect(() => {
    if (!chartContainerRef.current) return;

    let chart: any;
    let candlestickSeries: any;

    import('lightweight-charts').then(({ createChart, CandlestickSeries }) => {
      if (!chartContainerRef.current) return;

      chart = createChart(chartContainerRef.current, {
        layout: {
          background: { color: '#0a0a0a' },
          textColor: '#d1d5db',
        },
        grid: {
          vertLines: { color: '#1f2937' },
          horzLines: { color: '#1f2937' },
        },
        width: chartContainerRef.current.clientWidth,
        height: 600,
        timeScale: {
          timeVisible: true,
          secondsVisible: false,
        },
      });

      candlestickSeries = chart.addSeries(CandlestickSeries, {
        upColor: '#10b981',
        downColor: '#ef4444',
        borderUpColor: '#10b981',
        borderDownColor: '#ef4444',
        wickUpColor: '#10b981',
        wickDownColor: '#ef4444',
      });

      chartRef.current = chart;
      candlestickSeriesRef.current = candlestickSeries;
      setIsChartReady(true);

      const handleResize = () => {
        if (chartContainerRef.current && chartRef.current) {
          chartRef.current.applyOptions({
            width: chartContainerRef.current.clientWidth,
          });
        }
      };

      window.addEventListener('resize', handleResize);
    });

    return () => {
      if (chart) {
        window.removeEventListener('resize', () => {});
        chart.remove();
      }
    };
  }, []);

  useEffect(() => {
    if (!isChartReady || !candlestickSeriesRef.current || currentCandles.length === 0) return;

    const data = currentCandles.map((candle: Candlestick) => ({
      time: candle.time as any,
      open: candle.open,
      high: candle.high,
      low: candle.low,
      close: candle.close,
    }));

    candlestickSeriesRef.current.setData(data);
  }, [isChartReady, currentCandles]);

  return (
    <div className="flex flex-col h-full bg-gray-950 rounded-lg border border-gray-800">
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800">
        <div className="flex items-center gap-4">
          <h2 className="text-lg font-semibold text-white">{selectedPair}</h2>
          {currentIndicators && (
            <div className="flex gap-4 text-sm">
              <span className="text-gray-400">
                RSI: <span className={currentIndicators.rsi > 70 ? 'text-red-400' : currentIndicators.rsi < 30 ? 'text-green-400' : 'text-gray-300'}>
                  {currentIndicators.rsi.toFixed(2)}
                </span>
              </span>
              <span className="text-gray-400">
                EMA20: <span className="text-gray-300">{currentIndicators.ema20.toFixed(2)}</span>
              </span>
            </div>
          )}
        </div>
        <div className="flex gap-2">
          {timeframes.map((tf) => (
            <button
              key={tf}
              onClick={() => setTimeframe(tf)}
              className={`px-3 py-1 text-sm rounded ${
                timeframe === tf
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
              }`}
            >
              {tf}
            </button>
          ))}
        </div>
      </div>
      <div ref={chartContainerRef} className="flex-1" />
    </div>
  );
}
