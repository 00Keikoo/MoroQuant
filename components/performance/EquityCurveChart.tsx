'use client';

import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Area,
  ComposedChart,
} from 'recharts';
import type {
  EquityPoint,
  EquitySnapshot,
  EquityRange,
} from '@/lib/services/performanceService';

// ─── Shared chart geometry ────────────────────────────────────────
const CHART_HEIGHT = 360;

// ─── Range selector pills ─────────────────────────────────────────
const RANGES: { label: string; value: EquityRange }[] = [
  { label: '1D', value: '1d' },
  { label: '7D', value: '7d' },
  { label: '30D', value: '30d' },
  { label: 'ALL', value: 'all' },
];

interface RangeSelectorProps {
  selected: EquityRange;
  onSelect: (range: EquityRange) => void;
  disabled?: boolean;
}

function RangeSelector({ selected, onSelect, disabled }: RangeSelectorProps) {
  return (
    <div className="flex items-center gap-1 bg-black/40 border border-mq-panel-border rounded-md p-0.5">
      {RANGES.map(({ label, value }) => {
        const active = value === selected;
        return (
          <button
            key={value}
            type="button"
            disabled={disabled}
            onClick={() => onSelect(value)}
            className={`px-2.5 py-1 rounded text-[10px] font-bold tracking-wider transition-all ${
              active
                ? 'bg-mq-accent/20 text-mq-accent border border-mq-accent/40'
                : 'text-neutral-500 hover:text-neutral-300 border border-transparent'
            } ${disabled ? 'opacity-40 cursor-not-allowed' : 'cursor-pointer'}`}
          >
            {label}
          </button>
        );
      })}
    </div>
  );
}

// ─── True Binance Equity Curve ────────────────────────────────────
interface TrueEquityTooltipProps {
  active?: boolean;
  payload?: { payload: EquitySnapshot }[];
}

function TrueEquityTooltip({ active, payload }: TrueEquityTooltipProps) {
  if (!active || !payload || payload.length === 0) return null;
  const point = payload[0].payload;
  const date = new Date(point.timestamp).toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
  const pnlColor = point.unrealized_pnl >= 0 ? '#00ff87' : '#ff0055';

  return (
    <div
      style={{
        backgroundColor: 'rgba(9, 9, 11, 0.95)',
        border: '1px solid rgba(0, 240, 255, 0.2)',
        borderRadius: '8px',
        padding: '10px 12px',
        boxShadow: '0 4px 12px rgba(0, 0, 0, 0.6)',
      }}
    >
      <div style={{ fontSize: '10px', color: '#8e8e93', marginBottom: '6px' }}>
        {date}
      </div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: '6px', marginBottom: '2px' }}>
        <span style={{ fontSize: '10px', color: '#8e8e93' }}>Equity:</span>
        <span style={{ fontSize: '13px', fontWeight: 700, color: '#00f0ff' }}>
          ${point.equity.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
        </span>
      </div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: '6px', marginBottom: '2px' }}>
        <span style={{ fontSize: '10px', color: '#8e8e93' }}>Wallet:</span>
        <span style={{ fontSize: '12px', fontWeight: 600, color: '#e4e4e7' }}>
          ${point.wallet_balance.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
        </span>
      </div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: '6px' }}>
        <span style={{ fontSize: '10px', color: '#8e8e93' }}>Unrealized:</span>
        <span style={{ fontSize: '12px', fontWeight: 600, color: pnlColor }}>
          {point.unrealized_pnl >= 0 ? '+' : ''}${point.unrealized_pnl.toFixed(2)}
        </span>
      </div>
    </div>
  );
}

interface TrueEquityCurveProps {
  data: EquitySnapshot[];
  height?: number;
}

/**
 * True Binance account equity curve — sourced from persisted wallet
 * snapshots. Equity = margin_balance = wallet_balance + unrealized_pnl,
 * which best reflects the live account value (captures funding, deposits,
 * withdrawals, transfers, and unrealized PnL).
 */
export function TrueEquityCurve({ data, height = CHART_HEIGHT }: TrueEquityCurveProps) {
  const chartData = data.map((point) => {
    const date = new Date(point.timestamp);
    return {
      ...point,
      label: date.toLocaleString(undefined, {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      }),
    };
  });

  if (chartData.length === 0) {
    return (
      <div
        className="flex items-center justify-center text-neutral-500 text-sm"
        style={{ height }}
      >
        No equity snapshots yet — waiting for Binance data
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={height}>
      <ComposedChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 5 }}>
        <defs>
          <linearGradient id="trueEquityFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#00f0ff" stopOpacity={0.25} />
            <stop offset="100%" stopColor="#00f0ff" stopOpacity={0} />
          </linearGradient>
        </defs>

        <CartesianGrid strokeDasharray="3 3" stroke="#1f1f23" vertical={false} />

        <XAxis
          dataKey="label"
          stroke="#52525b"
          tick={{ fontSize: 10, fill: '#8e8e93' }}
          tickLine={false}
          axisLine={{ stroke: '#27272a' }}
          interval="preserveStartEnd"
          minTickGap={30}
        />

        <YAxis
          stroke="#52525b"
          tick={{ fontSize: 10, fill: '#8e8e93' }}
          tickLine={false}
          axisLine={{ stroke: '#27272a' }}
          width={60}
          domain={['dataMin - 1', 'dataMax + 1']}
          tickFormatter={(value: number) => `$${value.toFixed(0)}`}
        />

        <Tooltip content={<TrueEquityTooltip />} cursor={{ stroke: '#00f0ff', strokeWidth: 1, strokeDasharray: '4 4' }} />

        <Area
          type="monotone"
          dataKey="equity"
          stroke="none"
          fill="url(#trueEquityFill)"
          isAnimationActive={true}
          animationDuration={600}
        />

        <Line
          type="monotone"
          dataKey="equity"
          stroke="#00f0ff"
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 4, fill: '#00f0ff', stroke: '#030303', strokeWidth: 2 }}
          isAnimationActive={true}
          animationDuration={600}
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}

// ─── Legacy Closed-Trade Equity Curve ─────────────────────────────
interface ClosedTradeTooltipProps {
  active?: boolean;
  payload?: { payload: EquityPoint }[];
}

function ClosedTradeTooltip({ active, payload }: ClosedTradeTooltipProps) {
  if (!active || !payload || payload.length === 0) return null;
  const point = payload[0].payload;
  const equity = typeof point.equity === 'number' ? point.equity : point.cumulative_pnl;
  const tradeColor = point.trade_pnl >= 0 ? '#00ff87' : '#ff0055';

  return (
    <div
      style={{
        backgroundColor: 'rgba(9, 9, 11, 0.95)',
        border: '1px solid rgba(0, 240, 255, 0.2)',
        borderRadius: '8px',
        padding: '10px 12px',
        boxShadow: '0 4px 12px rgba(0, 0, 0, 0.6)',
      }}
    >
      <div style={{ fontSize: '10px', color: '#8e8e93', marginBottom: '6px' }}>
        Trade #{point.trade_count}
      </div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: '6px', marginBottom: '2px' }}>
        <span style={{ fontSize: '10px', color: '#8e8e93' }}>Equity:</span>
        <span style={{ fontSize: '13px', fontWeight: 700, color: '#00f0ff' }}>
          ${equity.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
        </span>
      </div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: '6px' }}>
        <span style={{ fontSize: '10px', color: '#8e8e93' }}>This trade:</span>
        <span style={{ fontSize: '12px', fontWeight: 600, color: tradeColor }}>
          {point.trade_pnl >= 0 ? '+' : ''}${point.trade_pnl.toFixed(2)}
        </span>
      </div>
    </div>
  );
}

interface ClosedTradeEquityCurveProps {
  data: EquityPoint[];
  height?: number;
}

/**
 * Legacy synthetic closed-trade equity curve.
 * equity[n] = starting_balance + Σ(net_realized_pnl[0:n]).
 * Retained for realized-trade strategy analysis.
 */
export function ClosedTradeEquityCurve({
  data,
  height = CHART_HEIGHT,
}: ClosedTradeEquityCurveProps) {
  const chartData = [...data]
    .sort((a, b) => a.trade_count - b.trade_count)
    .map((point) => ({
      ...point,
      equityValue: typeof point.equity === 'number' ? point.equity : point.cumulative_pnl,
      label: `#${point.trade_count}`,
    }));

  if (chartData.length === 0) {
    return (
      <div
        className="flex items-center justify-center text-neutral-500 text-sm"
        style={{ height }}
      >
        No closed-trade data yet
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={height}>
      <ComposedChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 5 }}>
        <defs>
          <linearGradient id="closedEquityFillPositive" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#00ff87" stopOpacity={0.25} />
            <stop offset="100%" stopColor="#00ff87" stopOpacity={0} />
          </linearGradient>
        </defs>

        <CartesianGrid strokeDasharray="3 3" stroke="#1f1f23" vertical={false} />

        <XAxis
          dataKey="label"
          stroke="#52525b"
          tick={{ fontSize: 10, fill: '#8e8e93' }}
          tickLine={false}
          axisLine={{ stroke: '#27272a' }}
          interval="preserveStartEnd"
          minTickGap={30}
        />

        <YAxis
          stroke="#52525b"
          tick={{ fontSize: 10, fill: '#8e8e93' }}
          tickLine={false}
          axisLine={{ stroke: '#27272a' }}
          width={60}
          tickFormatter={(value: number) => `$${value.toFixed(0)}`}
        />

        <Tooltip content={<ClosedTradeTooltip />} cursor={{ stroke: '#00f0ff', strokeWidth: 1, strokeDasharray: '4 4' }} />

        <Area
          type="monotone"
          dataKey="equityValue"
          stroke="none"
          fill="url(#closedEquityFillPositive)"
          isAnimationActive={true}
          animationDuration={600}
        />

        <Line
          type="monotone"
          dataKey="equityValue"
          stroke="#00ff87"
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 4, fill: '#00ff87', stroke: '#030303', strokeWidth: 2 }}
          isAnimationActive={true}
          animationDuration={600}
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}

// ─── Default export (backward compatibility shim) ─────────────────
/**
 * DEPRECATED default export — retained so any legacy import keeps
 * compiling. Renders the closed-trade curve. New callers should use
 * the named exports `TrueEquityCurve` / `ClosedTradeEquityCurve`.
 */
export default function EquityCurveChart({ data, height = CHART_HEIGHT }: {
  data: EquityPoint[];
  height?: number;
}) {
  return <ClosedTradeEquityCurve data={data} height={height} />;
}

export { RangeSelector };
