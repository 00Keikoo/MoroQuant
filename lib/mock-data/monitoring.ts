export interface SystemHealth {
  api: 'operational' | 'degraded' | 'down';
  database: 'operational' | 'degraded' | 'down';
  cache: 'operational' | 'degraded' | 'down';
  queue: 'operational' | 'degraded' | 'down';
}

export interface ResourceMetrics {
  cpu: number;
  memory: number;
  disk: number;
  network: {
    in: number;
    out: number;
  };
  latency: {
    p50: number;
    p95: number;
    p99: number;
  };
}

export interface NodeHeatmap {
  id: number;
  status: 'healthy' | 'busy' | 'critical';
}

export const monitoringData = {
  health: {
    api: 'operational' as const,
    database: 'operational' as const,
    cache: 'operational' as const,
    queue: 'operational' as const,
  } as SystemHealth,
  metrics: {
    cpu: 68.2,
    memory: 74.1,
    disk: 45.3,
    network: {
      in: 8.2,
      out: 4.2,
    },
    latency: {
      p50: 0.4,
      p95: 0.8,
      p99: 1.2,
    },
  } as ResourceMetrics,
  uptime: {
    days: 14,
    hours: 2,
    minutes: 11,
  },
  heatmap: Array.from({ length: 16 }, (_, i) => ({
    id: i + 1,
    status: i === 10 ? ('critical' as const) : i === 4 ? ('busy' as const) : ('healthy' as const),
  })) as NodeHeatmap[],
};
