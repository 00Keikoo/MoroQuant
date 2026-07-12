'use client';

import { useState } from 'react';
import { MQPanel, MQTable, MQStatusBadge, MQSearch, MQButton, MQChartContainer } from '@/components/mqds';
import { Filter, Target } from 'lucide-react';

type ValidationRun = {
  id: string;
  name: string;
  model: string;
  method: string;
  period: string;
  accuracy: number;
  sharpeRatio: number;
  maxDrawdown: number;
  winRate: number;
  totalTrades: number;
  status: 'PASSED' | 'FAILED' | 'RUNNING' | 'PENDING' | 'WARNING';
  created: string;
};

const mockValidationRuns: ValidationRun[] = [
  {
    id: 'val_001',
    name: 'Q4 2025 Walk-Forward',
    model: 'LSTM_v2.3',
    method: 'Walk-Forward',
    period: '2025-Q4',
    accuracy: 0.673,
    sharpeRatio: 1.82,
    maxDrawdown: 0.156,
    winRate: 0.581,
    totalTrades: 342,
    status: 'PASSED',
    created: '2026-01-15'
  },
  {
    id: 'val_002',
    name: 'Cross-Val 5-Fold',
    model: 'RandomForest_v1.8',
    method: 'Cross-Validation',
    period: '2024-2025',
    accuracy: 0.621,
    sharpeRatio: 1.45,
    maxDrawdown: 0.203,
    winRate: 0.553,
    totalTrades: 1205,
    status: 'PASSED',
    created: '2026-01-12'
  },
  {
    id: 'val_003',
    name: 'Out-of-Sample Test',
    model: 'XGBoost_v3.1',
    method: 'Out-of-Sample',
    period: '2026-Q1',
    accuracy: 0.589,
    sharpeRatio: 1.21,
    maxDrawdown: 0.278,
    winRate: 0.512,
    totalTrades: 187,
    status: 'WARNING',
    created: '2026-02-03'
  },
  {
    id: 'val_004',
    name: 'Monte Carlo Sim',
    model: 'Ensemble_v1.2',
    method: 'Monte Carlo',
    period: '2025-2026',
    accuracy: 0.712,
    sharpeRatio: 2.03,
    maxDrawdown: 0.132,
    winRate: 0.624,
    totalTrades: 892,
    status: 'PASSED',
    created: '2026-03-08'
  },
  {
    id: 'val_005',
    name: 'Backtesting Full',
    model: 'GRU_v1.5',
    method: 'Backtesting',
    period: '2023-2025',
    accuracy: 0.548,
    sharpeRatio: 0.87,
    maxDrawdown: 0.341,
    winRate: 0.489,
    totalTrades: 2103,
    status: 'FAILED',
    created: '2026-04-21'
  },
  {
    id: 'val_006',
    name: 'Rolling Window Val',
    model: 'Transformer_v2.0',
    method: 'Rolling Window',
    period: '2025-H2',
    accuracy: 0.691,
    sharpeRatio: 1.76,
    maxDrawdown: 0.167,
    winRate: 0.572,
    totalTrades: 521,
    status: 'RUNNING',
    created: '2026-05-15'
  },
  {
    id: 'val_007',
    name: 'Time-Series Split',
    model: 'LSTM_v2.3',
    method: 'Time-Series Split',
    period: '2024-2026',
    accuracy: 0.0,
    sharpeRatio: 0.0,
    maxDrawdown: 0.0,
    winRate: 0.0,
    totalTrades: 0,
    status: 'PENDING',
    created: '2026-06-30'
  }
];

export default function ValidationPage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [methodFilter, setMethodFilter] = useState<string>('ALL');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [accuracyFilter, setAccuracyFilter] = useState<string>('ALL');

  const filteredRuns = mockValidationRuns.filter(run => {
    const matchesSearch = run.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         run.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         run.model.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesMethod = methodFilter === 'ALL' || run.method === methodFilter;
    const matchesStatus = statusFilter === 'ALL' || run.status === statusFilter;

    let matchesAccuracy = true;
    if (accuracyFilter === 'HIGH') matchesAccuracy = run.accuracy >= 0.65;
    else if (accuracyFilter === 'MEDIUM') matchesAccuracy = run.accuracy >= 0.55 && run.accuracy < 0.65;
    else if (accuracyFilter === 'LOW') matchesAccuracy = run.accuracy < 0.55;

    return matchesSearch && matchesMethod && matchesStatus && matchesAccuracy;
  });

  const statusMap: Record<string, 'success' | 'failure' | 'warning' | 'running' | 'pending'> = {
    PASSED: 'success',
    FAILED: 'failure',
    WARNING: 'warning',
    RUNNING: 'running',
    PENDING: 'pending'
  };

  const methods = ['ALL', ...Array.from(new Set(mockValidationRuns.map(r => r.method)))];

  const statusCounts = mockValidationRuns.reduce((acc, r) => {
    acc[r.status] = (acc[r.status] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const getAccuracyColor = (score: number) => {
    if (score >= 0.65) return 'text-[var(--color-mq-success)]';
    if (score >= 0.55) return 'text-[var(--color-mq-warning)]';
    return 'text-[var(--color-mq-failure)]';
  };

  const accuracyDistribution = [
    { range: '0.7+', count: mockValidationRuns.filter(r => r.accuracy >= 0.7).length },
    { range: '0.65-0.7', count: mockValidationRuns.filter(r => r.accuracy >= 0.65 && r.accuracy < 0.7).length },
    { range: '0.6-0.65', count: mockValidationRuns.filter(r => r.accuracy >= 0.6 && r.accuracy < 0.65).length },
    { range: '0.55-0.6', count: mockValidationRuns.filter(r => r.accuracy >= 0.55 && r.accuracy < 0.6).length },
    { range: '<0.55', count: mockValidationRuns.filter(r => r.accuracy < 0.55).length }
  ];

  const methodDistribution = methods.slice(1).map(method => ({
    method,
    count: mockValidationRuns.filter(r => r.method === method).length
  }));

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-2 flex-1">
          <MQSearch
            value={searchQuery}
            onSearch={setSearchQuery}
            placeholder="Search validation runs..."
            className="w-[300px]"
          />
          <Filter size={16} className="text-[var(--color-mq-text-secondary)]" />

          <select
            value={methodFilter}
            onChange={(e) => setMethodFilter(e.target.value)}
            className="bg-[var(--color-mq-bg-secondary)] border border-[var(--color-mq-border)] rounded-[var(--radius-minimal)] px-2 h-8 text-[var(--font-size-small)] text-[var(--color-mq-text-primary)] font-mono"
          >
            {methods.map(method => (
              <option key={method} value={method}>{method}</option>
            ))}
          </select>

          <select
            value={accuracyFilter}
            onChange={(e) => setAccuracyFilter(e.target.value)}
            className="bg-[var(--color-mq-bg-secondary)] border border-[var(--color-mq-border)] rounded-[var(--radius-minimal)] px-2 h-8 text-[var(--font-size-small)] text-[var(--color-mq-text-primary)] font-mono"
          >
            <option value="ALL">All Accuracy</option>
            <option value="HIGH">High (≥65%)</option>
            <option value="MEDIUM">Medium (55-65%)</option>
            <option value="LOW">Low (&lt;55%)</option>
          </select>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-[var(--color-mq-bg-secondary)] border border-[var(--color-mq-border)] rounded-[var(--radius-minimal)] px-2 h-8 text-[var(--font-size-small)] text-[var(--color-mq-text-primary)] font-mono"
          >
            <option value="ALL">All Status ({mockValidationRuns.length})</option>
            <option value="PASSED">Passed ({statusCounts.PASSED || 0})</option>
            <option value="FAILED">Failed ({statusCounts.FAILED || 0})</option>
            <option value="WARNING">Warning ({statusCounts.WARNING || 0})</option>
            <option value="RUNNING">Running ({statusCounts.RUNNING || 0})</option>
            <option value="PENDING">Pending ({statusCounts.PENDING || 0})</option>
          </select>
        </div>
        <MQButton>
          New Validation Run
        </MQButton>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <MQChartContainer title="Accuracy Distribution" className="lg:col-span-1">
          <div className="h-[120px] flex items-end gap-1">
            {accuracyDistribution.map((point, idx) => (
              <div key={idx} className="flex-1 flex flex-col items-center gap-1">
                <div
                  className="w-full rounded-t"
                  style={{
                    height: `${(point.count / Math.max(...accuracyDistribution.map(p => p.count))) * 100}%`,
                    backgroundColor: idx === 0 ? 'var(--color-mq-success)' : idx === 1 ? 'var(--color-mq-success)' : idx === 2 ? 'var(--color-mq-warning)' : 'var(--color-mq-failure)'
                  }}
                />
                <span className="text-[var(--font-size-caption)] text-[var(--color-mq-text-muted)] font-mono">
                  {point.range}
                </span>
              </div>
            ))}
          </div>
        </MQChartContainer>

        <MQChartContainer title="Method Distribution" className="lg:col-span-1">
          <div className="h-[120px] flex items-end gap-1">
            {methodDistribution.map((point, idx) => (
              <div key={idx} className="flex-1 flex flex-col items-center gap-1">
                <div
                  className="w-full bg-[var(--color-mq-accent)] rounded-t"
                  style={{ height: `${(point.count / Math.max(...methodDistribution.map(p => p.count))) * 100}%` }}
                />
                <span className="text-[var(--font-size-caption)] text-[var(--color-mq-text-muted)] font-mono">
                  {point.method}
                </span>
              </div>
            ))}
          </div>
        </MQChartContainer>

        <MQChartContainer title="Validation Runs" className="lg:col-span-1">
          <div className="h-[120px] flex flex-col justify-center items-center gap-2">
            <Target size={32} className="text-[var(--color-mq-accent)]" />
            <div className="text-center">
              <div className="text-[var(--font-size-h3)] font-mono text-[var(--color-mq-text-primary)]">
                {mockValidationRuns.length}
              </div>
              <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)]">
                Total Runs
              </div>
            </div>
          </div>
        </MQChartContainer>
      </div>

      <MQPanel title={`Validation Runs (${filteredRuns.length})`}>
        <MQTable
          columns={[
            {
              key: 'name',
              header: 'Validation Name',
              render: (row) => (
                <span className="text-[var(--color-mq-text-primary)] font-mono">
                  {row.name}
                </span>
              ),
              width: 'w-[180px]'
            },
            {
              key: 'model',
              header: 'Model',
              render: (row) => row.model,
              width: 'w-[140px]'
            },
            {
              key: 'method',
              header: 'Method',
              render: (row) => row.method,
              width: 'w-[140px]'
            },
            {
              key: 'period',
              header: 'Period',
              render: (row) => row.period,
              width: 'w-[100px]'
            },
            {
              key: 'accuracy',
              header: 'Accuracy',
              align: 'right',
              render: (row) => (
                <span className={getAccuracyColor(row.accuracy)}>
                  {(row.accuracy * 100).toFixed(1)}%
                </span>
              ),
              width: 'w-[90px]'
            },
            {
              key: 'sharpeRatio',
              header: 'Sharpe',
              align: 'right',
              render: (row) => (
                <span className={row.sharpeRatio >= 1.5 ? 'text-[var(--color-mq-success)]' : row.sharpeRatio >= 1.0 ? 'text-[var(--color-mq-warning)]' : 'text-[var(--color-mq-failure)]'}>
                  {row.sharpeRatio.toFixed(2)}
                </span>
              ),
              width: 'w-[80px]'
            },
            {
              key: 'maxDrawdown',
              header: 'Max DD',
              align: 'right',
              render: (row) => (
                <span className={row.maxDrawdown < 0.15 ? 'text-[var(--color-mq-success)]' : row.maxDrawdown < 0.25 ? 'text-[var(--color-mq-warning)]' : 'text-[var(--color-mq-failure)]'}>
                  {(row.maxDrawdown * 100).toFixed(1)}%
                </span>
              ),
              width: 'w-[80px]'
            },
            {
              key: 'winRate',
              header: 'Win Rate',
              align: 'right',
              render: (row) => (
                <span>
                  {(row.winRate * 100).toFixed(1)}%
                </span>
              ),
              width: 'w-[90px]'
            },
            {
              key: 'totalTrades',
              header: 'Trades',
              align: 'right',
              render: (row) => row.totalTrades,
              width: 'w-[80px]'
            },
            {
              key: 'created',
              header: 'Created',
              render: (row) => new Date(row.created).toLocaleDateString(),
              width: 'w-[100px]'
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
          data={filteredRuns}
          keyExtractor={(row) => row.id}
        />
      </MQPanel>
    </div>
  );
}
