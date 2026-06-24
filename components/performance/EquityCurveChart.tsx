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
import type { EquityPoint } from '@/lib/services/performanceService';

interface EquityCurveChartProps {
  data: EquityPoint[];
  height?: number;
}

interface TooltipPayloadEntry {
  payload: EquityPoint;
  value: number;
}

interface ChartTooltipProps {
  active?: boolean;
  payload?: TooltipPayloadEntry[];
}

function ChartTooltip({ active, payload }: ChartTooltipProps) {
  if (!active || !payload || payload.length === 0) return null;
  const point = payload[0].payload;
  const date = new Date(point.timestamp).toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
  // Equity is the absolute account balance (starting_balance + cumulative
  // realized PnL). Fall back to cumulative_pnl only for legacy payloads.
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
        Trade #{point.trade_count} · {date}
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

/**
 * Equity curve rendered as a smooth line chart with gradient fill below the line.
 * Uses ComposedChart to overlay an Area (fill) under the Line (stroke).
 *
 * Semantics: the Y-axis is ABSOLUTE ACCOUNT EQUITY
 *   equity[n] = starting_balance + Σ net_realized_pnl[0:n]
 * NOT cumulative PnL (which would start at 0). Falls back to cumulative_pnl
 * only for legacy payloads that lack the `equity` field.
 */
export default function EquityCurveChart({ data, height = 360 }: EquityCurveChartProps) {
  // Sort by trade_count ascending so the line progresses chronologically.
  // Derive `equityValue` = absolute account equity per point.
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
        No equity data yet
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={height}>
      <ComposedChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 5 }}>
        <defs>
          <linearGradient id="equityFillPositive" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#00ff87" stopOpacity={0.25} />
            <stop offset="100%" stopColor="#00ff87" stopOpacity={0} />
          </linearGradient>
          <linearGradient id="equityFillNegative" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#ff0055" stopOpacity={0.25} />
            <stop offset="100%" stopColor="#ff0055" stopOpacity={0} />
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

        <Tooltip content={<ChartTooltip />} cursor={{ stroke: '#00f0ff', strokeWidth: 1, strokeDasharray: '4 4' }} />

        <Area
          type="monotone"
          dataKey="equityValue"
          stroke="none"
          fill="url(#equityFillPositive)"
          isAnimationActive={true}
          animationDuration={600}
        />

        <Line
          type="monotone"
          dataKey="equityValue"
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
