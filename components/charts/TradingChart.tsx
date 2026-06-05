'use client';

import { useEffect, useRef, useState } from 'react';
import { useMarketStore } from '@/lib/stores/marketStore';
import { Candlestick, Timeframe } from '@/lib/types';

const timeframes: Timeframe[] = ['1m', '5m', '15m', '1h', '4h', '1D'];

const BINANCE_WS_BASE = 'wss://stream.binance.com:9443/ws';
const MAX_RETRIES = 5;
const RETRY_DELAY = 3000;
const POLLING_FALLBACK_INTERVAL = 5000;

export default function TradingChart() {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<any>(null);
  const candlestickSeriesRef = useRef<any>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const retryCountRef = useRef(0);
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const [isChartReady, setIsChartReady] = useState(false);
  const [isLive, setIsLive] = useState(false);

  const { selectedPair, timeframe, setTimeframe, candlesticks, indicators, updateCandlesticks } = useMarketStore();
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

  const connectWebSocket = () => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const tfMap: Record<Timeframe, string> = {
      '1m': '1m', '5m': '5m', '15m': '15m', '1h': '1h', '4h': '4h', '1D': '1d'
    };
    const interval = tfMap[timeframe];
    const symbol = selectedPair.toLowerCase();
    const wsUrl = `${BINANCE_WS_BASE}/${symbol}@kline_${interval}`;

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsLive(true);
        retryCountRef.current = 0;
        if (pollingIntervalRef.current) {
          clearInterval(pollingIntervalRef.current);
          pollingIntervalRef.current = null;
        }
      };

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          const kline = message.k;
          if (!kline) return;

          const newCandle: Candlestick = {
            time: Math.floor(kline.t / 1000),
            open: parseFloat(kline.o),
            high: parseFloat(kline.h),
            low: parseFloat(kline.l),
            close: parseFloat(kline.c),
            volume: parseFloat(kline.v),
          };

          const currentCandles = candlesticks.get(selectedPair) || [];
          const lastCandle = currentCandles[currentCandles.length - 1];

          if (lastCandle && lastCandle.time === newCandle.time) {
            const updatedCandles = [...currentCandles.slice(0, -1), newCandle];
            updateCandlesticks(selectedPair, updatedCandles);
          } else if (kline.x) {
            const updatedCandles = [...currentCandles, newCandle];
            updateCandlesticks(selectedPair, updatedCandles);
          }
        } catch (err) {
          console.error('WebSocket message parse error:', err);
        }
      };

      ws.onerror = () => {
        setIsLive(false);
      };

      ws.onclose = () => {
        setIsLive(false);
        wsRef.current = null;

        if (retryCountRef.current < MAX_RETRIES) {
          retryCountRef.current++;
          setTimeout(connectWebSocket, RETRY_DELAY);
        } else {
          startPollingFallback();
        }
      };
    } catch (err) {
      console.error('WebSocket connection error:', err);
      if (retryCountRef.current < MAX_RETRIES) {
        retryCountRef.current++;
        setTimeout(connectWebSocket, RETRY_DELAY);
      } else {
        startPollingFallback();
      }
    }
  };

  const startPollingFallback = () => {
    if (pollingIntervalRef.current) return;

    pollingIntervalRef.current = setInterval(async () => {
      try {
        const response = await fetch(`/api/market/candlesticks?symbol=${selectedPair}&timeframe=${timeframe}&limit=1`);
        if (response.ok) {
          const data = await response.json();
          if (data.length > 0) {
            const currentCandles = candlesticks.get(selectedPair) || [];
            const newCandle = data[0];
            const lastCandle = currentCandles[currentCandles.length - 1];

            if (lastCandle && lastCandle.time === newCandle.time) {
              const updatedCandles = [...currentCandles.slice(0, -1), newCandle];
              updateCandlesticks(selectedPair, updatedCandles);
            }
          }
        }
      } catch (err) {
        console.error('Polling fallback error:', err);
      }
    }, POLLING_FALLBACK_INTERVAL);
  };

  useEffect(() => {
    if (isChartReady) {
      connectWebSocket();
    }

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
      }
    };
  }, [selectedPair, timeframe, isChartReady]);

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
          {isLive && (
            <span className="flex items-center gap-1 text-xs text-green-400">
              <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></span>
              LIVE
            </span>
          )}
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
