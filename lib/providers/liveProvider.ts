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
    return getAccountEquity();
  }

  async getEquityHistory(range: EquityRange = '7d') {
    return getAccountEquityHistory(range);
  }

  async getMetrics() {
    const report = await getLivePerformanceReport();
    if (report.status === 'success') {
      return report.metrics;
    }
    return null;
  }

  async getOpenPositions() {
    return getOpenPositions();
  }

  async getRecentTrades(limit = 20) {
    return getRecentTrades(limit);
  }

  async getRegimePerformance() {
    return getRegimePerformance();
  }

  async getConfidenceBuckets() {
    return getConfidenceBuckets();
  }

  async getEquityCurve() {
    return getClosedTradeEquity();
  }
}
