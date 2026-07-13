export interface SystemSetting {
  key: string;
  value: string | number | boolean;
  type: 'string' | 'number' | 'boolean' | 'select';
  description: string;
  options?: string[];
}

export const settingsData = {
  general: [
    {
      key: 'system.name',
      value: 'QuantOS',
      type: 'string' as const,
      description: 'System display name',
    },
    {
      key: 'system.environment',
      value: 'production',
      type: 'select' as const,
      description: 'Deployment environment',
      options: ['development', 'staging', 'production'],
    },
    {
      key: 'system.debug',
      value: false,
      type: 'boolean' as const,
      description: 'Enable debug logging',
    },
  ] as SystemSetting[],
  performance: [
    {
      key: 'cluster.max_workers',
      value: 16,
      type: 'number' as const,
      description: 'Maximum concurrent workers',
    },
    {
      key: 'cluster.memory_limit',
      value: 2048,
      type: 'number' as const,
      description: 'Memory limit per node (GB)',
    },
    {
      key: 'training.batch_size',
      value: 256,
      type: 'number' as const,
      description: 'Training batch size',
    },
  ] as SystemSetting[],
  alerts: [
    {
      key: 'alerts.cpu_threshold',
      value: 90,
      type: 'number' as const,
      description: 'CPU usage alert threshold (%)',
    },
    {
      key: 'alerts.memory_threshold',
      value: 85,
      type: 'number' as const,
      description: 'Memory usage alert threshold (%)',
    },
    {
      key: 'alerts.enabled',
      value: true,
      type: 'boolean' as const,
      description: 'Enable system alerts',
    },
  ] as SystemSetting[],
};
