'use client';

import { useState } from 'react';
import { MQPanel, MQTable, MQStatusBadge, MQSearch, MQButton } from '@/components/mqds';
import { mockExperiments, Experiment } from '@/lib/mock-data/experiments';
import { ExperimentInspector } from '@/components/lab/ExperimentInspector';
import { Plus, Filter } from 'lucide-react';

export default function ExperimentsPage() {
  const [selectedExperiment, setSelectedExperiment] = useState<Experiment | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');

  const filteredExperiments = mockExperiments.filter(exp => {
    const matchesSearch = exp.runId.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         exp.algorithm.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         exp.dataset.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = statusFilter === 'ALL' || exp.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const statusMap: Record<string, 'success' | 'failure' | 'warning' | 'running' | 'pending'> = {
    PRODUCTION: 'success',
    PROMOTION: 'success',
    PAPER: 'warning',
    TRAINING: 'running',
    VALIDATING: 'warning',
    CALIBRATING: 'warning',
    FAILED: 'failure',
    CREATED: 'pending',
    ARCHIVED: 'pending'
  };

  const statusCounts = mockExperiments.reduce((acc, exp) => {
    acc[exp.status] = (acc[exp.status] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <MQSearch
            value={searchQuery}
            onSearch={setSearchQuery}
            placeholder="Search experiments..."
          />
          <div className="flex items-center gap-2">
            <Filter size={16} className="text-[var(--color-mq-text-secondary)]" />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="bg-[var(--color-mq-bg-secondary)] border border-[var(--color-mq-border)] rounded-[var(--radius-minimal)] px-2 h-8 text-[var(--font-size-small)] text-[var(--color-mq-text-primary)] font-mono"
            >
              <option value="ALL">All ({mockExperiments.length})</option>
              <option value="TRAINING">Training ({statusCounts.TRAINING || 0})</option>
              <option value="VALIDATING">Validating ({statusCounts.VALIDATING || 0})</option>
              <option value="CALIBRATING">Calibrating ({statusCounts.CALIBRATING || 0})</option>
              <option value="PAPER">Paper ({statusCounts.PAPER || 0})</option>
              <option value="PROMOTION">Promotion ({statusCounts.PROMOTION || 0})</option>
              <option value="PRODUCTION">Production ({statusCounts.PRODUCTION || 0})</option>
              <option value="FAILED">Failed ({statusCounts.FAILED || 0})</option>
              <option value="ARCHIVED">Archived ({statusCounts.ARCHIVED || 0})</option>
            </select>
          </div>
        </div>
        <MQButton>
          Create Experiment
        </MQButton>
      </div>

      <MQPanel title={`Experiments (${filteredExperiments.length})`}>
        <MQTable
          columns={[
            {
              key: 'runId',
              header: 'Run ID',
              render: (row) => (
                <button
                  onClick={() => setSelectedExperiment(row)}
                  className="text-[var(--color-mq-accent)] hover:underline text-left font-mono"
                >
                  {row.runId}
                </button>
              ),
              width: 'w-[180px]'
            },
            {
              key: 'status',
              header: 'Status',
              render: (row) => (
                <MQStatusBadge status={statusMap[row.status]} label={row.status} />
              ),
              width: 'w-[120px]'
            },
            {
              key: 'dataset',
              header: 'Dataset',
              render: (row) => row.dataset,
              width: 'w-[150px]'
            },
            {
              key: 'featureVersion',
              header: 'Feature Version',
              render: (row) => row.featureVersion,
              width: 'w-[140px]'
            },
            {
              key: 'algorithm',
              header: 'Algorithm',
              render: (row) => row.algorithm
            },
            {
              key: 'created',
              header: 'Created',
              render: (row) => new Date(row.created).toLocaleDateString(),
              width: 'w-[100px]'
            },
            {
              key: 'duration',
              header: 'Duration',
              align: 'right',
              render: (row) => row.duration,
              width: 'w-[100px]'
            },
            {
              key: 'score',
              header: 'Score',
              align: 'right',
              render: (row) => row.score ? (
                <span className={row.score >= 0.8 ? 'text-[var(--color-mq-success)]' : ''}>
                  {row.score.toFixed(2)}
                </span>
              ) : '-',
              width: 'w-[80px]'
            }
          ]}
          data={filteredExperiments}
          keyExtractor={(row) => row.runId}
        />
      </MQPanel>

      {selectedExperiment && (
        <ExperimentInspector
          experiment={selectedExperiment}
          onClose={() => setSelectedExperiment(null)}
        />
      )}
    </div>
  );
}
