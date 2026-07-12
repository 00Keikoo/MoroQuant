'use client';

import { useState } from 'react';
import { X } from 'lucide-react';
import { MQStatusBadge } from '@/components/mqds';
import { PromotionCandidate } from '@/lib/mock-data/promotion';

interface PromotionInspectorProps {
  candidate: PromotionCandidate;
  onClose: () => void;
}

export function PromotionInspector({ candidate, onClose }: PromotionInspectorProps) {
  const [activeTab, setActiveTab] = useState('general');

  const tabs = [
    'general',
    'validation',
    'calibration',
    'evaluation',
    'risk-review',
    'promotion-checklist',
    'decision',
    'rollback-plan',
    'lineage'
  ];

  const getStageStatus = (stage: string): 'success' | 'failure' | 'warning' | 'pending' => {
    if (stage === 'validation') return candidate.validationPassed ? 'success' : 'failure';
    if (stage === 'calibration') return candidate.calibrationPassed ? 'success' : 'failure';
    if (stage === 'evaluation') return candidate.evaluationPassed ? 'success' : 'failure';
    if (stage === 'risk-review') return candidate.riskReviewPassed ? 'success' : 'failure';
    return 'pending';
  };

  const getDecisionStatus = (): 'success' | 'failure' | 'warning' | 'pending' => {
    if (candidate.decision === 'APPROVED') return 'success';
    if (candidate.decision === 'REJECTED') return 'failure';
    if (candidate.decision === 'ON_HOLD') return 'warning';
    return 'pending';
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-[var(--color-mq-bg-primary)] border border-[var(--color-mq-border)] rounded-[var(--radius-minimal)] w-full max-w-4xl max-h-[90vh] flex flex-col">
        <div className="flex items-center justify-between p-4 border-b border-[var(--color-mq-border)]">
          <div>
            <h2 className="text-[var(--font-size-h4)] font-mono text-[var(--color-mq-text-primary)]">
              Promotion Candidate: {candidate.modelVersion}
            </h2>
            <p className="text-[var(--font-size-small)] text-[var(--color-mq-text-secondary)] font-mono mt-1">
              {candidate.id} • {candidate.experimentId}
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-[var(--color-mq-text-secondary)] hover:text-[var(--color-mq-text-primary)]"
          >
            <X size={20} />
          </button>
        </div>

        <div className="flex border-b border-[var(--color-mq-border)] overflow-x-auto">
          {tabs.map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 text-[var(--font-size-small)] font-mono whitespace-nowrap border-b-2 transition-colors ${
                activeTab === tab
                  ? 'border-[var(--color-mq-accent)] text-[var(--color-mq-accent)]'
                  : 'border-transparent text-[var(--color-mq-text-secondary)] hover:text-[var(--color-mq-text-primary)]'
              }`}
            >
              {tab.split('-').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}
            </button>
          ))}
        </div>

        <div className="flex-1 overflow-y-auto p-4">
          {activeTab === 'general' && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-muted)] mb-1">Model Version</div>
                  <div className="text-[var(--font-size-body)] text-[var(--color-mq-text-primary)] font-mono">{candidate.modelVersion}</div>
                </div>
                <div>
                  <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-muted)] mb-1">Experiment ID</div>
                  <div className="text-[var(--font-size-body)] text-[var(--color-mq-text-primary)] font-mono">{candidate.experimentId}</div>
                </div>
                <div>
                  <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-muted)] mb-1">Dataset Version</div>
                  <div className="text-[var(--font-size-body)] text-[var(--color-mq-text-primary)] font-mono">{candidate.datasetVersion}</div>
                </div>
                <div>
                  <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-muted)] mb-1">Feature Version</div>
                  <div className="text-[var(--font-size-body)] text-[var(--color-mq-text-primary)] font-mono">{candidate.featureVersion}</div>
                </div>
                <div>
                  <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-muted)] mb-1">Current Stage</div>
                  <div className="text-[var(--font-size-body)] text-[var(--color-mq-text-primary)] font-mono">{candidate.currentStage}</div>
                </div>
                <div>
                  <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-muted)] mb-1">Reviewer</div>
                  <div className="text-[var(--font-size-body)] text-[var(--color-mq-text-primary)] font-mono">{candidate.reviewer}</div>
                </div>
                <div>
                  <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-muted)] mb-1">Promotion ETA</div>
                  <div className="text-[var(--font-size-body)] text-[var(--color-mq-text-primary)] font-mono">{candidate.promotionEta}</div>
                </div>
                <div>
                  <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-muted)] mb-1">Submitted At</div>
                  <div className="text-[var(--font-size-body)] text-[var(--color-mq-text-primary)] font-mono">{new Date(candidate.submittedAt).toLocaleString()}</div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'validation' && (
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <MQStatusBadge status={getStageStatus('validation')} label={candidate.validationPassed ? 'PASSED' : 'FAILED'} />
              </div>
              <div>
                <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-muted)] mb-1">Validation Score</div>
                <div className="text-[var(--font-size-h3)] text-[var(--color-mq-text-primary)] font-mono">
                  {(candidate.validationScore * 100).toFixed(1)}%
                </div>
              </div>
              <div>
                <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-muted)] mb-1">Details</div>
                <div className="text-[var(--font-size-body)] text-[var(--color-mq-text-secondary)] font-mono">
                  {candidate.validationPassed ? 'Model passed all validation checks.' : 'Model failed validation. See blockers for details.'}
                </div>
              </div>
            </div>
          )}

          {activeTab === 'calibration' && (
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <MQStatusBadge status={getStageStatus('calibration')} label={candidate.calibrationPassed ? 'PASSED' : 'FAILED'} />
              </div>
              <div>
                <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-muted)] mb-1">Calibration Score</div>
                <div className="text-[var(--font-size-h3)] text-[var(--color-mq-text-primary)] font-mono">
                  {candidate.calibrationScore > 0 ? (candidate.calibrationScore * 100).toFixed(1) + '%' : '—'}
                </div>
              </div>
              <div>
                <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-muted)] mb-1">Details</div>
                <div className="text-[var(--font-size-body)] text-[var(--color-mq-text-secondary)] font-mono">
                  {candidate.calibrationPassed ? 'Model calibration is within acceptable bounds.' : 'Model calibration failed. See blockers for details.'}
                </div>
              </div>
            </div>
          )}

          {activeTab === 'evaluation' && (
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <MQStatusBadge status={getStageStatus('evaluation')} label={candidate.evaluationPassed ? 'PASSED' : 'FAILED'} />
              </div>
              <div>
                <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-muted)] mb-1">Evaluation Score</div>
                <div className="text-[var(--font-size-h3)] text-[var(--color-mq-text-primary)] font-mono">
                  {candidate.evaluationScore > 0 ? (candidate.evaluationScore * 100).toFixed(1) + '%' : '—'}
                </div>
              </div>
              <div>
                <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-muted)] mb-1">Promotion Score</div>
                <div className="text-[var(--font-size-h3)] text-[var(--color-mq-text-primary)] font-mono">
                  {candidate.promotionScore > 0 ? (candidate.promotionScore * 100).toFixed(1) + '%' : '—'}
                </div>
              </div>
            </div>
          )}

          {activeTab === 'risk-review' && (
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <MQStatusBadge status={getStageStatus('risk-review')} label={candidate.riskReviewPassed ? 'PASSED' : 'FAILED'} />
              </div>
              <div>
                <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-muted)] mb-1">Risk Score</div>
                <div className="text-[var(--font-size-h3)] text-[var(--color-mq-text-primary)] font-mono">
                  {(candidate.riskScore * 100).toFixed(1)}%
                </div>
              </div>
              <div>
                <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-muted)] mb-1">Critical Issues</div>
                <div className="text-[var(--font-size-h3)] text-[var(--color-mq-text-primary)] font-mono">
                  {candidate.criticalIssues}
                </div>
              </div>
            </div>
          )}

          {activeTab === 'promotion-checklist' && (
            <div className="space-y-2">
              <div className="flex items-center gap-2 p-2 bg-[var(--color-mq-bg-secondary)] rounded">
                <span className={candidate.validationPassed ? 'text-[var(--color-mq-success)]' : 'text-[var(--color-mq-failure)]'}>
                  {candidate.validationPassed ? '✓' : '✗'}
                </span>
                <span className="text-[var(--font-size-body)] text-[var(--color-mq-text-primary)] font-mono">Validation Passed</span>
              </div>
              <div className="flex items-center gap-2 p-2 bg-[var(--color-mq-bg-secondary)] rounded">
                <span className={candidate.calibrationPassed ? 'text-[var(--color-mq-success)]' : 'text-[var(--color-mq-failure)]'}>
                  {candidate.calibrationPassed ? '✓' : '✗'}
                </span>
                <span className="text-[var(--font-size-body)] text-[var(--color-mq-text-primary)] font-mono">Calibration Passed</span>
              </div>
              <div className="flex items-center gap-2 p-2 bg-[var(--color-mq-bg-secondary)] rounded">
                <span className={candidate.evaluationPassed ? 'text-[var(--color-mq-success)]' : 'text-[var(--color-mq-failure)]'}>
                  {candidate.evaluationPassed ? '✓' : '✗'}
                </span>
                <span className="text-[var(--font-size-body)] text-[var(--color-mq-text-primary)] font-mono">Evaluation Passed</span>
              </div>
              <div className="flex items-center gap-2 p-2 bg-[var(--color-mq-bg-secondary)] rounded">
                <span className={candidate.riskReviewPassed ? 'text-[var(--color-mq-success)]' : 'text-[var(--color-mq-failure)]'}>
                  {candidate.riskReviewPassed ? '✓' : '✗'}
                </span>
                <span className="text-[var(--font-size-body)] text-[var(--color-mq-text-primary)] font-mono">Risk Review Passed</span>
              </div>
              <div className="flex items-center gap-2 p-2 bg-[var(--color-mq-bg-secondary)] rounded">
                <span className={candidate.rollbackPlan !== 'Not defined' ? 'text-[var(--color-mq-success)]' : 'text-[var(--color-mq-failure)]'}>
                  {candidate.rollbackPlan !== 'Not defined' ? '✓' : '✗'}
                </span>
                <span className="text-[var(--font-size-body)] text-[var(--color-mq-text-primary)] font-mono">Rollback Plan Defined</span>
              </div>
            </div>
          )}

          {activeTab === 'decision' && (
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <MQStatusBadge status={getDecisionStatus()} label={candidate.decision} />
              </div>
              <div>
                <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-muted)] mb-1">Reviewer</div>
                <div className="text-[var(--font-size-body)] text-[var(--color-mq-text-primary)] font-mono">{candidate.reviewer}</div>
              </div>
              {candidate.blockers.length > 0 && (
                <div>
                  <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-muted)] mb-1">Blockers</div>
                  <ul className="space-y-1">
                    {candidate.blockers.map((blocker, idx) => (
                      <li key={idx} className="text-[var(--font-size-body)] text-[var(--color-mq-failure)] font-mono">
                        • {blocker}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {activeTab === 'rollback-plan' && (
            <div className="space-y-4">
              <div>
                <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-muted)] mb-1">Rollback Strategy</div>
                <div className="text-[var(--font-size-body)] text-[var(--color-mq-text-primary)] font-mono">{candidate.rollbackPlan}</div>
              </div>
            </div>
          )}

          {activeTab === 'lineage' && (
            <div className="space-y-4">
              <div>
                <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-muted)] mb-1">Model Lineage</div>
                <div className="space-y-2">
                  <div className="text-[var(--font-size-body)] text-[var(--color-mq-text-secondary)] font-mono">
                    Dataset: {candidate.datasetVersion}
                  </div>
                  <div className="text-[var(--font-size-body)] text-[var(--color-mq-text-secondary)] font-mono">
                    Features: {candidate.featureVersion}
                  </div>
                  <div className="text-[var(--font-size-body)] text-[var(--color-mq-text-secondary)] font-mono">
                    Experiment: {candidate.experimentId}
                  </div>
                  <div className="text-[var(--font-size-body)] text-[var(--color-mq-text-secondary)] font-mono">
                    Model: {candidate.modelVersion}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
