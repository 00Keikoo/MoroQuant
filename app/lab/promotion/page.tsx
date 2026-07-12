'use client';

import { useState } from 'react';
import { MQPanel, MQTable, MQStatusBadge, MQSearch, MQButton, MQChartContainer } from '@/components/mqds';
import { Filter, ChevronDown } from 'lucide-react';
import { PromotionInspector } from '@/components/lab/PromotionInspector';
import { mockPromotionQueue, type PromotionCandidate } from '@/lib/mock-data/promotion';

export default function PromotionPage() {
  const [selectedCandidate, setSelectedCandidate] = useState<PromotionCandidate | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [stageFilter, setStageFilter] = useState<string>('ALL');
  const [decisionFilter, setDecisionFilter] = useState<string>('ALL');

  const filteredCandidates = mockPromotionQueue.filter(candidate => {
    const matchesSearch = candidate.modelVersion.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         candidate.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         candidate.experimentId.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStage = stageFilter === 'ALL' || candidate.currentStage === stageFilter;
    const matchesDecision = decisionFilter === 'ALL' || candidate.decision === decisionFilter;

    return matchesSearch && matchesStage && matchesDecision;
  });

  const stageCounts = mockPromotionQueue.reduce((acc, c) => {
    acc[c.currentStage] = (acc[c.currentStage] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const decisionCounts = mockPromotionQueue.reduce((acc, c) => {
    acc[c.decision] = (acc[c.decision] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const decisionMap: Record<string, 'success' | 'failure' | 'warning' | 'pending'> = {
    APPROVED: 'success',
    REJECTED: 'failure',
    ON_HOLD: 'warning',
    PENDING: 'pending'
  };

  const getScoreColor = (score: number) => {
    if (score === 0) return 'text-[var(--color-mq-text-muted)]';
    if (score >= 0.80) return 'text-[var(--color-mq-success)]';
    if (score >= 0.70) return 'text-[var(--color-mq-warning)]';
    return 'text-[var(--color-mq-failure)]';
  };

  const getRiskColor = (score: number) => {
    if (score >= 0.50) return 'text-[var(--color-mq-failure)]';
    if (score >= 0.30) return 'text-[var(--color-mq-warning)]';
    return 'text-[var(--color-mq-success)]';
  };

  const stages = [
    { name: 'VALIDATION', count: stageCounts.VALIDATION || 0 },
    { name: 'CALIBRATION', count: stageCounts.CALIBRATION || 0 },
    { name: 'EVALUATION', count: stageCounts.EVALUATION || 0 },
    { name: 'RISK_REVIEW', count: stageCounts.RISK_REVIEW || 0 },
    { name: 'READY', count: stageCounts.READY || 0 },
    { name: 'PRODUCTION', count: stageCounts.PRODUCTION || 0 }
  ];

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-2 flex-1">
          <MQSearch
            value={searchQuery}
            onSearch={setSearchQuery}
            placeholder="Search promotion queue..."
            className="w-[300px]"
          />
          <Filter size={16} className="text-[var(--color-mq-text-secondary)]" />

          <select
            value={stageFilter}
            onChange={(e) => setStageFilter(e.target.value)}
            className="bg-[var(--color-mq-bg-secondary)] border border-[var(--color-mq-border)] rounded-[var(--radius-minimal)] px-2 h-8 text-[var(--font-size-small)] text-[var(--color-mq-text-primary)] font-mono"
          >
            <option value="ALL">All Stages ({mockPromotionQueue.length})</option>
            <option value="VALIDATION">Validation ({stageCounts.VALIDATION || 0})</option>
            <option value="CALIBRATION">Calibration ({stageCounts.CALIBRATION || 0})</option>
            <option value="EVALUATION">Evaluation ({stageCounts.EVALUATION || 0})</option>
            <option value="RISK_REVIEW">Risk Review ({stageCounts.RISK_REVIEW || 0})</option>
            <option value="READY">Ready ({stageCounts.READY || 0})</option>
            <option value="PRODUCTION">Production ({stageCounts.PRODUCTION || 0})</option>
          </select>

          <select
            value={decisionFilter}
            onChange={(e) => setDecisionFilter(e.target.value)}
            className="bg-[var(--color-mq-bg-secondary)] border border-[var(--color-mq-border)] rounded-[var(--radius-minimal)] px-2 h-8 text-[var(--font-size-small)] text-[var(--color-mq-text-primary)] font-mono"
          >
            <option value="ALL">All Decisions</option>
            <option value="APPROVED">Approved ({decisionCounts.APPROVED || 0})</option>
            <option value="PENDING">Pending ({decisionCounts.PENDING || 0})</option>
            <option value="ON_HOLD">On Hold ({decisionCounts.ON_HOLD || 0})</option>
            <option value="REJECTED">Rejected ({decisionCounts.REJECTED || 0})</option>
          </select>
        </div>
        <MQButton>
          Submit Candidate
        </MQButton>
      </div>

      <div className="grid grid-cols-6 gap-2">
        {stages.map((stage, idx) => (
          <div key={stage.name}>
            <MQChartContainer title={stage.name.replace('_', ' ')}>
              <div className="h-[80px] flex flex-col justify-center items-center gap-1">
                <div className="text-[var(--font-size-h3)] font-mono text-[var(--color-mq-text-primary)]">
                  {stage.count}
                </div>
                {idx < stages.length - 1 && (
                  <ChevronDown size={16} className="text-[var(--color-mq-text-muted)]" />
                )}
              </div>
            </MQChartContainer>
          </div>
        ))}
      </div>

      <MQPanel title={`Promotion Queue (${filteredCandidates.length})`}>
        <MQTable
          columns={[
            {
              key: 'modelVersion',
              header: 'Model Version',
              render: (row) => (
                <button
                  onClick={() => setSelectedCandidate(row)}
                  className="text-[var(--color-mq-accent)] hover:underline text-left font-mono"
                >
                  {row.modelVersion}
                </button>
              ),
              width: 'w-[100px]'
            },
            {
              key: 'experimentId',
              header: 'Experiment',
              render: (row) => row.experimentId,
              width: 'w-[160px]'
            },
            {
              key: 'datasetVersion',
              header: 'Dataset Version',
              render: (row) => row.datasetVersion,
              width: 'w-[120px]'
            },
            {
              key: 'featureVersion',
              header: 'Feature Version',
              render: (row) => row.featureVersion,
              width: 'w-[120px]'
            },
            {
              key: 'validationScore',
              header: 'Validation Score',
              align: 'right',
              render: (row) => (
                <span className={getScoreColor(row.validationScore)}>
                  {row.validationScore > 0 ? (row.validationScore * 100).toFixed(1) + '%' : '—'}
                </span>
              ),
              width: 'w-[120px]'
            },
            {
              key: 'calibrationScore',
              header: 'Calibration Score',
              align: 'right',
              render: (row) => (
                <span className={getScoreColor(row.calibrationScore)}>
                  {row.calibrationScore > 0 ? (row.calibrationScore * 100).toFixed(1) + '%' : '—'}
                </span>
              ),
              width: 'w-[120px]'
            },
            {
              key: 'evaluationScore',
              header: 'Evaluation Score',
              align: 'right',
              render: (row) => (
                <span className={getScoreColor(row.evaluationScore)}>
                  {row.evaluationScore > 0 ? (row.evaluationScore * 100).toFixed(1) + '%' : '—'}
                </span>
              ),
              width: 'w-[120px]'
            },
            {
              key: 'promotionScore',
              header: 'Promotion Score',
              align: 'right',
              render: (row) => (
                <span className={getScoreColor(row.promotionScore)}>
                  {row.promotionScore > 0 ? (row.promotionScore * 100).toFixed(1) + '%' : '—'}
                </span>
              ),
              width: 'w-[120px]'
            },
            {
              key: 'riskScore',
              header: 'Risk Score',
              align: 'right',
              render: (row) => (
                <span className={getRiskColor(row.riskScore)}>
                  {(row.riskScore * 100).toFixed(1)}%
                </span>
              ),
              width: 'w-[100px]'
            },
            {
              key: 'currentStage',
              header: 'Current Stage',
              render: (row) => row.currentStage.replace('_', ' '),
              width: 'w-[120px]'
            },
            {
              key: 'reviewer',
              header: 'Reviewer',
              render: (row) => row.reviewer,
              width: 'w-[110px]'
            },
            {
              key: 'decision',
              header: 'Decision',
              render: (row) => (
                <MQStatusBadge status={decisionMap[row.decision]} label={row.decision} />
              ),
              width: 'w-[100px]'
            },
            {
              key: 'promotionEta',
              header: 'Promotion ETA',
              render: (row) => row.promotionEta,
              width: 'w-[120px]'
            }
          ]}
          data={filteredCandidates}
          keyExtractor={(row) => row.id}
        />
      </MQPanel>

      {selectedCandidate && (
        <PromotionInspector
          candidate={selectedCandidate}
          onClose={() => setSelectedCandidate(null)}
        />
      )}
    </div>
  );
}
