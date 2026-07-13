export interface ScheduledTask {
  id: string;
  name: string;
  schedule: string;
  status: 'running' | 'idle' | 'error' | 'pending';
  lastRun: string;
  nextRun: string;
  duration: string;
  success: boolean;
}

export const schedulerData = {
  tasks: [
    {
      id: 'TRD_ALPHA_V4',
      name: 'Trading Alpha V4 Pipeline',
      schedule: '0 */4 * * *',
      status: 'running' as const,
      lastRun: '2026-07-13T14:02:33Z',
      nextRun: '2026-07-13T18:00:00Z',
      duration: '12m 41s',
      success: true,
    },
    {
      id: 'BKLT_SIM_882',
      name: 'Backtest Simulation 882',
      schedule: '0 2 * * *',
      status: 'idle' as const,
      lastRun: '2026-07-13T02:00:00Z',
      nextRun: '2026-07-14T02:00:00Z',
      duration: '3m 22s',
      success: true,
    },
    {
      id: 'DATA_SYNC_001',
      name: 'Market Data Sync',
      schedule: '*/15 * * * *',
      status: 'idle' as const,
      lastRun: '2026-07-13T15:45:00Z',
      nextRun: '2026-07-13T16:00:00Z',
      duration: '45s',
      success: true,
    },
    {
      id: 'MODEL_RETRAIN',
      name: 'Model Retraining Job',
      schedule: '0 0 * * 0',
      status: 'pending' as const,
      lastRun: '2026-07-07T00:00:00Z',
      nextRun: '2026-07-14T00:00:00Z',
      duration: '2h 14m',
      success: true,
    },
  ],
};
