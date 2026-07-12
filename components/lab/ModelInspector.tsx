'use client';

import { MQInspector } from '@/components/mqds';
import { type ModelRegistryEntry } from '@/lib/mock-data/models';
import { ArrowDown } from 'lucide-react';

type ModelInspectorProps = {
  model: ModelRegistryEntry;
  onClose: () => void;
};

export function ModelInspector({ model, onClose }: ModelInspectorProps) {
  const getScoreColor = (score: number) => {
    if (score === 0) return 'text-[var(--color-mq-text-muted)]';
    if (score >= 0.80) return 'text-[var(--color-mq-success)]';
    if (score >= 0.70) return 'text-[var(--color-mq-warning)]';
    return 'text-[var(--color-mq-failure)]';
  };

  const getECEColor = (score: number) => {
    if (score === 0) return 'text-[var(--color-mq-text-muted)]';
    if (score <= 0.05) return 'text-[var(--color-mq-success)]';
    if (score <= 0.10) return 'text-[var(--color-mq-warning)]';
    return 'text-[var(--color-mq-failure)]';
  };

  const sections = [
    {
      title: 'General',
      content: (
        <div className="grid grid-cols-2 gap-4">
          <div>
            <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-muted)] mb-1">
              Model Version
            </div>
            <div className="text-[var(--font-size-body)] font-mono text-[var(--color-mq-text-primary)]">
              {model.modelVersion}
            </div>
          </div>
          <div>
            <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-muted)] mb-1">
              Experiment
            </div>
            <div className="text-[var(--font-size-body)] font-mono text-[var(--color-mq-text-primary)]">
              {model.experimentId}
            </div>
          </div>
          <div>
            <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-muted)] mb-1">
              Dataset
            </div>
            <div className="text-[var(--font-size-body)] font-mono text-[var(--color-mq-text-primary)]">
              {model.datasetVersion}
            </div>
          </div>
          <div>
            <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-muted)] mb-1">
              Feature Version
            </div>
            <div className="text-[var(--font-size-body)] font-mono text-[var(--color-mq-text-primary)]">
              {model.featureVersion}
            </div>
          </div>
          <div>
            <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-muted)] mb-1">
              Training Configuration
            </div>
            <div className="text-[var(--font-size-body)] font-mono text-[var(--color-mq-text-primary)]">
              {model.algorithm}
            </div>
          </div>
        </div>
      )
    },
    {
      title: 'Validation',
      content: (
        <div className="grid grid-cols-2 gap-4">
          <div>
            <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-muted)] mb-1">
              Purged Walk Forward
            </div>
            <div className="text-[var(--font-size-body)] font-mono">
              <span className={model.purgedWalkForward ? 'text-[var(--color-mq-success)]' : 'text-[var(--color-mq-failure)]'}>
                {model.purgedWalkForward ? 'Enabled' : 'Disabled'}
              </span>
            </div>
          </div>
          <div>
            <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-muted)] mb-1">
              Fold Metrics
            </div>
            <div className="text-[var(--font-size-body)] font-mono text-[var(--color-mq-text-primary)]">
              {model.folds} Folds
            </div>
          </div>
          <div>
            <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-muted)] mb-1">
              Validation Score
            </div>
            <div className={`text-[var(--font-size-body)] font-mono ${getScoreColor(model.validationScore)}`}>
              {model.validationScore > 0 ? (model.validationScore * 100).toFixed(1) + '%' : '—'}
            </div>
          </div>
        </div>
      )
    },
    {
      title: 'Calibration',
      content: (
        <div className="grid grid-cols-3 gap-4">
          <div>
            <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-muted)] mb-1">
              ECE Before
            </div>
            <div className={`text-[var(--font-size-body)] font-mono ${getECEColor(model.eceBefore)}`}>
              {model.eceBefore > 0 ? model.eceBefore.toFixed(3) : '—'}
            </div>
          </div>
          <div>
            <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-muted)] mb-1">
              ECE After
            </div>
            <div className={`text-[var(--font-size-body)] font-mono ${getECEColor(model.eceAfter)}`}>
              {model.eceAfter > 0 ? model.eceAfter.toFixed(3) : '—'}
            </div>
          </div>
          <div>
            <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-muted)] mb-1">
              Brier
            </div>
            <div className={`text-[var(--font-size-body)] font-mono ${getECEColor(model.brierScore)}`}>
              {model.brierScore > 0 ? model.brierScore.toFixed(3) : '—'}
            </div>
          </div>
          <div>
            <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-muted)] mb-1">
              Calibration Score
            </div>
            <div className={`text-[var(--font-size-body)] font-mono ${getScoreColor(model.calibrationScore)}`}>
              {model.calibrationScore > 0 ? (model.calibrationScore * 100).toFixed(1) + '%' : '—'}
            </div>
          </div>
        </div>
      )
    },
    {
      title: 'Evaluation',
      content: (
        <div className="grid grid-cols-2 gap-4">
          <div>
            <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-muted)] mb-1">
              Stability Score
            </div>
            <div className={`text-[var(--font-size-body)] font-mono ${getScoreColor(model.stabilityScore)}`}>
              {model.stabilityScore > 0 ? (model.stabilityScore * 100).toFixed(1) + '%' : '—'}
            </div>
          </div>
          <div>
            <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-muted)] mb-1">
              Consistency Score
            </div>
            <div className={`text-[var(--font-size-body)] font-mono ${getScoreColor(model.consistencyScore)}`}>
              {model.consistencyScore > 0 ? (model.consistencyScore * 100).toFixed(1) + '%' : '—'}
            </div>
          </div>
          <div>
            <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-muted)] mb-1">
              Risk Score
            </div>
            <div className={`text-[var(--font-size-body)] font-mono ${getScoreColor(1 - model.riskScore)}`}>
              {model.riskScore > 0 ? (model.riskScore * 100).toFixed(1) + '%' : '—'}
            </div>
          </div>
          <div>
            <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-muted)] mb-1">
              Evaluation Score
            </div>
            <div className={`text-[var(--font-size-body)] font-mono ${getScoreColor(model.evaluationScore)}`}>
              {model.evaluationScore > 0 ? (model.evaluationScore * 100).toFixed(1) + '%' : '—'}
            </div>
          </div>
        </div>
      )
    },
    {
      title: 'Promotion',
      content: (
        <div className="grid grid-cols-2 gap-4">
          <div>
            <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-muted)] mb-1">
              Promotion Decision
            </div>
            <div className="text-[var(--font-size-body)] font-mono">
              <span className={
                model.promotionDecision === 'APPROVED' ? 'text-[var(--color-mq-success)]' :
                model.promotionDecision === 'REJECTED' ? 'text-[var(--color-mq-failure)]' :
                'text-[var(--color-mq-warning)]'
              }>
                {model.promotionDecision || '—'}
              </span>
            </div>
          </div>
          <div>
            <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-muted)] mb-1">
              Promotion Score
            </div>
            <div className={`text-[var(--font-size-body)] font-mono ${getScoreColor(model.promotionScore)}`}>
              {model.promotionScore > 0 ? (model.promotionScore * 100).toFixed(1) + '%' : '—'}
            </div>
          </div>
          <div>
            <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-muted)] mb-1">
              Activated
            </div>
            <div className="text-[var(--font-size-body)] font-mono text-[var(--color-mq-text-primary)]">
              {model.activatedAt ? new Date(model.activatedAt).toLocaleString() : '—'}
            </div>
          </div>
          <div>
            <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-muted)] mb-1">
              Rollback
            </div>
            <div className="text-[var(--font-size-body)] font-mono text-[var(--color-mq-text-primary)]">
              {model.rollbackTargetVersion || '—'}
            </div>
          </div>
        </div>
      )
    },
    {
      title: 'Lineage',
      content: (
        <div className="flex flex-col gap-2">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-[var(--color-mq-accent)]" />
            <span className="text-[var(--font-size-small)] font-mono text-[var(--color-mq-text-primary)]">
              Dataset: {model.datasetVersion}
            </span>
          </div>
          <div className="ml-3 border-l-2 border-[var(--color-mq-border)] pl-4 py-1">
            <ArrowDown size={14} className="text-[var(--color-mq-text-muted)]" />
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-[var(--color-mq-accent)]" />
            <span className="text-[var(--font-size-small)] font-mono text-[var(--color-mq-text-primary)]">
              Feature Version: {model.featureVersion}
            </span>
          </div>
          <div className="ml-3 border-l-2 border-[var(--color-mq-border)] pl-4 py-1">
            <ArrowDown size={14} className="text-[var(--color-mq-text-muted)]" />
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-[var(--color-mq-accent)]" />
            <span className="text-[var(--font-size-small)] font-mono text-[var(--color-mq-text-primary)]">
              Experiment: {model.experimentId}
            </span>
          </div>
          <div className="ml-3 border-l-2 border-[var(--color-mq-border)] pl-4 py-1">
            <ArrowDown size={14} className="text-[var(--color-mq-text-muted)]" />
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-[var(--color-mq-success)]" />
            <span className="text-[var(--font-size-small)] font-mono text-[var(--color-mq-text-primary)]">
              Validation: {model.validationScore > 0 ? (model.validationScore * 100).toFixed(1) + '%' : '—'}
            </span>
          </div>
          <div className="ml-3 border-l-2 border-[var(--color-mq-border)] pl-4 py-1">
            <ArrowDown size={14} className="text-[var(--color-mq-text-muted)]" />
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-[var(--color-mq-success)]" />
            <span className="text-[var(--font-size-small)] font-mono text-[var(--color-mq-text-primary)]">
              Calibration: {model.calibrationScore > 0 ? (model.calibrationScore * 100).toFixed(1) + '%' : '—'}
            </span>
          </div>
          <div className="ml-3 border-l-2 border-[var(--color-mq-border)] pl-4 py-1">
            <ArrowDown size={14} className="text-[var(--color-mq-text-muted)]" />
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-[var(--color-mq-success)]" />
            <span className="text-[var(--font-size-small)] font-mono text-[var(--color-mq-text-primary)]">
              Evaluation: {model.evaluationScore > 0 ? (model.evaluationScore * 100).toFixed(1) + '%' : '—'}
            </span>
          </div>
          <div className="ml-3 border-l-2 border-[var(--color-mq-border)] pl-4 py-1">
            <ArrowDown size={14} className="text-[var(--color-mq-text-muted)]" />
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-[var(--color-mq-warning)]" />
            <span className="text-[var(--font-size-small)] font-mono text-[var(--color-mq-text-primary)]">
              Registry: {model.modelVersion}
            </span>
          </div>
          <div className="ml-3 border-l-2 border-[var(--color-mq-border)] pl-4 py-1">
            <ArrowDown size={14} className="text-[var(--color-mq-text-muted)]" />
          </div>
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${model.lifecycleStatus === 'PRODUCTION' ? 'bg-[var(--color-mq-success)]' : 'bg-[var(--color-mq-text-muted)]'}`} />
            <span className="text-[var(--font-size-small)] font-mono text-[var(--color-mq-text-primary)]">
              Production: {model.lifecycleStatus}
            </span>
          </div>
        </div>
      )
    }
  ];

  return (
    <MQInspector
      title={`Model Registry: ${model.modelVersion}`}
      onClose={onClose}
    >
      <div className="space-y-6">
        {sections.map((section, idx) => (
          <div key={idx}>
            <h4 className="text-[var(--font-size-small)] font-semibold text-[var(--color-mq-text-primary)] mb-3 uppercase tracking-wide">
              {section.title}
            </h4>
            {section.content}
          </div>
        ))}
      </div>
    </MQInspector>
  );
}
