'use client';

import { useState } from 'react';
import { MQPanel, MQTable, MQStatusBadge, MQSearch, MQButton, MQChartContainer } from '@/components/mqds';
import { Filter, Table } from 'lucide-react';

type TimelineEvent = {
  id: string;
  timestamp: string;
  eventType: string;
  entity: string;
  entityId: string;
  action: string;
  user: string;
  metadata: string;
  status: 'SUCCESS' | 'FAILED' | 'WARNING' | 'INFO';
};

const mockTimelineEvents: TimelineEvent[] = [
  {
    id: 'evt_001',
    timestamp: '2026-07-12T14:30:00Z',
    eventType: 'EXPERIMENT',
    entity: 'LSTM_Market_Predictor',
    entityId: 'exp_2847',
    action: 'Training Started',
    user: 'research.team',
    metadata: 'Dataset: Q4_2025_Full',
    status: 'INFO'
  },
  {
    id: 'evt_002',
    timestamp: '2026-07-12T13:15:00Z',
    eventType: 'MODEL',
    entity: 'Ensemble_Multi_Strategy',
    entityId: 'mdl_004',
    action: 'Promoted to Production',
    user: 'ml.ops',
    metadata: 'Approval Score: 95%',
    status: 'SUCCESS'
  },
  {
    id: 'evt_003',
    timestamp: '2026-07-12T12:45:00Z',
    eventType: 'VALIDATION',
    entity: 'XGBoost_Ensemble',
    entityId: 'val_003',
    action: 'Validation Failed',
    user: 'quant.team',
    metadata: 'Accuracy: 58.9%',
    status: 'FAILED'
  },
  {
    id: 'evt_004',
    timestamp: '2026-07-12T11:20:00Z',
    eventType: 'CALIBRATION',
    entity: 'RandomForest_Classifier',
    entityId: 'cal_002',
    action: 'Recalibration Complete',
    user: 'ml.ops',
    metadata: 'ECE: 3.1%',
    status: 'SUCCESS'
  },
  {
    id: 'evt_005',
    timestamp: '2026-07-12T10:05:00Z',
    eventType: 'DATASET',
    entity: 'Sentiment_Analysis_v3',
    entityId: 'ds_015',
    action: 'Dataset Created',
    user: 'data.eng',
    metadata: 'Size: 2.4M rows',
    status: 'SUCCESS'
  },
  {
    id: 'evt_006',
    timestamp: '2026-07-12T09:30:00Z',
    eventType: 'FEATURE',
    entity: 'Volume_Momentum_Ratio',
    entityId: 'feat_128',
    action: 'Feature Deployed',
    user: 'research.team',
    metadata: 'Importance: 87%',
    status: 'SUCCESS'
  },
  {
    id: 'evt_007',
    timestamp: '2026-07-12T08:50:00Z',
    eventType: 'EXPERIMENT',
    entity: 'Transformer_Attention',
    entityId: 'exp_2846',
    action: 'Training Failed',
    user: 'research.team',
    metadata: 'Error: OOM',
    status: 'FAILED'
  },
  {
    id: 'evt_008',
    timestamp: '2026-07-12T07:15:00Z',
    eventType: 'MODEL',
    entity: 'LSTM_Market_Predictor',
    entityId: 'mdl_001',
    action: 'Model Registered',
    user: 'ml.ops',
    metadata: 'Version: v2.3',
    status: 'SUCCESS'
  },
  {
    id: 'evt_009',
    timestamp: '2026-07-12T06:00:00Z',
    eventType: 'PROMOTION',
    entity: 'GRU_Volatility_Model',
    entityId: 'prm_005',
    action: 'Promotion Pending',
    user: 'quant.team',
    metadata: 'Gates: 6/8',
    status: 'WARNING'
  },
  {
    id: 'evt_010',
    timestamp: '2026-07-12T04:45:00Z',
    eventType: 'DATASET',
    entity: 'Market_Depth_v2',
    entityId: 'ds_014',
    action: 'Dataset Updated',
    user: 'data.eng',
    metadata: 'Added: 340K rows',
    status: 'SUCCESS'
  }
];

export default function ChroniclePage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState<string>('ALL');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [userFilter, setUserFilter] = useState<string>('ALL');

  const filteredEvents = mockTimelineEvents.filter(event => {
    const matchesSearch = event.entity.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         event.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         event.action.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesType = typeFilter === 'ALL' || event.eventType === typeFilter;
    const matchesStatus = statusFilter === 'ALL' || event.status === statusFilter;
    const matchesUser = userFilter === 'ALL' || event.user === userFilter;

    return matchesSearch && matchesType && matchesStatus && matchesUser;
  });

  const statusMap: Record<string, 'success' | 'failure' | 'warning' | 'running' | 'pending'> = {
    SUCCESS: 'success',
    FAILED: 'failure',
    WARNING: 'warning',
    INFO: 'pending'
  };

  const eventTypes = ['ALL', ...Array.from(new Set(mockTimelineEvents.map(e => e.eventType)))];
  const users = ['ALL', ...Array.from(new Set(mockTimelineEvents.map(e => e.user)))];

  const statusCounts = mockTimelineEvents.reduce((acc, e) => {
    acc[e.status] = (acc[e.status] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const typeDistribution = eventTypes.slice(1).map(type => ({
    type,
    count: mockTimelineEvents.filter(e => e.eventType === type).length
  }));

  const userDistribution = users.slice(1).map(user => ({
    user,
    count: mockTimelineEvents.filter(e => e.user === user).length
  }));

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-2 flex-1">
          <MQSearch
            value={searchQuery}
            onSearch={setSearchQuery}
            placeholder="Search timeline events..."
            className="w-[300px]"
          />
          <Filter size={16} className="text-[var(--color-mq-text-secondary)]" />

          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="bg-[var(--color-mq-bg-secondary)] border border-[var(--color-mq-border)] rounded-[var(--radius-minimal)] px-2 h-8 text-[var(--font-size-small)] text-[var(--color-mq-text-primary)] font-mono"
          >
            {eventTypes.map(type => (
              <option key={type} value={type}>{type}</option>
            ))}
          </select>

          <select
            value={userFilter}
            onChange={(e) => setUserFilter(e.target.value)}
            className="bg-[var(--color-mq-bg-secondary)] border border-[var(--color-mq-border)] rounded-[var(--radius-minimal)] px-2 h-8 text-[var(--font-size-small)] text-[var(--color-mq-text-primary)] font-mono"
          >
            {users.map(user => (
              <option key={user} value={user}>{user}</option>
            ))}
          </select>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-[var(--color-mq-bg-secondary)] border border-[var(--color-mq-border)] rounded-[var(--radius-minimal)] px-2 h-8 text-[var(--font-size-small)] text-[var(--color-mq-text-primary)] font-mono"
          >
            <option value="ALL">All Status ({mockTimelineEvents.length})</option>
            <option value="SUCCESS">Success ({statusCounts.SUCCESS || 0})</option>
            <option value="FAILED">Failed ({statusCounts.FAILED || 0})</option>
            <option value="WARNING">Warning ({statusCounts.WARNING || 0})</option>
            <option value="INFO">Info ({statusCounts.INFO || 0})</option>
          </select>
        </div>
        <MQButton>
          Export Timeline
        </MQButton>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <MQChartContainer title="Event Type Distribution" className="lg:col-span-1">
          <div className="h-[120px] flex items-end gap-1">
            {typeDistribution.map((point, idx) => (
              <div key={idx} className="flex-1 flex flex-col items-center gap-1">
                <div
                  className="w-full bg-[var(--color-mq-accent)] rounded-t"
                  style={{ height: `${(point.count / Math.max(...typeDistribution.map(p => p.count))) * 100}%` }}
                />
                <span className="text-[var(--font-size-caption)] text-[var(--color-mq-text-muted)] font-mono">
                  {point.type}
                </span>
              </div>
            ))}
          </div>
        </MQChartContainer>

        <MQChartContainer title="User Activity" className="lg:col-span-1">
          <div className="h-[120px] flex items-end gap-1">
            {userDistribution.map((point, idx) => (
              <div key={idx} className="flex-1 flex flex-col items-center gap-1">
                <div
                  className="w-full bg-[var(--color-mq-accent)] rounded-t"
                  style={{ height: `${(point.count / Math.max(...userDistribution.map(p => p.count))) * 100}%` }}
                />
                <span className="text-[var(--font-size-caption)] text-[var(--color-mq-text-muted)] font-mono">
                  {point.user}
                </span>
              </div>
            ))}
          </div>
        </MQChartContainer>

        <MQChartContainer title="Timeline Events" className="lg:col-span-1">
          <div className="h-[120px] flex flex-col justify-center items-center gap-2">
            <Table size={32} className="text-[var(--color-mq-accent)]" />
            <div className="text-center">
              <div className="text-[var(--font-size-h3)] font-mono text-[var(--color-mq-text-primary)]">
                {mockTimelineEvents.length}
              </div>
              <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)]">
                Total Events
              </div>
            </div>
          </div>
        </MQChartContainer>
      </div>

      <MQPanel title={`Research Timeline (${filteredEvents.length})`}>
        <MQTable
          columns={[
            {
              key: 'timestamp',
              header: 'Timestamp',
              render: (row) => new Date(row.timestamp).toLocaleString(),
              width: 'w-[180px]'
            },
            {
              key: 'eventType',
              header: 'Type',
              render: (row) => row.eventType,
              width: 'w-[120px]'
            },
            {
              key: 'entity',
              header: 'Entity',
              render: (row) => (
                <span className="text-[var(--color-mq-text-primary)] font-mono">
                  {row.entity}
                </span>
              ),
              width: 'w-[200px]'
            },
            {
              key: 'action',
              header: 'Action',
              render: (row) => row.action,
              width: 'w-[160px]'
            },
            {
              key: 'user',
              header: 'User',
              render: (row) => row.user,
              width: 'w-[120px]'
            },
            {
              key: 'metadata',
              header: 'Metadata',
              render: (row) => (
                <span className="text-[var(--font-size-small)] text-[var(--color-mq-text-secondary)]">
                  {row.metadata}
                </span>
              ),
              width: 'w-[200px]'
            },
            {
              key: 'status',
              header: 'Status',
              render: (row) => (
                <MQStatusBadge status={statusMap[row.status]} label={row.status} />
              ),
              width: 'w-[100px]'
            }
          ]}
          data={filteredEvents}
          keyExtractor={(row) => row.id}
        />
      </MQPanel>
    </div>
  );
}
