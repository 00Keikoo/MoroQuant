'use client';

import { monitoringData } from '@/lib/mock-data/monitoring';
import { TradingTopBar, TradingSidebar, TradingLayout } from '@/components/trading/shared';

export default function MonitoringPage() {
  const { health, metrics, uptime, heatmap } = monitoringData;

  const navItems = [
    { icon: 'dashboard', label: 'Cluster Health', active: true },
    { icon: 'psychology', label: 'Training Pipelines' },
    { icon: 'swap_horiz', label: 'Edge Routers' },
    { icon: 'pie_chart', label: 'Node Resource Allocation' },
    { icon: 'gpp_maybe', label: 'Security Firewall' },
    { icon: 'terminal', label: 'Service Logs' },
    { icon: 'insights', label: 'Alert History' },
  ];

  const getHealthColor = (status: string) => {
    switch (status) {
      case 'operational':
        return 'text-green-500';
      case 'degraded':
        return 'text-primary';
      case 'down':
        return 'text-error';
      default:
        return 'text-secondary';
    }
  };

  const getHeatmapColor = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'bg-green-900 border-green-500/50';
      case 'busy':
        return 'bg-primary border-primary/50';
      case 'critical':
        return 'bg-[#93000a] border-[#ffb4ab]/50 animate-pulse';
      default:
        return 'bg-surface-container border-outline-variant';
    }
  };

  return (
    <TradingLayout
      topBar={<TradingTopBar searchPlaceholder="Search Resources..." />}
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
      <div className="flex h-full overflow-hidden">
        <div className="flex-1 flex flex-col overflow-hidden">
          <div className="px-lg py-lg border-b border-outline-variant bg-surface-container-low">
            <h1 className="font-display-lg text-display-lg mb-sm">System Health</h1>
            <div className="flex items-center gap-md">
              <span className="text-green-500 flex items-center gap-xs">
                <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                System Status: Operational
              </span>
              <div className="h-3 w-px bg-outline-variant"></div>
              <span className="text-secondary font-code-sm text-code-sm">
                Uptime: {uptime.days}d {uptime.hours}h {uptime.minutes}m
              </span>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto p-lg">
            <div className="grid grid-cols-2 gap-md mb-lg">
              <div className="bg-surface-container border border-outline-variant p-md">
                <span className="font-label-caps text-label-caps text-secondary block mb-xs">SERVICE STATUS</span>
                <div className="space-y-sm mt-md">
                  <div className="flex justify-between items-center">
                    <span className="font-body-base text-on-surface">API</span>
                    <span className={`font-data-tabular text-data-tabular uppercase ${getHealthColor(health.api)}`}>
                      {health.api}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="font-body-base text-on-surface">Database</span>
                    <span className={`font-data-tabular text-data-tabular uppercase ${getHealthColor(health.database)}`}>
                      {health.database}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="font-body-base text-on-surface">Cache</span>
                    <span className={`font-data-tabular text-data-tabular uppercase ${getHealthColor(health.cache)}`}>
                      {health.cache}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="font-body-base text-on-surface">Queue</span>
                    <span className={`font-data-tabular text-data-tabular uppercase ${getHealthColor(health.queue)}`}>
                      {health.queue}
                    </span>
                  </div>
                </div>
              </div>

              <div className="bg-surface-container border border-outline-variant p-md">
                <span className="font-label-caps text-label-caps text-secondary block mb-xs">LATENCY (ms)</span>
                <div className="space-y-sm mt-md">
                  <div className="flex justify-between items-center">
                    <span className="font-body-base text-on-surface">p50</span>
                    <span className="font-data-tabular text-data-tabular text-green-400">
                      {metrics.latency.p50.toFixed(1)}ms
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="font-body-base text-on-surface">p95</span>
                    <span className="font-data-tabular text-data-tabular text-green-400">
                      {metrics.latency.p95.toFixed(1)}ms
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="font-body-base text-on-surface">p99</span>
                    <span className="font-data-tabular text-data-tabular text-primary">
                      {metrics.latency.p99.toFixed(1)}ms
                    </span>
                  </div>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-md">
              <div className="bg-surface-container border border-outline-variant p-md">
                <div className="flex justify-between items-end mb-sm">
                  <span className="font-label-caps text-label-caps text-secondary">CPU LOAD</span>
                  <span className="font-data-tabular text-data-tabular text-primary">{metrics.cpu.toFixed(1)}%</span>
                </div>
                <div className="h-16 bg-[#090909] border border-outline-variant relative flex items-end overflow-hidden p-[2px]">
                  {[20, 40, 35, 60, 55, 68, 72, 68].map((height, i) => (
                    <div
                      key={i}
                      className={`flex-1 mx-[1px] ${i === 7 ? 'bg-primary' : 'bg-primary/20'}`}
                      style={{ height: `${height}%` }}
                    ></div>
                  ))}
                </div>
              </div>

              <div className="bg-surface-container border border-outline-variant p-md">
                <div className="flex justify-between items-end mb-sm">
                  <span className="font-label-caps text-label-caps text-secondary">MEMORY USAGE</span>
                  <span className="font-data-tabular text-data-tabular text-secondary">{metrics.memory.toFixed(1)}%</span>
                </div>
                <div className="h-2 bg-surface-container-highest border border-outline-variant mt-auto">
                  <div className="h-full bg-primary" style={{ width: `${metrics.memory}%` }}></div>
                </div>
              </div>

              <div className="bg-surface-container border border-outline-variant p-md">
                <div className="flex justify-between items-end mb-sm">
                  <span className="font-label-caps text-label-caps text-secondary">THROUGHPUT</span>
                  <span className="font-data-tabular text-data-tabular text-green-400">
                    {(metrics.network.in + metrics.network.out).toFixed(1)} GB/s
                  </span>
                </div>
                <div className="space-y-xs mt-sm">
                  <div className="flex justify-between font-code-sm text-code-sm">
                    <span className="text-secondary">Network In</span>
                    <span className="text-on-surface">{metrics.network.in.toFixed(1)} GB/s</span>
                  </div>
                  <div className="flex justify-between font-code-sm text-code-sm">
                    <span className="text-secondary">Network Out</span>
                    <span className="text-on-surface">{metrics.network.out.toFixed(1)} GB/s</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <aside className="w-80 bg-surface-container-low border-l border-outline-variant flex flex-col overflow-hidden">
          <div className="p-lg border-b border-outline-variant">
            <h3 className="font-header-md text-header-md font-bold text-on-surface uppercase mb-sm">Inspector</h3>
            <p className="font-label-caps text-label-caps text-secondary">Active Resource: CLUSTER_BRAVO_09</p>
          </div>

          <div className="flex-1 overflow-y-auto p-lg space-y-lg">
            <section>
              <div className="flex justify-between items-end mb-sm">
                <span className="font-label-caps text-label-caps text-secondary">VRAM USAGE</span>
                <span className="font-data-tabular text-data-tabular text-secondary">74.1 GB / 80 GB</span>
              </div>
              <div className="h-2 bg-surface-container-highest border border-outline-variant">
                <div className="h-full bg-primary" style={{ width: '92%' }}></div>
              </div>
            </section>

            <section>
              <span className="font-label-caps text-label-caps text-secondary block mb-sm">NODE HEATMAP</span>
              <div className="grid grid-cols-8 gap-1">
                {heatmap.map((node) => (
                  <div
                    key={node.id}
                    className={`w-full aspect-square ${getHeatmapColor(node.status)}`}
                  ></div>
                ))}
              </div>
              {heatmap.find(n => n.status === 'critical') && (
                <p className="font-code-sm text-code-sm text-[#ffb4ab] mt-sm">
                  Critical: Node #{heatmap.find(n => n.status === 'critical')?.id} Fan Failure
                </p>
              )}
            </section>
          </div>

          <div className="p-lg bg-surface-container-highest">
            <button className="w-full py-md bg-transparent border border-outline text-secondary hover:text-on-surface hover:border-primary transition-all font-label-caps text-label-caps tracking-widest uppercase">
              Download Artifacts
            </button>
          </div>
        </aside>
      </div>
    </TradingLayout>
  );
}
