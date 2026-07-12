'use client';

import { useState } from 'react';
import { MQPanel, MQTable, MQStatusBadge, MQSearch, MQButton, MQChartContainer } from '@/components/mqds';
import { Filter, Database } from 'lucide-react';
import { ModelInspector } from '@/components/lab/ModelInspector';
import { mockModelRegistry, type ModelRegistryEntry } from '@/lib/mock-data/models';

export default function ModelsPage() {
  const [selectedModel, setSelectedModel] = useState<ModelRegistryEntry | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [lifecycleFilter, setLifecycleFilter] = useState<string>('ALL');
  const [governanceFilter, setGovernanceFilter] = useState<string>('ALL');
  const [scoreFilter, setScoreFilter] = useState<string>('ALL');

  const filteredModels = mockModelRegistry.filter(model => {
    const matchesSearch = model.modelVersion.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         model.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         model.experimentId.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesLifecycle = lifecycleFilter === 'ALL' || model.lifecycleStatus === lifecycleFilter;
    const matchesGovernance = governanceFilter === 'ALL' || model.governanceStatus === governanceFilter;

    let matchesScore = true;
    if (scoreFilter === 'HIGH') matchesScore = model.overallScore >= 0.80;
    else if (scoreFilter === 'MEDIUM') matchesScore = model.overallScore >= 0.70 && model.overallScore < 0.80;
    else if (scoreFilter === 'LOW') matchesScore = model.overallScore < 0.70 && model.overallScore > 0;

    return matchesSearch && matchesLifecycle && matchesGovernance && matchesScore;
  });

  const lifecycleMap: Record<string, 'success' | 'warning' | 'pending'> = {
    PRODUCTION: 'success',
    CANDIDATE: 'warning',
    ARCHIVED: 'pending'
  };

  const governanceMap: Record<string, 'success' | 'failure' | 'warning' | 'pending'> = {
    APPROVED: 'success',
    REJECTED: 'failure',
    UNDER_REVIEW: 'warning',
    PENDING: 'pending'
  };

  const lifecycleCounts = mockModelRegistry.reduce((acc, m) => {
    acc[m.lifecycleStatus] = (acc[m.lifecycleStatus] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const governanceCounts = mockModelRegistry.reduce((acc, m) => {
    acc[m.governanceStatus] = (acc[m.governanceStatus] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const getScoreColor = (score: number) => {
    if (score === 0) return 'text-[var(--color-mq-text-muted)]';
    if (score >= 0.80) return 'text-[var(--color-mq-success)]';
    if (score >= 0.70) return 'text-[var(--color-mq-warning)]';
    return 'text-[var(--color-mq-failure)]';
  };

  const scoreDistribution = [
    { range: '0.8+', count: mockModelRegistry.filter(m => m.overallScore >= 0.8).length },
    { range: '0.75-0.8', count: mockModelRegistry.filter(m => m.overallScore >= 0.75 && m.overallScore < 0.8).length },
    { range: '0.7-0.75', count: mockModelRegistry.filter(m => m.overallScore >= 0.7 && m.overallScore < 0.75).length },
    { range: '0.65-0.7', count: mockModelRegistry.filter(m => m.overallScore >= 0.65 && m.overallScore < 0.7).length },
    { range: '<0.65', count: mockModelRegistry.filter(m => m.overallScore < 0.65 && m.overallScore > 0).length }
  ];

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-2 flex-1">
          <MQSearch
            value={searchQuery}
            onSearch={setSearchQuery}
            placeholder="Search model registry..."
            className="w-[300px]"
          />
          <Filter size={16} className="text-[var(--color-mq-text-secondary)]" />

          <select
            value={scoreFilter}
            onChange={(e) => setScoreFilter(e.target.value)}
            className="bg-[var(--color-mq-bg-secondary)] border border-[var(--color-mq-border)] rounded-[var(--radius-minimal)] px-2 h-8 text-[var(--font-size-small)] text-[var(--color-mq-text-primary)] font-mono"
          >
            <option value="ALL">All Scores</option>
            <option value="HIGH">High (≥80%)</option>
            <option value="MEDIUM">Medium (70-80%)</option>
            <option value="LOW">Low (&lt;70%)</option>
          </select>

          <select
            value={lifecycleFilter}
            onChange={(e) => setLifecycleFilter(e.target.value)}
            className="bg-[var(--color-mq-bg-secondary)] border border-[var(--color-mq-border)] rounded-[var(--radius-minimal)] px-2 h-8 text-[var(--font-size-small)] text-[var(--color-mq-text-primary)] font-mono"
          >
            <option value="ALL">All Lifecycle ({mockModelRegistry.length})</option>
            <option value="PRODUCTION">Production ({lifecycleCounts.PRODUCTION || 0})</option>
            <option value="CANDIDATE">Candidate ({lifecycleCounts.CANDIDATE || 0})</option>
            <option value="ARCHIVED">Archived ({lifecycleCounts.ARCHIVED || 0})</option>
          </select>

          <select
            value={governanceFilter}
            onChange={(e) => setGovernanceFilter(e.target.value)}
            className="bg-[var(--color-mq-bg-secondary)] border border-[var(--color-mq-border)] rounded-[var(--radius-minimal)] px-2 h-8 text-[var(--font-size-small)] text-[var(--color-mq-text-primary)] font-mono"
          >
            <option value="ALL">All Governance</option>
            <option value="APPROVED">Approved ({governanceCounts.APPROVED || 0})</option>
            <option value="UNDER_REVIEW">Under Review ({governanceCounts.UNDER_REVIEW || 0})</option>
            <option value="PENDING">Pending ({governanceCounts.PENDING || 0})</option>
            <option value="REJECTED">Rejected ({governanceCounts.REJECTED || 0})</option>
          </select>
        </div>
        <MQButton>
          Register New Model
        </MQButton>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <MQChartContainer title="Overall Score Distribution" className="lg:col-span-1">
          <div className="h-[120px] flex items-end gap-1">
            {scoreDistribution.map((point, idx) => (
              <div key={idx} className="flex-1 flex flex-col items-center gap-1">
                <div
                  className="w-full rounded-t"
                  style={{
                    height: `${(point.count / Math.max(...scoreDistribution.map(p => p.count))) * 100}%`,
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

        <MQChartContainer title="Production Models" className="lg:col-span-1">
          <div className="h-[120px] flex flex-col justify-center items-center gap-2">
            <Database size={32} className="text-[var(--color-mq-success)]" />
            <div className="text-center">
              <div className="text-[var(--font-size-h3)] font-mono text-[var(--color-mq-text-primary)]">
                {lifecycleCounts.PRODUCTION || 0}
              </div>
              <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)]">
                Active
              </div>
            </div>
          </div>
        </MQChartContainer>

        <MQChartContainer title="Model Registry" className="lg:col-span-1">
          <div className="h-[120px] flex flex-col justify-center items-center gap-2">
            <Database size={32} className="text-[var(--color-mq-accent)]" />
            <div className="text-center">
              <div className="text-[var(--font-size-h3)] font-mono text-[var(--color-mq-text-primary)]">
                {mockModelRegistry.length}
              </div>
              <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)]">
                Total Models
              </div>
            </div>
          </div>
        </MQChartContainer>
      </div>

      <MQPanel title={`Model Registry (${filteredModels.length})`}>
        <MQTable
          columns={[
            {
              key: 'modelVersion',
              header: 'Model Version',
              render: (row) => (
                <button
                  onClick={() => setSelectedModel(row)}
                  className="text-[var(--color-mq-accent)] hover:underline text-left font-mono"
                >
                  {row.modelVersion}
                </button>
              ),
              width: 'w-[100px]'
            },
            {
              key: 'experimentId',
              header: 'Experiment ID',
              render: (row) => row.experimentId,
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
              key: 'algorithm',
              header: 'Algorithm',
              render: (row) => row.algorithm,
              width: 'w-[100px]'
            },
            {
              key: 'trainingDate',
              header: 'Training Date',
              render: (row) => new Date(row.trainingDate).toLocaleDateString(),
              width: 'w-[110px]'
            },
            {
              key: 'validationScore',
              header: 'Val Score',
              align: 'right',
              render: (row) => (
                <span className={getScoreColor(row.validationScore)}>
                  {row.validationScore > 0 ? (row.validationScore * 100).toFixed(1) + '%' : '—'}
                </span>
              ),
              width: 'w-[90px]'
            },
            {
              key: 'calibrationScore',
              header: 'Cal Score',
              align: 'right',
              render: (row) => (
                <span className={getScoreColor(row.calibrationScore)}>
                  {row.calibrationScore > 0 ? (row.calibrationScore * 100).toFixed(1) + '%' : '—'}
                </span>
              ),
              width: 'w-[90px]'
            },
            {
              key: 'evaluationScore',
              header: 'Eval Score',
              align: 'right',
              render: (row) => (
                <span className={getScoreColor(row.evaluationScore)}>
                  {row.evaluationScore > 0 ? (row.evaluationScore * 100).toFixed(1) + '%' : '—'}
                </span>
              ),
              width: 'w-[90px]'
            },
            {
              key: 'promotionScore',
              header: 'Promo Score',
              align: 'right',
              render: (row) => (
                <span className={getScoreColor(row.promotionScore)}>
                  {row.promotionScore > 0 ? (row.promotionScore * 100).toFixed(1) + '%' : '—'}
                </span>
              ),
              width: 'w-[100px]'
            },
            {
              key: 'overallScore',
              header: 'Overall',
              align: 'right',
              render: (row) => (
                <span className={getScoreColor(row.overallScore)}>
                  {row.overallScore > 0 ? (row.overallScore * 100).toFixed(1) + '%' : '—'}
                </span>
              ),
              width: 'w-[80px]'
            },
            {
              key: 'lifecycleStatus',
              header: 'Lifecycle',
              render: (row) => (
                <MQStatusBadge status={lifecycleMap[row.lifecycleStatus]} label={row.lifecycleStatus} />
              ),
              width: 'w-[100px]'
            },
            {
              key: 'governanceStatus',
              header: 'Governance',
              render: (row) => (
                <MQStatusBadge status={governanceMap[row.governanceStatus]} label={row.governanceStatus} />
              ),
              width: 'w-[120px]'
            },
            {
              key: 'activatedAt',
              header: 'Activated At',
              render: (row) => row.activatedAt ? new Date(row.activatedAt).toLocaleDateString() : '—',
              width: 'w-[110px]'
            },
            {
              key: 'rollbackAvailable',
              header: 'Rollback',
              align: 'center',
              render: (row) => (
                <span className={row.rollbackAvailable ? 'text-[var(--color-mq-success)]' : 'text-[var(--color-mq-text-muted)]'}>
                  {row.rollbackAvailable ? '✓' : '—'}
                </span>
              ),
              width: 'w-[80px]'
            }
          ]}
          data={filteredModels}
          keyExtractor={(row) => row.id}
        />
      </MQPanel>

      {selectedModel && (
        <ModelInspector
          model={selectedModel}
          onClose={() => setSelectedModel(null)}
        />
      )}
    </div>
  );
}
