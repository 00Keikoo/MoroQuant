'use client';

import { workersData } from '@/lib/mock-data/workers';
import { TradingTopBar, TradingSidebar, TradingLayout } from '@/components/trading/shared';

export default function WorkersPage() {
  const { cluster, nodes } = workersData;

  const navItems = [
    { icon: 'dashboard', label: 'Cluster Health' },
    { icon: 'psychology', label: 'Training Pipelines' },
    { icon: 'swap_horiz', label: 'Edge Routers' },
    { icon: 'pie_chart', label: 'Node Resource Allocation', active: true },
    { icon: 'gpp_maybe', label: 'Security Firewall' },
    { icon: 'terminal', label: 'Service Logs' },
    { icon: 'insights', label: 'Alert History' },
  ];

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'online':
        return 'bg-green-500';
      case 'busy':
        return 'bg-primary';
      case 'offline':
        return 'bg-secondary';
      case 'error':
        return 'bg-error';
      default:
        return 'bg-secondary';
    }
  };

  const cpuPercent = ((cluster.usedCPU / cluster.totalCPU) * 100).toFixed(1);
  const memoryPercent = ((cluster.usedMemory / cluster.totalMemory) * 100).toFixed(1);
  const gpuPercent = ((cluster.usedGPU / cluster.totalGPU) * 100).toFixed(1);

  return (
    <TradingLayout
      topBar={<TradingTopBar searchPlaceholder="Search Nodes..." />}
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
        <div className="px-lg py-lg border-b border-outline-variant bg-surface-container-low">
          <h1 className="font-display-lg text-display-lg mb-lg">Worker Nodes</h1>

          <div className="grid grid-cols-4 gap-md">
            <div className="bg-surface-container border border-outline-variant p-md">
              <span className="font-label-caps text-label-caps text-secondary block mb-xs">TOTAL NODES</span>
              <span className="font-display-lg text-display-lg text-on-surface">{cluster.totalNodes}</span>
              <span className="font-code-sm text-code-sm text-green-500 ml-sm">
                {cluster.activeNodes} active
              </span>
            </div>

            <div className="bg-surface-container border border-outline-variant p-md">
              <span className="font-label-caps text-label-caps text-secondary block mb-xs">CPU USAGE</span>
              <span className="font-display-lg text-display-lg text-on-surface">{cpuPercent}%</span>
              <div className="mt-xs h-1 bg-surface-container-high">
                <div className="h-full bg-primary" style={{ width: `${cpuPercent}%` }}></div>
              </div>
            </div>

            <div className="bg-surface-container border border-outline-variant p-md">
              <span className="font-label-caps text-label-caps text-secondary block mb-xs">MEMORY</span>
              <span className="font-display-lg text-display-lg text-on-surface">{memoryPercent}%</span>
              <div className="mt-xs h-1 bg-surface-container-high">
                <div className="h-full bg-primary" style={{ width: `${memoryPercent}%` }}></div>
              </div>
            </div>

            <div className="bg-surface-container border border-outline-variant p-md">
              <span className="font-label-caps text-label-caps text-secondary block mb-xs">GPU USAGE</span>
              <span className="font-display-lg text-display-lg text-on-surface">{gpuPercent}%</span>
              <div className="mt-xs h-1 bg-surface-container-high">
                <div className="h-full bg-primary" style={{ width: `${gpuPercent}%` }}></div>
              </div>
            </div>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-lg">
          <div className="bg-surface-container border border-outline-variant">
            <div className="grid grid-cols-[2fr,1fr,1fr,1fr,1fr,1fr] gap-md px-md py-sm border-b border-outline-variant bg-surface-container-low">
              <span className="font-label-caps text-label-caps text-secondary">NODE</span>
              <span className="font-label-caps text-label-caps text-secondary">STATUS</span>
              <span className="font-label-caps text-label-caps text-secondary">CPU</span>
              <span className="font-label-caps text-label-caps text-secondary">MEMORY</span>
              <span className="font-label-caps text-label-caps text-secondary">GPU</span>
              <span className="font-label-caps text-label-caps text-secondary">JOBS</span>
            </div>
            {nodes.map((node) => (
              <div
                key={node.id}
                className="grid grid-cols-[2fr,1fr,1fr,1fr,1fr,1fr] gap-md px-md py-sm border-b border-outline-variant last:border-b-0 hover:bg-surface-container-high transition-colors"
              >
                <div className="flex flex-col">
                  <span className="font-body-base text-on-surface">{node.name}</span>
                  <span className="font-code-sm text-code-sm text-secondary">{node.id}</span>
                </div>
                <div className="flex items-center gap-xs">
                  <span className={`w-2 h-2 rounded-full ${getStatusColor(node.status)}`}></span>
                  <span className="font-data-tabular text-data-tabular uppercase text-secondary">
                    {node.status}
                  </span>
                </div>
                <span className="font-data-tabular text-data-tabular text-on-surface flex items-center">
                  {node.cpu.toFixed(1)}%
                </span>
                <span className="font-data-tabular text-data-tabular text-on-surface flex items-center">
                  {node.memory.toFixed(1)}%
                </span>
                <span className="font-data-tabular text-data-tabular text-on-surface flex items-center">
                  {node.gpu ? `${node.gpu.toFixed(1)}%` : 'N/A'}
                </span>
                <span className="font-data-tabular text-data-tabular text-secondary flex items-center">
                  {node.activeJobs}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </TradingLayout>
  );
}
