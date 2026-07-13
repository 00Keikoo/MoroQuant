export interface LogEntry {
  timestamp: string;
  level: 'INFO' | 'WARN' | 'ERROR' | 'DEBUG' | 'BUSY';
  message: string;
  source?: string;
}

export const logsData = {
  entries: [
    {
      timestamp: '14:02:33.411',
      level: 'INFO' as const,
      message: 'Validation successful. 14,201,992 records synced to memory cluster.',
      source: 'validator',
    },
    {
      timestamp: '14:02:34.002',
      level: 'INFO' as const,
      message: 'Outlier filter pass 1 complete. 5,122 records purged (threshold: 3.5sigma).',
      source: 'filter',
    },
    {
      timestamp: '14:02:34.119',
      level: 'BUSY' as const,
      message: 'Initiating Model Signal Generation on H100 cluster unit #4...',
      source: 'trainer',
    },
    {
      timestamp: '14:02:35.882',
      level: 'BUSY' as const,
      message: 'Epoch 12/50: Loss 0.0021 | Accuracy 99.1%',
      source: 'trainer',
    },
    {
      timestamp: '14:02:37.221',
      level: 'INFO' as const,
      message: 'Checkpoint saved: model_v4_epoch_12.pth',
      source: 'trainer',
    },
    {
      timestamp: '14:02:38.003',
      level: 'WARN' as const,
      message: 'GPU temperature rising: 82°C on unit #3',
      source: 'monitor',
    },
    {
      timestamp: '14:02:39.115',
      level: 'DEBUG' as const,
      message: 'Memory allocation: 74.1 GB / 80 GB VRAM',
      source: 'system',
    },
    {
      timestamp: '14:02:40.421',
      level: 'ERROR' as const,
      message: 'Node #11 Fan Failure - Critical temperature alert',
      source: 'hardware',
    },
  ] as LogEntry[],
};
