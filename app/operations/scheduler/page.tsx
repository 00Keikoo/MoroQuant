'use client';

import { schedulerData } from '@/lib/mock-data/scheduler';
import { TradingTopBar, TradingSidebar, TradingLayout } from '@/components/trading/shared';

export default function SchedulerPage() {
  const { tasks } = schedulerData;

  const navItems = [
    { icon: 'dashboard', label: 'Cluster Health' },
    { icon: 'psychology', label: 'Training Pipelines', active: true },
    { icon: 'swap_horiz', label: 'Edge Routers' },
    { icon: 'pie_chart', label: 'Node Resource Allocation' },
    { icon: 'gpp_maybe', label: 'Security Firewall' },
    { icon: 'terminal', label: 'Service Logs' },
    { icon: 'insights', label: 'Alert History' },
  ];

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running':
        return 'text-green-500';
      case 'idle':
        return 'text-secondary';
      case 'error':
        return 'text-error';
      case 'pending':
        return 'text-primary';
      default:
        return 'text-secondary';
    }
  };

  return (
    <TradingLayout
      topBar={<TradingTopBar searchPlaceholder="Search Tasks..." />}
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
        <div className="flex items-center justify-between px-lg py-lg border-b border-outline-variant bg-surface-container-low">
          <div>
            <h1 className="font-display-lg text-display-lg">Scheduled Tasks</h1>
            <p className="text-body-base text-secondary">Manage automated pipeline executions</p>
          </div>
          <div className="flex gap-sm">
            <button className="flex items-center gap-xs px-md py-1 bg-surface-container-highest border border-outline-variant hover:text-on-surface transition-colors">
              <span className="material-symbols-outlined text-[16px]">add</span>
              <span className="font-label-caps text-label-caps">New Task</span>
            </button>
            <button className="flex items-center gap-xs px-md py-1 bg-primary-container text-on-primary-container border border-transparent transition-opacity">
              <span className="material-symbols-outlined text-[16px]">play_arrow</span>
              <span className="font-label-caps text-label-caps uppercase">Run All</span>
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-lg">
          <div className="bg-surface-container border border-outline-variant">
            <div className="grid grid-cols-[2fr,1fr,1fr,1fr,1fr,auto] gap-md px-md py-sm border-b border-outline-variant bg-surface-container-low">
              <span className="font-label-caps text-label-caps text-secondary">TASK NAME</span>
              <span className="font-label-caps text-label-caps text-secondary">STATUS</span>
              <span className="font-label-caps text-label-caps text-secondary">SCHEDULE</span>
              <span className="font-label-caps text-label-caps text-secondary">LAST RUN</span>
              <span className="font-label-caps text-label-caps text-secondary">DURATION</span>
              <span className="font-label-caps text-label-caps text-secondary">ACTIONS</span>
            </div>
            {tasks.map((task) => (
              <div
                key={task.id}
                className="grid grid-cols-[2fr,1fr,1fr,1fr,1fr,auto] gap-md px-md py-sm border-b border-outline-variant last:border-b-0 hover:bg-surface-container-high transition-colors"
              >
                <div className="flex flex-col">
                  <span className="font-body-base text-on-surface">{task.name}</span>
                  <span className="font-code-sm text-code-sm text-secondary">{task.id}</span>
                </div>
                <div className="flex items-center">
                  <span className={`font-data-tabular text-data-tabular uppercase ${getStatusColor(task.status)}`}>
                    {task.status}
                  </span>
                </div>
                <span className="font-code-sm text-code-sm text-secondary flex items-center">{task.schedule}</span>
                <span className="font-code-sm text-code-sm text-secondary flex items-center">
                  {new Date(task.lastRun).toLocaleTimeString()}
                </span>
                <span className="font-code-sm text-code-sm text-secondary flex items-center">{task.duration}</span>
                <div className="flex items-center gap-xs">
                  <button className="material-symbols-outlined text-[18px] text-secondary hover:text-primary cursor-pointer">
                    play_arrow
                  </button>
                  <button className="material-symbols-outlined text-[18px] text-secondary hover:text-primary cursor-pointer">
                    edit
                  </button>
                  <button className="material-symbols-outlined text-[18px] text-secondary hover:text-error cursor-pointer">
                    delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </TradingLayout>
  );
}
