import { Candlestick, TechnicalIndicators } from '../types';

export function calculateRSI(candles: Candlestick[], period: number = 14): number {
  if (candles.length < period + 1) return 50;

  const changes = candles.slice(-period - 1).map((candle, i, arr) => {
    if (i === 0) return 0;
    return candle.close - arr[i - 1].close;
  }).slice(1);

  const gains = changes.map(c => c > 0 ? c : 0);
  const losses = changes.map(c => c < 0 ? Math.abs(c) : 0);

  const avgGain = gains.reduce((a, b) => a + b, 0) / period;
  const avgLoss = losses.reduce((a, b) => a + b, 0) / period;

  if (avgLoss === 0) return 100;
  const rs = avgGain / avgLoss;
  return 100 - (100 / (1 + rs));
}

export function calculateEMA(candles: Candlestick[], period: number): number {
  if (candles.length < period) return candles[candles.length - 1]?.close || 0;

  const multiplier = 2 / (period + 1);
  let ema = candles.slice(0, period).reduce((sum, c) => sum + c.close, 0) / period;

  for (let i = period; i < candles.length; i++) {
    ema = (candles[i].close - ema) * multiplier + ema;
  }

  return ema;
}

export function calculateMACD(candles: Candlestick[]): { macd: number; signal: number; histogram: number } {
  const ema12 = calculateEMA(candles, 12);
  const ema26 = calculateEMA(candles, 26);
  const macd = ema12 - ema26;

  const macdLine = candles.slice(-9).map((_, i) => {
    const subset = candles.slice(0, candles.length - 9 + i + 1);
    const e12 = calculateEMA(subset, 12);
    const e26 = calculateEMA(subset, 26);
    return e12 - e26;
  });

  const signal = macdLine.reduce((sum, val) => sum + val, 0) / macdLine.length;
  const histogram = macd - signal;

  return { macd, signal, histogram };
}

export function calculateBollingerBands(
  candles: Candlestick[],
  period: number = 20,
  stdDev: number = 2
): { upper: number; middle: number; lower: number } {
  if (candles.length < period) {
    const close = candles[candles.length - 1]?.close || 0;
    return { upper: close, middle: close, lower: close };
  }

  const closes = candles.slice(-period).map(c => c.close);
  const middle = closes.reduce((sum, val) => sum + val, 0) / period;

  const variance = closes.reduce((sum, val) => sum + Math.pow(val - middle, 2), 0) / period;
  const std = Math.sqrt(variance);

  return {
    upper: middle + (std * stdDev),
    middle,
    lower: middle - (std * stdDev),
  };
}

export function calculateIndicators(candles: Candlestick[]): TechnicalIndicators {
  return {
    rsi: calculateRSI(candles),
    macd: calculateMACD(candles),
    bollingerBands: calculateBollingerBands(candles),
    ema20: calculateEMA(candles, 20),
    ema50: calculateEMA(candles, 50),
    ema200: calculateEMA(candles, 200),
  };
}
