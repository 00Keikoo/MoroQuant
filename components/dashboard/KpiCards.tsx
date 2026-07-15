'use client';

import { useMemo } from 'react';
import { usePerformanceReport, useOpenPositions, useModelHealth } from '@/lib/hooks/usePerformanceData';
import { normalizeError } from '@/lib/utils/errorNormalization';
import WidgetError from '@/components/shared/widgets/WidgetError';

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

interface ErrorKpiCardProps {
  label: string;
  error: unknown;
  onRetry: () => void;
}

function ErrorKpiCard({ label, error, onRetry }: ErrorKpiCardProps) {
  return (
    <div className="bg-surface-container p-md border border-error flex flex-col justify-between">
      <p className="font-label-caps text-label-caps text-error">{label}</p>
      <div className="mt-sm">
        <WidgetError error={error} onRetry={onRetry} />
      </div>
    </div>
  );
}

function LoadingKpiCard({ label }: { label: string }) {
  return (
    <div className="bg-surface-container p-md border border-outline-variant flex flex-col justify-between">
      <p className="font-label-caps text-label-caps text-secondary">{label}</p>
      <div className="flex items-end justify-between mt-sm">
        <div className="h-8 w-32 bg-outline-variant/50 animate-pulse rounded"></div>
        <div className="h-4 w-16 bg-outline-variant/50 animate-pulse rounded"></div>
      </div>
    </div>
  );
}

export default function KpiCards() {
  const { data: perfReport, isLoading: loadingPerf, error: errorPerf, refetch: refetchPerf, isFetching: fetchingPerf } = usePerformanceReport();
  const { data: positions = [], isLoading: loadingPos, error: errorPos, refetch: refetchPos, isFetching: fetchingPos } = useOpenPositions();
  const { data: modelHealthData, isLoading: loadingHealth, error: errorHealth, refetch: refetchHealth, isFetching: fetchingHealth } = useModelHealth();

  const dailyPnl = useMemo(() => {
    if (!perfReport?.equity_curve || perfReport.equity_curve.length === 0) {
      return { value: 0, pct: 0 };
    }

    const now = Date.now();
    const oneDayAgo = now - 24 * 60 * 60 * 1000;
    const recent = perfReport.equity_curve.filter(p => p.timestamp >= oneDayAgo);

    if (recent.length >= 2) {
      const firstPnl = recent[0].cumulative_pnl;
      const lastPnl = recent[recent.length - 1].cumulative_pnl;
      const change = lastPnl - firstPnl;
      const pct = firstPnl !== 0 ? (change / Math.abs(firstPnl)) * 100 : 0;
      return { value: change, pct };
    } else if (recent.length === 1) {
      return { value: recent[0].cumulative_pnl, pct: 0 };
    } else {
      return { value: perfReport.metrics.total_pnl, pct: 0 };
    }
  }, [perfReport]);

  const grossExposure = useMemo(() =>
    positions.reduce((sum, pos) => sum + Math.abs(pos.unrealized_pnl), 0)
  , [positions]);

  const netDelta = useMemo(() =>
    positions.reduce((sum, pos) => sum + (pos.side === 'long' ? pos.unrealized_pnl : -pos.unrealized_pnl), 0)
  , [positions]);

  const sharpe = perfReport?.metrics.sharpe_ratio ?? null;

  const modelHealth = useMemo(() => {
    if (!modelHealthData || modelHealthData.length === 0) return null;
    const green = modelHealthData.filter(m => m.health_status === 'green').length;
    const yellow = modelHealthData.filter(m => m.health_status === 'yellow').length;
    const red = modelHealthData.filter(m => m.health_status === 'red').length;
    const total = modelHealthData.length;

    let status = 'unknown';
    if (red > 0) status = 'critical';
    else if (yellow > 0) status = 'warning';
    else if (green > 0) status = 'normal';

    const avgDrift = modelHealthData.reduce((sum, m) => sum + (m.overall_score || 0), 0) / total;

    return { status, drift: avgDrift, timestamp: modelHealthData[0]?.timestamp || new Date().toISOString() };
  }, [modelHealthData]);

  const pnlColor = dailyPnl.value >= 0 ? 'text-[#00FF94]' : 'text-error';

  return (
    <div className="grid grid-cols-5 gap-md shrink-0">
      {/* Daily PNL - depends on perfReport */}
      {loadingPerf && !perfReport ? (
        <LoadingKpiCard label="DAILY PNL" />
      ) : errorPerf ? (
        <ErrorKpiCard label="DAILY PNL" error={errorPerf} onRetry={refetchPerf} />
      ) : (
        <KpiCard
          label="DAILY PNL"
          value={`${dailyPnl.value >= 0 ? '+' : ''}${dailyPnl.value.toFixed(2)}`}
          subValue={`${dailyPnl.pct >= 0 ? '+' : ''}${dailyPnl.pct.toFixed(2)}%`}
          valueColor={pnlColor}
          subValueColor={pnlColor}
        />
      )}

      {/* Gross Exposure - depends on positions */}
      {loadingPos && positions.length === 0 ? (
        <LoadingKpiCard label="GROSS EXPOSURE" />
      ) : errorPos ? (
        <ErrorKpiCard label="GROSS EXPOSURE" error={errorPos} onRetry={refetchPos} />
      ) : (
        <KpiCard
          label="GROSS EXPOSURE"
          value={`$${grossExposure.toFixed(0)}`}
          subValue="Total"
          valueColor="text-on-surface"
          subValueColor="text-secondary"
        />
      )}

      {/* Net Delta - depends on positions */}
      {loadingPos && positions.length === 0 ? (
        <LoadingKpiCard label="NET DELTA" />
      ) : errorPos ? (
        <ErrorKpiCard label="NET DELTA" error={errorPos} onRetry={refetchPos} />
      ) : (
        <KpiCard
          label="NET DELTA"
          value={`$${netDelta.toFixed(0)}`}
          subValue={netDelta >= 0 ? 'Long' : 'Short'}
          valueColor="text-on-surface"
          subValueColor="text-secondary"
        />
      )}

      {/* Model Health - depends on modelHealthData */}
      {loadingHealth && !modelHealthData ? (
        <LoadingKpiCard label="MODEL HEALTH" />
      ) : errorHealth ? (
        <ErrorKpiCard label="MODEL HEALTH" error={errorHealth} onRetry={refetchHealth} />
      ) : (
        <KpiCard
          label="MODEL HEALTH"
          value={modelHealth ? modelHealth.status.toUpperCase() : 'N/A'}
          subValue={modelHealth ? `Drift: ${(modelHealth.drift * 100).toFixed(1)}%` : 'Not Available'}
          valueColor={
            modelHealth?.status === 'normal' ? 'text-[#00FF94]' :
            modelHealth?.status === 'warning' ? 'text-yellow-500' :
            modelHealth?.status === 'critical' ? 'text-error' :
            'text-secondary'
          }
          subValueColor="text-secondary"
        />
      )}

      {/* Sharpe Ratio - depends on perfReport */}
      {loadingPerf && !perfReport ? (
        <LoadingKpiCard label="SHARPE RATIO (30D)" />
      ) : errorPerf ? (
        <ErrorKpiCard label="SHARPE RATIO (30D)" error={errorPerf} onRetry={refetchPerf} />
      ) : (
        <KpiCard
          label="SHARPE RATIO (30D)"
          value={sharpe !== null ? sharpe.toFixed(2) : '--'}
          subValue={sharpe !== null && sharpe > 1 ? 'Good' : sharpe !== null && sharpe > 0 ? 'Fair' : 'Poor'}
          valueColor="text-on-surface"
          subValueColor={sharpe !== null && sharpe > 1 ? 'text-[#00FF94]' : 'text-secondary'}
        />
      )}
    </div>
  );
}
