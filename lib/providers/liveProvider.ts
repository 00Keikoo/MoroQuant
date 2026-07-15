import type { TradingDataProvider, EquityRange } from './types';
import {
  getLivePerformanceReport,
  getRecentTrades,
  getOpenPositions,
  getRegimePerformance,
  getConfidenceBuckets,
  getAccountEquity,
  getAccountEquityHistory,
  getClosedTradeEquity,
} from '@/lib/services/performanceService';

export class LiveProvider implements TradingDataProvider {
  async getAccountEquity() {
    return getAccountEquity('LIVE');
  }

  async getEquityHistory(range: EquityRange = '7d') {
    return getAccountEquityHistory(range, 'LIVE');
  }

  async getMetrics() {
    const report = await getLivePerformanceReport('LIVE');
    if (report.status === 'success') {
      return report.metrics;
    }
    return null;
  }

  async getOpenPositions() {
    return getOpenPositions('LIVE');
  }

  async getRecentTrades(limit = 20) {
    return getRecentTrades('LIVE', { limit });
  }

  async getRegimePerformance() {
    return getRegimePerformance('LIVE');
  }

  async getConfidenceBuckets() {
    return getConfidenceBuckets('LIVE');
  }

  async getEquityCurve() {
    return getClosedTradeEquity('LIVE');
  }
}
