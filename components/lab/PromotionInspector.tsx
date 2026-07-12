'use client';

import React from 'react';
import { MQPanel, MQStatusBadge, MQProgressBar } from '@/components/mqds';
import { ArrowUpCircle } from 'lucide-react';

type PromotionRequest = {
  id: string;
  modelName: string;
  version: string;
  fromEnvironment: string;
  toEnvironment: string;
  requestedBy: string;
  approvalScore: number;
  gatesPassed: number;
  gatesTotal: number;
  riskLevel: string;
  status: 'APPROVED' | 'PENDING' | 'REJECTED' | 'IN_REVIEW' | 'DEPLOYED';
  created: string;
};

interface PromotionInspectorProps {
  promotion: PromotionRequest;
  onClose: () => void;
}

export function PromotionInspector({ promotion, onClose }: PromotionInspectorProps) {
  const statusMap: Record<string, 'success' | 'failure' | 'warning' | 'running' | 'pending'> = {
    APPROVED: 'success',
    DEPLOYED: 'success',
    REJECTED: 'failure',
    IN_REVIEW: 'warning',
    PENDING: 'pending'
  };

  const getScoreColor = (score: number) => {
    if (score >= 0.85) return 'var(--color-mq-success)';
    if (score >= 0.70) return 'var(--color-mq-warning)';
    return 'var(--color-mq-failure)';
  };

  const getRiskColor = (risk: string) => {
    if (risk === 'LOW') return 'var(--color-mq-success)';
    if (risk === 'MEDIUM') return 'var(--color-mq-warning)';
    return 'var(--color-mq-failure)';
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-[var(--color-mq-bg-secondary)] border border-[var(--color-mq-border)] rounded-[var(--radius-minimal)] w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
        <div className="flex items-center justify-between p-4 border-b border-[var(--color-mq-border)]">
          <div className="flex items-center gap-3">
            <h2 className="text-[var(--font-size-h4)] font-bold text-[var(--color-mq-text-primary)] font-mono">
              {promotion.modelName}
            </h2>
            <span className="text-[var(--font-size-body)] text-[var(--color-mq-text-secondary)] font-mono">
              {promotion.version}
            </span>
            <MQStatusBadge status={statusMap[promotion.status]} label={promotion.status} />
          </div>
          <button
            onClick={onClose}
            className="text-[var(--color-mq-text-secondary)] hover:text-[var(--color-mq-text-primary)] transition-colors"
          >
            ✕
          </button>
        </div>

        <div className="flex-1 overflow-auto p-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div className="space-y-4">
              <MQPanel title="Promotion Details">
                <div className="space-y-3">
                  <div>
                    <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)] mb-1">
                      Request ID
                    </div>
                    <div className="text-[var(--font-size-body)] font-mono text-[var(--color-mq-text-primary)]">
                      {promotion.id}
                    </div>
                  </div>
                  <div>
                    <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)] mb-1">
                      Promotion Path
                    </div>
                    <div className="text-[var(--font-size-body)] font-mono text-[var(--color-mq-text-primary)]">
                      {promotion.fromEnvironment} → {promotion.toEnvironment}
                    </div>
                  </div>
                  <div>
                    <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)] mb-1">
                      Requested By
                    </div>
                    <div className="text-[var(--font-size-body)] font-mono text-[var(--color-mq-text-primary)]">
                      {promotion.requestedBy}
                    </div>
                  </div>
                  <div>
                    <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)] mb-1">
                      Risk Level
                    </div>
                    <div className="text-[var(--font-size-body)] font-mono" style={{ color: getRiskColor(promotion.riskLevel) }}>
                      {promotion.riskLevel}
                    </div>
                  </div>
                  <div>
                    <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)] mb-1">
                      Created
                    </div>
                    <div className="text-[var(--font-size-body)] font-mono text-[var(--color-mq-text-primary)]">
                      {new Date(promotion.created).toLocaleString()}
                    </div>
                  </div>
                </div>
              </MQPanel>
            </div>

            <div className="space-y-4">
              <MQPanel title="Gate Checks">
                <div className="space-y-4">
                  <div>
                    <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)] mb-2">
                      Approval Score
                    </div>
                    <div className="text-[var(--font-size-h3)] font-mono mb-2" style={{ color: getScoreColor(promotion.approvalScore) }}>
                      {(promotion.approvalScore * 100).toFixed(0)}%
                    </div>
                    <MQProgressBar
                      value={promotion.approvalScore * 100}
                      max={100}
                      color={getScoreColor(promotion.approvalScore)}
                    />
                  </div>
                  <div className="pt-2 border-t border-[var(--color-mq-border)]">
                    <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)] mb-2">
                      Gates Passed
                    </div>
                    <div className="text-[var(--font-size-h4)] font-mono mb-2 text-[var(--color-mq-text-primary)]">
                      {promotion.gatesPassed} / {promotion.gatesTotal}
                    </div>
                    <MQProgressBar
                      value={(promotion.gatesPassed / promotion.gatesTotal) * 100}
                      max={100}
                      color={promotion.gatesPassed === promotion.gatesTotal ? 'var(--color-mq-success)' : 'var(--color-mq-warning)'}
                    />
                  </div>
                </div>
              </MQPanel>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
