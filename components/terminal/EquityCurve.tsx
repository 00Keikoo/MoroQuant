'use client';

import { useQuery } from '@tanstack/react-query';
import { getEquityHistory } from '@/lib/services/terminalService';
import { useTradingMode } from '@/lib/hooks/useTradingMode';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Area, AreaChart } from 'recharts';

export default function EquityCurve() {
  const { mode } = useTradingMode();

  const { data: equityData, isLoading } = useQuery({
    queryKey: ['terminal-equity-history', mode],
    queryFn: () => getEquityHistory(mode || 'OFF'),
    enabled: mode !== null && mode !== 'OFF',
    refetchInterval: 10000,
  });

  if (isLoading) {
    return (
      <div className="bg-[#141414] border border-[#262626] rounded-sm p-4 h-[400px] flex items-center justify-center">
        <div className="text-[#666666] text-xs">Loading equity curve...</div>
      </div>
    );
  }

  if (!equityData || equityData.length === 0) {
    return (
      <div className="bg-[#141414] border border-[#262626] rounded-sm p-4 h-[400px] flex items-center justify-center">
        <div className="text-[#666666] text-xs">No equity data available</div>
      </div>
    );
  }

  // Calculate peak and drawdown
  const chartData = equityData.map((point) => {
    return {
      timestamp: point.timestamp,
      equity: point.equity,
      cumulative_pnl: point.cumulative_pnl,
      displayTime: new Date(point.timestamp).toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        hour12: false
      }),
    };
  });

  let peak = chartData[0]?.equity || 0;
  const dataWithDrawdown = chartData.map((point) => {
    if (point.equity > peak) peak = point.equity;
    const drawdown = peak > 0 ? ((point.equity - peak) / peak) * 100 : 0;
    return { ...point, drawdown, peak };
  });

  const startingEquity = chartData[0]?.equity || 0;
  const currentEquity = chartData[chartData.length - 1]?.equity || 0;
  const totalReturn = startingEquity > 0 ? ((currentEquity - startingEquity) / startingEquity) * 100 : 0;

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-[#0e0e0e] border border-[#262626] p-2 rounded-sm text-xs font-mono">
          <div className="text-[#666666] mb-1">{data.displayTime}</div>
          <div className="text-white">Equity: ${data.equity.toFixed(2)}</div>
          <div className="text-[#A1A1A1]">PnL: ${data.cumulative_pnl.toFixed(2)}</div>
          {data.drawdown < 0 && (
            <div className="text-red-500">Drawdown: {data.drawdown.toFixed(2)}%</div>
          )}
        </div>
      );
    }
    return null;
  };

  return (
    <div className="bg-[#141414] border border-[#262626] rounded-sm p-4">
      <div className="flex justify-between items-center mb-3">
        <div className="text-xs font-bold text-[#666666] tracking-wider">EQUITY CURVE</div>
        <div className="flex items-center gap-4 text-xs font-mono">
          <div>
            <span className="text-[#666666]">Start: </span>
            <span className="text-white">${startingEquity.toFixed(2)}</span>
          </div>
          <div>
            <span className="text-[#666666]">Current: </span>
            <span className="text-white">${currentEquity.toFixed(2)}</span>
          </div>
          <div>
            <span className="text-[#666666]">Return: </span>
            <span className={totalReturn >= 0 ? 'text-green-500' : 'text-red-500'}>
              {totalReturn >= 0 ? '+' : ''}{totalReturn.toFixed(2)}%
            </span>
          </div>
        </div>
      </div>

      <ResponsiveContainer width="100%" height={350}>
        <AreaChart data={dataWithDrawdown} margin={{ top: 5, right: 5, left: 5, bottom: 5 }}>
          <defs>
            <linearGradient id="equityGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#FF6B00" stopOpacity={0.3}/>
              <stop offset="95%" stopColor="#FF6B00" stopOpacity={0}/>
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#262626" />
          <XAxis
            dataKey="displayTime"
            stroke="#666666"
            style={{ fontSize: '10px', fontFamily: 'JetBrains Mono' }}
            tick={{ fill: '#666666' }}
          />
          <YAxis
            stroke="#666666"
            style={{ fontSize: '10px', fontFamily: 'JetBrains Mono' }}
            tick={{ fill: '#666666' }}
            domain={['auto', 'auto']}
          />
          <Tooltip content={<CustomTooltip />} />
          <Area
            type="monotone"
            dataKey="equity"
            stroke="#FF6B00"
            strokeWidth={2}
            fill="url(#equityGradient)"
          />
          <Line
            type="monotone"
            dataKey="peak"
            stroke="#666666"
            strokeWidth={1}
            strokeDasharray="3 3"
            dot={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
