'use client';

import { logsData } from '@/lib/mock-data/logs';
import { TradingTopBar, TradingSidebar, TradingLayout } from '@/components/trading/shared';

export default function LogsPage() {
  const { entries } = logsData;

  const navItems = [
    { icon: 'dashboard', label: 'Cluster Health' },
    { icon: 'psychology', label: 'Training Pipelines' },
    { icon: 'swap_horiz', label: 'Edge Routers' },
    { icon: 'pie_chart', label: 'Node Resource Allocation' },
    { icon: 'gpp_maybe', label: 'Security Firewall' },
    { icon: 'terminal', label: 'Service Logs', active: true },
    { icon: 'insights', label: 'Alert History' },
  ];

  const getLevelColor = (level: string) => {
    switch (level) {
      case 'INFO':
        return 'text-green-500';
      case 'WARN':
        return 'text-primary';
      case 'ERROR':
        return 'text-error';
      case 'DEBUG':
        return 'text-secondary';
      case 'BUSY':
        return 'text-primary';
      default:
        return 'text-secondary';
    }
  };

  return (
    <TradingLayout
      topBar={<TradingTopBar searchPlaceholder="Search Logs..." />}
      sidebar={
        <TradingSidebar
          items={navItems}
          footer={
            <div className="px-lg">
              <p className="font-label-caps text-label-caps text-secondary mb-sm uppercase tracking-widest">Active Jobs</p>
              <div className="flex flex-col gap-xs">
                <div className="bg-surface-container-lowest p-xs border border-outline-variant flex items-center justify-between">
                  <span className="font-code-sm text-code-sm">TRD_ALPHA_V4</span>
                  <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
                </div>
                <div className="bg-surface-container-lowest p-xs border border-outline-variant flex items-center justify-between">
                  <span className="font-code-sm text-code-sm">BKLT_SIM_882</span>
                  <span className="w-2 h-2 bg-primary rounded-full"></span>
                </div>
              </div>
            </div>
          }
        />
      }
    >
      <div className="flex flex-col h-full overflow-hidden">
        <div className="flex items-center justify-between px-lg py-sm border-b border-outline-variant bg-surface-container-low">
          <div className="flex items-center gap-md">
            <span className="font-label-caps text-label-caps text-secondary">SYSTEM LOGS [STDOUT]</span>
            <div className="flex gap-xs">
              <button className="px-sm py-xs bg-surface-container-high border border-outline-variant font-code-sm text-code-sm text-secondary hover:text-on-surface">
                ALL
              </button>
              <button className="px-sm py-xs bg-surface-container border border-outline-variant font-code-sm text-code-sm text-secondary hover:text-on-surface">
                INFO
              </button>
              <button className="px-sm py-xs bg-surface-container border border-outline-variant font-code-sm text-code-sm text-secondary hover:text-on-surface">
                WARN
              </button>
              <button className="px-sm py-xs bg-surface-container border border-outline-variant font-code-sm text-code-sm text-secondary hover:text-on-surface">
                ERROR
              </button>
            </div>
          </div>
          <div className="flex gap-md">
            <button className="material-symbols-outlined text-[14px] cursor-pointer hover:text-primary">
              search
            </button>
            <button className="material-symbols-outlined text-[14px] cursor-pointer hover:text-primary">
              filter_list
            </button>
            <button className="material-symbols-outlined text-[14px] cursor-pointer hover:text-primary">
              download
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-sm bg-[#090909] font-code-sm text-code-sm">
          {entries.map((entry, index) => (
            <div key={index} className="flex gap-md text-secondary py-1 hover:bg-surface-container-lowest">
              <span className="text-outline">{entry.timestamp}</span>
              <span className={getLevelColor(entry.level)}>[{entry.level}]</span>
              {entry.source && <span className="text-outline-variant">{entry.source}:</span>}
              <span className="flex-1">{entry.message}</span>
            </div>
          ))}
        </div>

        <div className="px-lg py-sm border-t border-outline-variant bg-surface-container-lowest">
          <div className="flex items-center gap-md font-code-sm text-code-sm">
            <span className="text-green-500 flex items-center gap-xs">
              <span className="w-2 h-2 bg-green-500 rounded-full"></span>
              Streaming
            </span>
            <span className="text-secondary">{entries.length} lines</span>
            <button className="ml-auto flex items-center gap-xs px-md py-1 bg-surface-container-highest border border-outline-variant hover:text-on-surface transition-colors">
              <span className="material-symbols-outlined text-[16px]">pause</span>
              <span className="font-label-caps text-label-caps">Pause</span>
            </button>
          </div>
        </div>
      </div>
    </TradingLayout>
  );
}
