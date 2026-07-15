'use client';

import { useCallback, useEffect, useState } from 'react';
import { getLivePerformanceReport, getOpenPositions } from '@/lib/services/performanceService';
import { getModelHealth } from '@/lib/api/ml-trading';
import { useTradingMode } from '@/lib/hooks/useTradingMode';

interface KpiCardProps {
  label: string;
  value: string;
  subValue: string;
  valueColor?: string;
  subValueColor?: string;
}

function KpiCard({ label, value, subValue, valueColor = 'text-on-surface', subValueColor = 'text-secondary' }: KpiCardProps) {
  return (
    <div className="bg-surface-container p-md border border-outline-variant flex flex-col justify-between">
      <p className="font-label-caps text-label-caps text-secondary">{label}</p>
      <div className="flex items-end justify-between mt-sm">
        <p className={`font-data-tabular text-display-lg ${valueColor}`}>{value}</p>
        <span className={`text-data-tabular ${subValueColor}`}>{subValue}</span>
      </div>
    </div>
  );
}

export default function KpiCards() {
  const { mode } = useTradingMode();
  const [loading, setLoading] = useState(true);
  const [dailyPnl, setDailyPnl] = useState<{ value: number; pct: number } | null>(null);
  const [grossExposure, setGrossExposure] = useState<number | null>(null);
  const [netDelta, setNetDelta] = useState<number | null>(null);
  const [sharpe, setSharpe] = useState<number | null>(null);
  const [modelHealth, setModelHealth] = useState<{ status: string; drift: number; timestamp: string } | null>(null);

  const load = useCallback(async () => {
    if (mode === null) return;

    if (mode === 'OFF') {
      setDailyPnl({ value: 0, pct: 0 });
      setGrossExposure(0);
      setNetDelta(0);
      setSharpe(null);
      setModelHealth(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const tradingMode = mode;
      const [perfReport, positions, healthData] = await Promise.all([
        getLivePerformanceReport(tradingMode),
        getOpenPositions(tradingMode),
        getModelHealth('ES_proxy', '1h').catch(() => null),
      ]);

      // Daily PnL: calculate from equity curve (last 24h change)
      if (perfReport.equity_curve && perfReport.equity_curve.length > 0) {
        const now = Date.now();
        const oneDayAgo = now - 24 * 60 * 60 * 1000;
        const recent = perfReport.equity_curve.filter(p => p.timestamp >= oneDayAgo);

        if (recent.length >= 2) {
          const firstPnl = recent[0].cumulative_pnl;
          const lastPnl = recent[recent.length - 1].cumulative_pnl;
          const change = lastPnl - firstPnl;
          const pct = firstPnl !== 0 ? (change / Math.abs(firstPnl)) * 100 : 0;
          setDailyPnl({ value: change, pct });
        } else if (recent.length === 1) {
          setDailyPnl({ value: recent[0].cumulative_pnl, pct: 0 });
        } else {
          setDailyPnl({ value: perfReport.metrics.total_pnl, pct: 0 });
        }
      } else {
        setDailyPnl({ value: 0, pct: 0 });
      }

      // Gross Exposure: sum of absolute unrealized PnL (proxy without position quantities)
      const exposure = positions.reduce((sum, pos) => sum + Math.abs(pos.unrealized_pnl), 0);
      setGrossExposure(exposure);

      // Net Delta: sum of unrealized PnL by direction
      const delta = positions.reduce((sum, pos) => {
        return sum + (pos.side === 'LONG' ? pos.unrealized_pnl : -pos.unrealized_pnl);
      }, 0);
      setNetDelta(delta);

      // Sharpe Ratio
      setSharpe(perfReport.metrics.sharpe_ratio);

      // Model Health
      if (healthData) {
        const status = healthData.health_status || 'unknown';
        const drift = healthData.overall_score || 0;
        const timestamp = healthData.timestamp || new Date().toISOString();
        setModelHealth({ status, drift, timestamp });
      } else {
        setModelHealth(null);
      }
    } catch (err) {
      console.error('Failed to load KPI data:', err);
    } finally {
      setLoading(false);
    }
  }, [mode]);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) {
    return (
      <div className="grid grid-cols-5 gap-md shrink-0">
        {[1, 2, 3, 4, 5].map(i => (
          <div key={i} className="bg-surface-container p-md border border-outline-variant flex flex-col justify-between">
            <p className="font-label-caps text-label-caps text-secondary">LOADING</p>
            <div className="flex items-end justify-between mt-sm">
              <p className="font-data-tabular text-display-lg text-secondary">--</p>
              <span className="text-data-tabular text-secondary">--</span>
            </div>
          </div>
        ))}
      </div>
    );
  }

  const pnlColor = dailyPnl && dailyPnl.value >= 0 ? 'text-[#00FF94]' : 'text-error';

  return (
    <div className="grid grid-cols-5 gap-md shrink-0">
      <KpiCard
        label="DAILY PNL"
        value={dailyPnl ? `${dailyPnl.value >= 0 ? '+' : ''}${dailyPnl.value.toFixed(2)}` : '--'}
        subValue={dailyPnl ? `${dailyPnl.pct >= 0 ? '+' : ''}${dailyPnl.pct.toFixed(2)}%` : '--'}
        valueColor={pnlColor}
        subValueColor={pnlColor}
      />
      <KpiCard
        label="GROSS EXPOSURE"
        value={grossExposure !== null ? `$${grossExposure.toFixed(0)}` : '--'}
        subValue="Total"
        valueColor="text-on-surface"
        subValueColor="text-secondary"
      />
      <KpiCard
        label="NET DELTA"
        value={netDelta !== null ? `$${netDelta.toFixed(0)}` : '--'}
        subValue={netDelta !== null && netDelta >= 0 ? 'Long' : 'Short'}
        valueColor="text-on-surface"
        subValueColor="text-secondary"
      />
      <KpiCard
        label="MODEL HEALTH"
        value={modelHealth ? modelHealth.status.toUpperCase() : 'N/A'}
        subValue={modelHealth ? `Drift: ${(modelHealth.drift * 100).toFixed(1)}%` : 'Not Available'}
        valueColor={
          modelHealth
            ? modelHealth.status === 'normal'
              ? 'text-[#00FF94]'
              : modelHealth.status === 'warning'
              ? 'text-yellow-500'
              : modelHealth.status === 'critical'
              ? 'text-error'
              : 'text-secondary'
            : 'text-secondary'
        }
        subValueColor="text-secondary"
      />
      <KpiCard
        label="SHARPE RATIO (30D)"
        value={sharpe !== null ? sharpe.toFixed(2) : '--'}
        subValue={sharpe !== null && sharpe > 1 ? 'Good' : sharpe !== null && sharpe > 0 ? 'Fair' : 'Poor'}
        valueColor="text-on-surface"
        subValueColor={sharpe !== null && sharpe > 1 ? 'text-[#00FF94]' : 'text-secondary'}
      />
    </div>
  );
}
