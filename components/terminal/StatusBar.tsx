'use client';

import { useQuery } from '@tanstack/react-query';
import { useTradingMode } from '@/lib/hooks/useTradingMode';
import { getSystemStatus } from '@/lib/api/system-status';
import type { SystemComponentStatus } from '@/lib/types/system-status';

interface SystemStatus {
  component: string;
  status: SystemComponentStatus;
  color: string;
  value?: string;
}

export default function StatusBar() {
  const { mode } = useTradingMode();

  const { data: systemStatus } = useQuery({
    queryKey: ['system-status'],
    queryFn: getSystemStatus,
    refetchInterval: 3000,
  });

  const getModeColor = () => {
    if (mode === 'LIVE') return 'text-red-500';
    if (mode === 'PAPER') return 'text-green-500';
    return 'text-gray-500';
  };

  const getStatusColor = (status: SystemComponentStatus): string => {
    switch (status) {
      case 'RUNNING':
      case 'CONNECTED':
      case 'HEALTHY':
        return 'text-green-500';
      case 'STOPPED':
      case 'DISCONNECTED':
      case 'DOWN':
        return 'text-red-500';
      case 'UNKNOWN':
      default:
        return 'text-gray-500';
    }
  };

  const statuses: SystemStatus[] = [
    {
      component: 'Scheduler',
      status: systemStatus?.scheduler || 'UNKNOWN',
      color: getStatusColor(systemStatus?.scheduler || 'UNKNOWN'),
    },
    {
      component: 'Paper Broker',
      status: systemStatus?.paper_broker || 'UNKNOWN',
      color: getStatusColor(systemStatus?.paper_broker || 'UNKNOWN'),
    },
    {
      component: 'Market Data',
      status: systemStatus?.market_data || 'UNKNOWN',
      color: getStatusColor(systemStatus?.market_data || 'UNKNOWN'),
    },
    {
      component: 'Binance WS',
      status: systemStatus?.binance_ws || 'UNKNOWN',
      color: getStatusColor(systemStatus?.binance_ws || 'UNKNOWN'),
    },
    {
      component: 'API',
      status: systemStatus?.api || 'UNKNOWN',
      color: getStatusColor(systemStatus?.api || 'UNKNOWN'),
    },
    {
      component: 'DB',
      status: systemStatus?.db || 'UNKNOWN',
      color: getStatusColor(systemStatus?.db || 'UNKNOWN'),
    },
  ];

  const StatusIndicator = ({ status }: { status: SystemStatus }) => (
    <div className="flex items-center gap-1.5">
      <span className="text-[#666666]">{status.component}:</span>
      <span className={`${status.color} flex items-center gap-1`}>
        <span className="text-xs">●</span>
        <span className="font-bold">{status.status}</span>
        {status.value && <span className="text-[#A1A1A1]">{status.value}</span>}
      </span>
    </div>
  );

  return (
    <div className="fixed bottom-0 left-0 right-0 bg-[#0e0e0e] border-t border-[#262626] px-4 py-1.5 z-50">
      <div className="flex items-center gap-4 text-[10px] font-mono">
        {/* Mode & Model */}
        <div className="flex items-center gap-1.5">
          <span className="text-[#666666]">MODE:</span>
          <span className={`font-bold ${getModeColor()}`}>{mode}</span>
        </div>

        <div className="w-px h-3 bg-[#262626]" />

        <div className="flex items-center gap-1.5">
          <span className="text-[#666666]">MODEL:</span>
          <span className="text-white">BTCUSDT_1H_XGB_v1.3</span>
        </div>

        <div className="w-px h-3 bg-[#262626]" />

        {/* System Statuses */}
        <div className="flex items-center gap-4 flex-1">
          {statuses.slice(0, 3).map((status) => (
            <StatusIndicator key={status.component} status={status} />
          ))}
        </div>

        <div className="w-px h-3 bg-[#262626]" />

        {/* Connection & Performance */}
        <div className="flex items-center gap-4">
          {statuses.slice(2, 4).map((status) => (
            <StatusIndicator key={status.component} status={status} />
          ))}

          <div className="flex items-center gap-1.5">
            <span className="text-[#666666]">Latency:</span>
            <span className={`font-bold ${systemStatus?.latency_ms ?
              (systemStatus.latency_ms < 100 ? 'text-green-500' :
               systemStatus.latency_ms < 300 ? 'text-yellow-500' : 'text-red-500')
              : 'text-gray-500'}`}
            >
              {systemStatus?.latency_ms ? `${systemStatus.latency_ms}ms` : '-'}
            </span>
          </div>

          <div className="flex items-center gap-1.5">
            <span className="text-[#666666]">Last Candle:</span>
            <span className="text-[#A1A1A1]">
              {systemStatus?.last_candle ||
                new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit' })}
            </span>
          </div>
        </div>

        <div className="w-px h-3 bg-[#262626]" />

        {/* Health */}
        <div className="flex items-center gap-4">
          {statuses.slice(4).map((status) => (
            <StatusIndicator key={status.component} status={status} />
          ))}
        </div>
      </div>
    </div>
  );
}
