'use client';

import { useState } from 'react';
import { MQPanel, MQTable, MQStatusBadge, MQSearch, MQButton, MQChartContainer } from '@/components/mqds';
import { Filter, TrendingUp } from 'lucide-react';
import { mockCalibrationRuns, type CalibrationRun } from '@/lib/mock-data/calibration';

export default function CalibrationPage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [methodFilter, setMethodFilter] = useState<string>('ALL');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [qualityFilter, setQualityFilter] = useState<string>('ALL');

  const filteredRuns = mockCalibrationRuns.filter(run => {
    const matchesSearch = run.experiment.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         run.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         run.modelVersion.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesMethod = methodFilter === 'ALL' || run.calibrationMethod === methodFilter;
    const matchesStatus = statusFilter === 'ALL' || run.status === statusFilter;

    let matchesQuality = true;
    if (qualityFilter === 'EXCELLENT') matchesQuality = run.eceAfter <= 0.05;
    else if (qualityFilter === 'GOOD') matchesQuality = run.eceAfter > 0.05 && run.eceAfter <= 0.10;
    else if (qualityFilter === 'POOR') matchesQuality = run.eceAfter > 0.10;

    return matchesSearch && matchesMethod && matchesStatus && matchesQuality;
  });

  const statusMap: Record<string, 'success' | 'failure' | 'warning' | 'running' | 'pending'> = {
    PASSED: 'success',
    FAILED: 'failure',
    WARNING: 'warning',
    RUNNING: 'running',
    PENDING: 'pending'
  };

  const methods = ['ALL', ...Array.from(new Set(mockCalibrationRuns.map(r => r.calibrationMethod)))];

  const statusCounts = mockCalibrationRuns.reduce((acc, r) => {
    acc[r.status] = (acc[r.status] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const getECEColor = (score: number) => {
    if (score <= 0.05) return 'text-[var(--color-mq-success)]';
    if (score <= 0.10) return 'text-[var(--color-mq-warning)]';
    return 'text-[var(--color-mq-failure)]';
  };

  const eceImprovementData = mockCalibrationRuns
    .filter(r => r.eceBefore > 0)
    .map(r => ({
      id: r.id,
      improvement: ((r.eceBefore - r.eceAfter) / r.eceBefore) * 100
    }));

  const eceAfterDistribution = [
    { range: '0-0.05', count: mockCalibrationRuns.filter(r => r.eceAfter <= 0.05).length },
    { range: '0.05-0.08', count: mockCalibrationRuns.filter(r => r.eceAfter > 0.05 && r.eceAfter <= 0.08).length },
    { range: '0.08-0.12', count: mockCalibrationRuns.filter(r => r.eceAfter > 0.08 && r.eceAfter <= 0.12).length },
    { range: '0.12-0.15', count: mockCalibrationRuns.filter(r => r.eceAfter > 0.12 && r.eceAfter <= 0.15).length },
    { range: '>0.15', count: mockCalibrationRuns.filter(r => r.eceAfter > 0.15).length }
  ];

  const methodDistribution = methods.slice(1).map(method => ({
    method,
    count: mockCalibrationRuns.filter(r => r.calibrationMethod === method).length
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
            <option value="EXCELLENT">Excellent (ECE ≤5%)</option>
            <option value="GOOD">Good (5-10%)</option>
            <option value="POOR">Poor (&gt;10%)</option>
          </select>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-[var(--color-mq-bg-secondary)] border border-[var(--color-mq-border)] rounded-[var(--radius-minimal)] px-2 h-8 text-[var(--font-size-small)] text-[var(--color-mq-text-primary)] font-mono"
          >
            <option value="ALL">All Status ({mockCalibrationRuns.length})</option>
            <option value="PASSED">Passed ({statusCounts.PASSED || 0})</option>
            <option value="FAILED">Failed ({statusCounts.FAILED || 0})</option>
            <option value="WARNING">Warning ({statusCounts.WARNING || 0})</option>
            <option value="RUNNING">Running ({statusCounts.RUNNING || 0})</option>
            <option value="PENDING">Pending ({statusCounts.PENDING || 0})</option>
          </select>
        </div>
        <MQButton>
          New Calibration Run
        </MQButton>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <MQChartContainer title="ECE After Distribution" className="lg:col-span-1">
          <div className="h-[120px] flex items-end gap-1">
            {eceAfterDistribution.map((point, idx) => (
              <div key={idx} className="flex-1 flex flex-col items-center gap-1">
                <div
                  className="w-full rounded-t"
                  style={{
                    height: `${(point.count / Math.max(...eceAfterDistribution.map(p => p.count))) * 100}%`,
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

        <MQChartContainer title="ECE Improvement" className="lg:col-span-1">
          <div className="h-[120px] flex flex-col justify-center items-center gap-2">
            <div className="text-center">
              <div className="text-[var(--font-size-h3)] font-mono text-[var(--color-mq-success)]">
                {eceImprovementData.length > 0 ?
                  `${(eceImprovementData.reduce((sum, d) => sum + d.improvement, 0) / eceImprovementData.length).toFixed(1)}%`
                  : 'N/A'}
              </div>
              <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)]">
                Avg ECE Reduction
              </div>
            </div>
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
              key: 'id',
              header: 'Run ID',
              render: (row) => (
                <span className="text-[var(--color-mq-text-primary)] font-mono">
                  {row.id}
                </span>
              ),
              width: 'w-[140px]'
            },
            {
              key: 'modelVersion',
              header: 'Model Version',
              render: (row) => row.modelVersion,
              width: 'w-[130px]'
            },
            {
              key: 'experiment',
              header: 'Experiment',
              render: (row) => row.experiment,
              width: 'w-[160px]'
            },
            {
              key: 'datasetVersion',
              header: 'Dataset',
              render: (row) => row.datasetVersion,
              width: 'w-[100px]'
            },
            {
              key: 'featureVersion',
              header: 'Features',
              render: (row) => row.featureVersion,
              width: 'w-[110px]'
            },
            {
              key: 'calibrationMethod',
              header: 'Method',
              render: (row) => row.calibrationMethod,
              width: 'w-[150px]'
            },
            {
              key: 'eceBefore',
              header: 'ECE Pre',
              align: 'right',
              render: (row) => (
                <span className={getECEColor(row.eceBefore)}>
                  {row.eceBefore > 0 ? row.eceBefore.toFixed(3) : '—'}
                </span>
              ),
              width: 'w-[80px]'
            },
            {
              key: 'eceAfter',
              header: 'ECE Post',
              align: 'right',
              render: (row) => (
                <span className={getECEColor(row.eceAfter)}>
                  {row.eceAfter > 0 ? row.eceAfter.toFixed(3) : '—'}
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
                  {row.brierScore > 0 ? row.brierScore.toFixed(3) : '—'}
                </span>
              ),
              width: 'w-[80px]'
            },
            {
              key: 'calibrationDate',
              header: 'Date',
              render: (row) => new Date(row.calibrationDate).toLocaleDateString(),
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
