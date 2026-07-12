'use client';

import { useState } from 'react';
import { MQPanel, MQTable, MQStatusBadge, MQSearch, MQButton, MQChartContainer } from '@/components/mqds';
import { Filter, TrendingUp } from 'lucide-react';
import { CalibrationInspector } from '@/components/lab/CalibrationInspector';

type CalibrationRun = {
  id: string;
  name: string;
  model: string;
  method: string;
  dataset: string;
  brierScore: number;
  ece: number;
  mce: number;
  logLoss: number;
  bins: number;
  status: 'CALIBRATED' | 'NEEDS_RECALIBRATION' | 'CALIBRATING' | 'FAILED' | 'PENDING';
  created: string;
};

const mockCalibrationRuns: CalibrationRun[] = [
  {
    id: 'cal_001',
    name: 'LSTM Production Calibration',
    model: 'LSTM_v2.3',
    method: 'Platt Scaling',
    dataset: 'Q4_2025_OOS',
    brierScore: 0.142,
    ece: 0.023,
    mce: 0.089,
    logLoss: 0.312,
    bins: 10,
    status: 'CALIBRATED',
    created: '2026-01-18'
  },
  {
    id: 'cal_002',
    name: 'RandomForest Recalibration',
    model: 'RandomForest_v1.8',
    method: 'Isotonic Regression',
    dataset: 'Full_2024_2025',
    brierScore: 0.168,
    ece: 0.031,
    mce: 0.112,
    logLoss: 0.387,
    bins: 15,
    status: 'CALIBRATED',
    created: '2026-01-20'
  },
  {
    id: 'cal_003',
    name: 'XGBoost Beta Calibration',
    model: 'XGBoost_v3.1',
    method: 'Beta Calibration',
    dataset: 'Q1_2026_Test',
    brierScore: 0.189,
    ece: 0.047,
    mce: 0.134,
    logLoss: 0.421,
    bins: 10,
    status: 'NEEDS_RECALIBRATION',
    created: '2026-02-05'
  },
  {
    id: 'cal_004',
    name: 'Ensemble Temperature Scaling',
    model: 'Ensemble_v1.2',
    method: 'Temperature Scaling',
    dataset: 'Monte_Carlo_2025_2026',
    brierScore: 0.128,
    ece: 0.018,
    mce: 0.071,
    logLoss: 0.279,
    bins: 20,
    status: 'CALIBRATED',
    created: '2026-03-10'
  },
  {
    id: 'cal_005',
    name: 'GRU Histogram Binning',
    model: 'GRU_v1.5',
    method: 'Histogram Binning',
    dataset: 'Full_2023_2025',
    brierScore: 0.234,
    ece: 0.062,
    mce: 0.187,
    logLoss: 0.512,
    bins: 12,
    status: 'FAILED',
    created: '2026-04-22'
  },
  {
    id: 'cal_006',
    name: 'Transformer BBQ Calibration',
    model: 'Transformer_v2.0',
    method: 'BBQ',
    dataset: 'H2_2025_Rolling',
    brierScore: 0.151,
    ece: 0.026,
    mce: 0.095,
    logLoss: 0.334,
    bins: 10,
    status: 'CALIBRATING',
    created: '2026-05-16'
  },
  {
    id: 'cal_007',
    name: 'LSTM Ensemble Calibration',
    model: 'LSTM_v2.3',
    method: 'Ensemble Temperature',
    dataset: 'Time_Series_2024_2026',
    brierScore: 0.0,
    ece: 0.0,
    mce: 0.0,
    logLoss: 0.0,
    bins: 15,
    status: 'PENDING',
    created: '2026-07-01'
  }
];

export default function CalibrationPage() {
  const [selectedRun, setSelectedRun] = useState<CalibrationRun | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [methodFilter, setMethodFilter] = useState<string>('ALL');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [qualityFilter, setQualityFilter] = useState<string>('ALL');

  const filteredRuns = mockCalibrationRuns.filter(run => {
    const matchesSearch = run.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         run.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         run.model.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesMethod = methodFilter === 'ALL' || run.method === methodFilter;
    const matchesStatus = statusFilter === 'ALL' || run.status === statusFilter;

    let matchesQuality = true;
    if (qualityFilter === 'EXCELLENT') matchesQuality = run.ece <= 0.025;
    else if (qualityFilter === 'GOOD') matchesQuality = run.ece > 0.025 && run.ece <= 0.04;
    else if (qualityFilter === 'POOR') matchesQuality = run.ece > 0.04;

    return matchesSearch && matchesMethod && matchesStatus && matchesQuality;
  });

  const statusMap: Record<string, 'success' | 'failure' | 'warning' | 'running' | 'pending'> = {
    CALIBRATED: 'success',
    NEEDS_RECALIBRATION: 'warning',
    CALIBRATING: 'running',
    FAILED: 'failure',
    PENDING: 'pending'
  };

  const methods = ['ALL', ...Array.from(new Set(mockCalibrationRuns.map(r => r.method)))];

  const statusCounts = mockCalibrationRuns.reduce((acc, r) => {
    acc[r.status] = (acc[r.status] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const getECEColor = (score: number) => {
    if (score <= 0.025) return 'text-[var(--color-mq-success)]';
    if (score <= 0.04) return 'text-[var(--color-mq-warning)]';
    return 'text-[var(--color-mq-failure)]';
  };

  const eceDistribution = [
    { range: '0-0.02', count: mockCalibrationRuns.filter(r => r.ece <= 0.02).length },
    { range: '0.02-0.03', count: mockCalibrationRuns.filter(r => r.ece > 0.02 && r.ece <= 0.03).length },
    { range: '0.03-0.04', count: mockCalibrationRuns.filter(r => r.ece > 0.03 && r.ece <= 0.04).length },
    { range: '0.04-0.05', count: mockCalibrationRuns.filter(r => r.ece > 0.04 && r.ece <= 0.05).length },
    { range: '>0.05', count: mockCalibrationRuns.filter(r => r.ece > 0.05).length }
  ];

  const methodDistribution = methods.slice(1).map(method => ({
    method,
    count: mockCalibrationRuns.filter(r => r.method === method).length
  }));

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-2 flex-1">
          <MQSearch
            value={searchQuery}
            onSearch={setSearchQuery}
            placeholder="Search calibration runs..."
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
            value={qualityFilter}
            onChange={(e) => setQualityFilter(e.target.value)}
            className="bg-[var(--color-mq-bg-secondary)] border border-[var(--color-mq-border)] rounded-[var(--radius-minimal)] px-2 h-8 text-[var(--font-size-small)] text-[var(--color-mq-text-primary)] font-mono"
          >
            <option value="ALL">All Quality</option>
            <option value="EXCELLENT">Excellent (ECE ≤2.5%)</option>
            <option value="GOOD">Good (2.5-4%)</option>
            <option value="POOR">Poor (&gt;4%)</option>
          </select>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-[var(--color-mq-bg-secondary)] border border-[var(--color-mq-border)] rounded-[var(--radius-minimal)] px-2 h-8 text-[var(--font-size-small)] text-[var(--color-mq-text-primary)] font-mono"
          >
            <option value="ALL">All Status ({mockCalibrationRuns.length})</option>
            <option value="CALIBRATED">Calibrated ({statusCounts.CALIBRATED || 0})</option>
            <option value="NEEDS_RECALIBRATION">Needs Recalibration ({statusCounts.NEEDS_RECALIBRATION || 0})</option>
            <option value="CALIBRATING">Calibrating ({statusCounts.CALIBRATING || 0})</option>
            <option value="FAILED">Failed ({statusCounts.FAILED || 0})</option>
            <option value="PENDING">Pending ({statusCounts.PENDING || 0})</option>
          </select>
        </div>
        <MQButton>
          New Calibration Run
        </MQButton>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <MQChartContainer title="ECE Distribution" className="lg:col-span-1">
          <div className="h-[120px] flex items-end gap-1">
            {eceDistribution.map((point, idx) => (
              <div key={idx} className="flex-1 flex flex-col items-center gap-1">
                <div
                  className="w-full rounded-t"
                  style={{
                    height: `${(point.count / Math.max(...eceDistribution.map(p => p.count))) * 100}%`,
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

        <MQChartContainer title="Calibration Runs" className="lg:col-span-1">
          <div className="h-[120px] flex flex-col justify-center items-center gap-2">
            <TrendingUp size={32} className="text-[var(--color-mq-accent)]" />
            <div className="text-center">
              <div className="text-[var(--font-size-h3)] font-mono text-[var(--color-mq-text-primary)]">
                {mockCalibrationRuns.length}
              </div>
              <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)]">
                Total Runs
              </div>
            </div>
          </div>
        </MQChartContainer>
      </div>

      <MQPanel title={`Calibration Runs (${filteredRuns.length})`}>
        <MQTable
          columns={[
            {
              key: 'name',
              header: 'Calibration Name',
              render: (row) => (
                <button
                  onClick={() => setSelectedRun(row)}
                  className="text-[var(--color-mq-accent)] hover:underline text-left font-mono"
                >
                  {row.name}
                </button>
              ),
              width: 'w-[220px]'
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
              width: 'w-[160px]'
            },
            {
              key: 'dataset',
              header: 'Dataset',
              render: (row) => row.dataset,
              width: 'w-[140px]'
            },
            {
              key: 'ece',
              header: 'ECE',
              align: 'right',
              render: (row) => (
                <span className={getECEColor(row.ece)}>
                  {(row.ece * 100).toFixed(2)}%
                </span>
              ),
              width: 'w-[80px]'
            },
            {
              key: 'brierScore',
              header: 'Brier',
              align: 'right',
              render: (row) => (
                <span className={row.brierScore <= 0.15 ? 'text-[var(--color-mq-success)]' : row.brierScore <= 0.20 ? 'text-[var(--color-mq-warning)]' : 'text-[var(--color-mq-failure)]'}>
                  {row.brierScore.toFixed(3)}
                </span>
              ),
              width: 'w-[80px]'
            },
            {
              key: 'mce',
              header: 'MCE',
              align: 'right',
              render: (row) => (
                <span>
                  {(row.mce * 100).toFixed(2)}%
                </span>
              ),
              width: 'w-[80px]'
            },
            {
              key: 'logLoss',
              header: 'Log Loss',
              align: 'right',
              render: (row) => row.logLoss.toFixed(3),
              width: 'w-[90px]'
            },
            {
              key: 'bins',
              header: 'Bins',
              align: 'right',
              render: (row) => row.bins,
              width: 'w-[60px]'
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
              width: 'w-[140px]'
            }
          ]}
          data={filteredRuns}
          keyExtractor={(row) => row.id}
        />
      </MQPanel>

      {selectedRun && (
        <CalibrationInspector
          calibration={selectedRun}
          onClose={() => setSelectedRun(null)}
        />
      )}
    </div>
  );
}
