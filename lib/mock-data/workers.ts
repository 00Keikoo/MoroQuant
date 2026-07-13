export interface WorkerNode {
  id: string;
  name: string;
  status: 'online' | 'offline' | 'busy' | 'error';
  cpu: number;
  memory: number;
  gpu?: number;
  uptime: string;
  activeJobs: number;
}

export interface ClusterMetrics {
  totalNodes: number;
  activeNodes: number;
  totalCPU: number;
  usedCPU: number;
  totalMemory: number;
  usedMemory: number;
  totalGPU: number;
  usedGPU: number;
}

export const workersData = {
  cluster: {
    totalNodes: 16,
    activeNodes: 15,
    totalCPU: 256,
    usedCPU: 174,
    totalMemory: 2048,
    usedMemory: 1420,
    totalGPU: 32,
    usedGPU: 22,
  } as ClusterMetrics,
  nodes: [
    {
      id: 'NODE_01',
      name: 'CLUSTER_BRAVO_09',
      status: 'busy' as const,
      cpu: 68.2,
      memory: 74.1,
      gpu: 92.3,
      uptime: '14d 02h 11m',
      activeJobs: 2,
    },
    {
      id: 'NODE_02',
      name: 'CLUSTER_BRAVO_10',
      status: 'online' as const,
      cpu: 12.4,
      memory: 23.8,
      gpu: 0,
      uptime: '14d 02h 11m',
      activeJobs: 0,
    },
    {
      id: 'NODE_03',
      name: 'CLUSTER_ALPHA_01',
      status: 'busy' as const,
      cpu: 89.1,
      memory: 91.2,
      gpu: 88.7,
      uptime: '7d 14h 32m',
      activeJobs: 3,
    },
    {
      id: 'NODE_04',
      name: 'CLUSTER_ALPHA_02',
      status: 'online' as const,
      cpu: 5.2,
      memory: 18.3,
      uptime: '7d 14h 32m',
      activeJobs: 0,
    },
    {
      id: 'NODE_05',
      name: 'CLUSTER_GAMMA_11',
      status: 'error' as const,
      cpu: 0,
      memory: 0,
      uptime: '0d 00h 00m',
      activeJobs: 0,
    },
  ] as WorkerNode[],
};
