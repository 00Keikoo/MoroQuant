import type { TradingDataProvider, EquityRange } from './types';
import {
  getPaperAccount,
  getPaperOpenPositions,
  getPaperEquityHistory,
  getPaperAnalytics,
  getPaperTrades,
} from '@/lib/api/ml-trading';

export class PaperProvider implements TradingDataProvider {
  async getAccountEquity() {
    const account = await getPaperAccount();
    return {
      wallet_balance: account.balance,
      unrealized_pnl: account.unrealized_pnl,
      margin_balance: account.equity,
      available_balance: account.balance,
      source: 'binance' as const,
    };
  }

  async getEquityHistory(range: EquityRange = '7d') {
    const history = await getPaperEquityHistory(range);
    return history.map((p) => ({
      timestamp: p.timestamp,
      equity: p.equity,
      wallet_balance: p.balance,
      unrealized_pnl: p.unrealized_pnl,
    }));
  }

  async getMetrics() {
    const analytics = await getPaperAnalytics();
    return {
      total_trades: analytics.closed_positions,
      winning_trades: 0,
      losing_trades: 0,
      win_rate: analytics.win_rate,
      total_pnl: analytics.total_realized_pnl,
      avg_pnl: analytics.avg_trade_pnl,
      avg_win: 0,
      avg_loss: 0,
      profit_factor: Number.isFinite(analytics.profit_factor) ? analytics.profit_factor : 0,
      expectancy: analytics.expectancy,
      roi: analytics.total_realized_pnl,
      gross_profit: 0,
      gross_loss: 0,
      sharpe_ratio: null,
      max_drawdown: 0,
      max_drawdown_pct: 0,
      avg_hold_time_hours: analytics.avg_hold_hours,
    };
  }

  async getOpenPositions() {
    const positions = await getPaperOpenPositions();
    return positions.map((p) => ({
      symbol: p.symbol,
      side: p.direction === 'LONG' ? 'long' : 'short',
      entry_price: p.entry_price,
      mark_price: p.current_price ?? p.entry_price,
      unrealized_pnl: 0,
      agreement: 'match' as const,
    }));
  }

  async getRecentTrades(limit = 20) {
    const { trades } = await getPaperTrades(limit);
    return trades.map((t) => ({
      symbol: t.symbol,
      side: t.direction === 'LONG' ? 'long' : 'short',
      direction: t.direction === 'LONG' ? 'long' : 'short',
      entry_time: new Date(t.opened_at).getTime() / 1000,
      exit_time: new Date(t.closed_at ?? t.opened_at).getTime() / 1000,
      duration_minutes:
        ((new Date(t.closed_at ?? t.opened_at).getTime() - new Date(t.opened_at).getTime()) /
          60000) || 0,
      entry_price: t.entry_price,
      exit_price: t.exit_price,
      quantity: 0,
      gross_pnl: t.realized_pnl,
      commission: 0,
      net_pnl: t.realized_pnl,
      regime: t.status,
      confidence: null,
      outcome: (t.realized_pnl > 0 ? 'win' : t.realized_pnl < 0 ? 'loss' : 'breakeven') as
        | 'win'
        | 'loss'
        | 'breakeven',
      matched_signal_id: null,
      fill_count: 1,
    }));
  }

  async getRegimePerformance() {
    const { getPaperRegimeAnalytics } = await import('@/lib/api/ml-trading');
    const regimes = await getPaperRegimeAnalytics();

    const result: Record<string, any> = {};
    for (const [key, data] of Object.entries(regimes)) {
      result[key] = {
        regime_label: (data as any).regime,
        total_trades: (data as any).total_trades,
        win_rate: (data as any).win_rate,
        profit_factor: 0,
        expectancy: (data as any).avg_pnl,
      };
    }
    return result;
  }

  async getConfidenceBuckets() {
    const { getPaperConfidenceAnalytics } = await import('@/lib/api/ml-trading');
    const buckets = await getPaperConfidenceAnalytics();

    const result: Record<string, any> = {};
    for (const [key, data] of Object.entries(buckets)) {
      result[key] = {
        bucket: (data as any).bucket,
        total_trades: (data as any).total_trades,
        win_rate: (data as any).win_rate,
        expectancy: (data as any).avg_pnl,
        total_pnl: (data as any).total_pnl,
      };
    }
    return result;
  }

  async getEquityCurve() {
    const history = await getPaperEquityHistory();
    const account = await getPaperAccount();
    return history.map((p, idx) => ({
      trade_count: idx + 1,
      equity: p.equity,
      cumulative_pnl: p.equity - account.balance,
      trade_pnl: 0,
      timestamp: new Date(p.timestamp).getTime(),
    }));
  }
}
