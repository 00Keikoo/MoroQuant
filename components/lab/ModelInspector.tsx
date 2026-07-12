'use client';

import React from 'react';
import { MQPanel, MQStatusBadge, MQProgressBar } from '@/components/mqds';
import { Clock } from 'lucide-react';

type Model = {
  id: string;
  name: string;
  version: string;
  architecture: string;
  framework: string;
  accuracy: number;
  parameters: number;
  trainingTime: string;
  deployments: number;
  status: 'PRODUCTION' | 'STAGING' | 'EXPERIMENTAL' | 'DEPRECATED' | 'ARCHIVED';
  created: string;
};

interface ModelInspectorProps {
  model: Model;
  onClose: () => void;
}

export function ModelInspector({ model, onClose }: ModelInspectorProps) {
  const statusMap: Record<string, 'success' | 'failure' | 'warning' | 'running' | 'pending'> = {
    PRODUCTION: 'success',
    STAGING: 'warning',
    EXPERIMENTAL: 'running',
    DEPRECATED: 'pending',
    ARCHIVED: 'pending'
  };

  const getAccuracyColor = (score: number) => {
    if (score >= 0.70) return 'var(--color-mq-success)';
    if (score >= 0.60) return 'var(--color-mq-warning)';
    return 'var(--color-mq-failure)';
  };

  const getParameterSize = (params: number) => {
    if (params >= 10000000) return 'Large';
    if (params >= 5000000) return 'Medium';
    return 'Small';
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-[var(--color-mq-bg-secondary)] border border-[var(--color-mq-border)] rounded-[var(--radius-minimal)] w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
        <div className="flex items-center justify-between p-4 border-b border-[var(--color-mq-border)]">
          <div className="flex items-center gap-3">
            <h2 className="text-[var(--font-size-h4)] font-bold text-[var(--color-mq-text-primary)] font-mono">
              {model.name}
            </h2>
            <span className="text-[var(--font-size-body)] text-[var(--color-mq-text-secondary)] font-mono">
              {model.version}
            </span>
            <MQStatusBadge status={statusMap[model.status]} label={model.status} />
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
              <MQPanel title="Model Metadata">
                <div className="space-y-3">
                  <div>
                    <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)] mb-1">
                      Model ID
                    </div>
                    <div className="text-[var(--font-size-body)] font-mono text-[var(--color-mq-text-primary)]">
                      {model.id}
                    </div>
                  </div>
                  <div>
                    <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)] mb-1">
                      Architecture
                    </div>
                    <div className="text-[var(--font-size-body)] font-mono text-[var(--color-mq-text-primary)]">
                      {model.architecture}
                    </div>
                  </div>
                  <div>
                    <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)] mb-1">
                      Framework
                    </div>
                    <div className="text-[var(--font-size-body)] font-mono text-[var(--color-mq-text-primary)]">
                      {model.framework}
                    </div>
                  </div>
                  <div>
                    <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)] mb-1">
                      Parameters
                    </div>
                    <div className="text-[var(--font-size-body)] font-mono text-[var(--color-mq-text-primary)]">
                      {(model.parameters / 1000000).toFixed(1)}M ({getParameterSize(model.parameters)})
                    </div>
                  </div>
                  <div>
                    <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)] mb-1">
                      Training Time
                    </div>
                    <div className="text-[var(--font-size-body)] font-mono text-[var(--color-mq-text-primary)]">
                      {model.trainingTime}
                    </div>
                  </div>
                  <div>
                    <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)] mb-1">
                      Created
                    </div>
                    <div className="text-[var(--font-size-body)] font-mono text-[var(--color-mq-text-primary)]">
                      {new Date(model.created).toLocaleString()}
                    </div>
                  </div>
                </div>
              </MQPanel>

              <MQPanel title="Deployment Statistics">
                <div className="space-y-3">
                  <div>
                    <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)] mb-1">
                      Active Deployments
                    </div>
                    <div className="text-[var(--font-size-h3)] font-mono text-[var(--color-mq-text-primary)]">
                      {model.deployments}
                    </div>
                  </div>
                </div>
              </MQPanel>
            </div>

            <div className="space-y-4">
              <MQPanel title="Performance Metrics">
                <div className="space-y-4">
                  <div>
                    <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)] mb-2">
                      Model Accuracy
                    </div>
                    <div className="text-[var(--font-size-h3)] font-mono mb-2" style={{ color: getAccuracyColor(model.accuracy) }}>
                      {(model.accuracy * 100).toFixed(1)}%
                    </div>
                    <MQProgressBar
                      value={model.accuracy * 100}
                      max={100}
                      color={getAccuracyColor(model.accuracy)}
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
