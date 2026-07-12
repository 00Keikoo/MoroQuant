'use client';

import { useState } from 'react';
import { MQPanel, MQTable, MQStatusBadge, MQSearch, MQButton, MQChartContainer } from '@/components/mqds';
import { Filter, Target } from 'lucide-react';
import { mockValidationRuns, type ValidationRun } from '@/lib/mock-data/validation';

export default function ValidationPage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [f1Filter, setF1Filter] = useState<string>('ALL');

  const filteredRuns = mockValidationRuns.filter(run => {
    const matchesSearch = run.experiment.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         run.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         run.datasetVersion.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = statusFilter === 'ALL' || run.status === statusFilter;

    let matchesF1 = true;
    if (f1Filter === 'HIGH') matchesF1 = run.weightedF1 >= 0.70;
    else if (f1Filter === 'MEDIUM') matchesF1 = run.weightedF1 >= 0.60 && run.weightedF1 < 0.70;
    else if (f1Filter === 'LOW') matchesF1 = run.weightedF1 < 0.60;

    return matchesSearch && matchesStatus && matchesF1;
  });

  const statusMap: Record<string, 'success' | 'failure' | 'warning' | 'running' | 'pending'> = {
    PASSED: 'success',
    FAILED: 'failure',
    WARNING: 'warning',
    RUNNING: 'running',
    PENDING: 'pending'
  };

  const statusCounts = mockValidationRuns.reduce((acc, r) => {
    acc[r.status] = (acc[r.status] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const getF1Color = (score: number) => {
    if (score >= 0.70) return 'text-[var(--color-mq-success)]';
    if (score >= 0.60) return 'text-[var(--color-mq-warning)]';
    return 'text-[var(--color-mq-failure)]';
  };

  const getECEColor = (score: number) => {
    if (score <= 0.05) return 'text-[var(--color-mq-success)]';
    if (score <= 0.10) return 'text-[var(--color-mq-warning)]';
    return 'text-[var(--color-mq-failure)]';
  };

  const f1Distribution = [
    { range: '0.7+', count: mockValidationRuns.filter(r => r.weightedF1 >= 0.7).length },
    { range: '0.65-0.7', count: mockValidationRuns.filter(r => r.weightedF1 >= 0.65 && r.weightedF1 < 0.7).length },
    { range: '0.6-0.65', count: mockValidationRuns.filter(r => r.weightedF1 >= 0.6 && r.weightedF1 < 0.65).length },
    { range: '0.55-0.6', count: mockValidationRuns.filter(r => r.weightedF1 >= 0.55 && r.weightedF1 < 0.6).length },
    { range: '<0.55', count: mockValidationRuns.filter(r => r.weightedF1 < 0.55).length }
  ];

  const eceImprovementData = mockValidationRuns
    .filter(r => r.eceBefore > 0)
    .map(r => ({
      id: r.id,
      improvement: ((r.eceBefore - r.eceAfter) / r.eceBefore) * 100
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
            value={f1Filter}
            onChange={(e) => setF1Filter(e.target.value)}
            className="bg-[var(--color-mq-bg-secondary)] border border-[var(--color-mq-border)] rounded-[var(--radius-minimal)] px-2 h-8 text-[var(--font-size-small)] text-[var(--color-mq-text-primary)] font-mono"
          >
            <option value="ALL">All F1 Scores</option>
            <option value="HIGH">High (≥70%)</option>
            <option value="MEDIUM">Medium (60-70%)</option>
            <option value="LOW">Low (&lt;60%)</option>
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
        <MQChartContainer title="Weighted F1 Distribution" className="lg:col-span-1">
          <div className="h-[120px] flex items-end gap-1">
            {f1Distribution.map((point, idx) => (
              <div key={idx} className="flex-1 flex flex-col items-center gap-1">
                <div
                  className="w-full rounded-t"
                  style={{
                    height: `${(point.count / Math.max(...f1Distribution.map(p => p.count))) * 100}%`,
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
              key: 'purgedWalkForward',
              header: 'PWF',
              align: 'center',
              render: (row) => (
                <span className={row.purgedWalkForward ? 'text-[var(--color-mq-success)]' : 'text-[var(--color-mq-text-muted)]'}>
                  {row.purgedWalkForward ? '✓' : '—'}
                </span>
              ),
              width: 'w-[60px]'
            },
            {
              key: 'purge',
              header: 'Purge',
              align: 'right',
              render: (row) => row.purge,
              width: 'w-[60px]'
            },
            {
              key: 'embargo',
              header: 'Emb',
              align: 'right',
              render: (row) => row.embargo,
              width: 'w-[50px]'
            },
            {
              key: 'weightedF1',
              header: 'W-F1',
              align: 'right',
              render: (row) => (
                <span className={getF1Color(row.weightedF1)}>
                  {row.weightedF1 > 0 ? (row.weightedF1 * 100).toFixed(1) + '%' : '—'}
                </span>
              ),
              width: 'w-[70px]'
            },
            {
              key: 'longF1',
              header: 'Long',
              align: 'right',
              render: (row) => (
                <span className={getF1Color(row.longF1)}>
                  {row.longF1 > 0 ? (row.longF1 * 100).toFixed(1) + '%' : '—'}
                </span>
              ),
              width: 'w-[70px]'
            },
            {
              key: 'neutralF1',
              header: 'Neutral',
              align: 'right',
              render: (row) => (
                <span className={getF1Color(row.neutralF1)}>
                  {row.neutralF1 > 0 ? (row.neutralF1 * 100).toFixed(1) + '%' : '—'}
                </span>
              ),
              width: 'w-[75px]'
            },
            {
              key: 'shortF1',
              header: 'Short',
              align: 'right',
              render: (row) => (
                <span className={getF1Color(row.shortF1)}>
                  {row.shortF1 > 0 ? (row.shortF1 * 100).toFixed(1) + '%' : '—'}
                </span>
              ),
              width: 'w-[70px]'
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
