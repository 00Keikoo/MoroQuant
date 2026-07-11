'use client';

import React from 'react';
import { MQPanel, MQTimeline, MQStatusBadge } from '@/components/mqds';
import { Experiment } from '@/lib/mock-data/experiments';
import { Database, Cpu, Clock, TrendingUp, GitBranch, CheckCircle, AlertCircle } from 'lucide-react';

interface ExperimentInspectorProps {
  experiment: Experiment;
  onClose: () => void;
}

export function ExperimentInspector({ experiment, onClose }: ExperimentInspectorProps) {
  const timelineEvents = [
    {
      id: '1',
      timestamp: new Date(experiment.created).toLocaleString(),
      title: 'Experiment Created',
      description: `Run ID: ${experiment.runId}`,
      icon: <GitBranch size={14} />,
      status: 'success' as const
    },
    {
      id: '2',
      timestamp: new Date(new Date(experiment.created).getTime() + 5 * 60000).toLocaleString(),
      title: 'Dataset Loaded',
      description: experiment.dataset,
      icon: <Database size={14} />,
      status: 'success' as const
    },
    {
      id: '3',
      timestamp: new Date(new Date(experiment.created).getTime() + 10 * 60000).toLocaleString(),
      title: 'Training Started',
      description: `${experiment.metadata.epochs} epochs, batch size ${experiment.metadata.batchSize}`,
      icon: <Cpu size={14} />,
      status: experiment.status === 'FAILED' ? 'failure' as const : 'success' as const
    }
  ];

  if (['VALIDATING', 'CALIBRATING', 'PAPER', 'PROMOTION', 'PRODUCTION'].includes(experiment.status)) {
    const event: any = {
      id: '4',
      timestamp: new Date(new Date(experiment.created).getTime() + parseInt(experiment.duration) * 60000).toLocaleString(),
      title: 'Training Completed',
      icon: <CheckCircle size={14} />,
      status: 'success' as const
    };
    if (experiment.metrics) {
      event.description = `Train Loss: ${experiment.metrics.trainLoss.toFixed(3)}, Val Loss: ${experiment.metrics.valLoss.toFixed(3)}`;
    }
    timelineEvents.push(event);
  }

  if (['VALIDATING', 'CALIBRATING', 'PAPER', 'PROMOTION', 'PRODUCTION'].includes(experiment.status)) {
    timelineEvents.push({
      id: '5',
      timestamp: new Date(new Date(experiment.created).getTime() + parseInt(experiment.duration) * 60000 + 15 * 60000).toLocaleString(),
      title: 'Validation Started',
      description: '5-fold cross-validation',
      icon: <TrendingUp size={14} />,
      status: 'success' as const
    });
  }

  if (['CALIBRATING', 'PAPER', 'PROMOTION', 'PRODUCTION'].includes(experiment.status)) {
    timelineEvents.push({
      id: '6',
      timestamp: new Date(new Date(experiment.created).getTime() + parseInt(experiment.duration) * 60000 + 45 * 60000).toLocaleString(),
      title: 'Calibration',
      description: 'Probability calibration applied',
      icon: <TrendingUp size={14} />,
      status: 'success' as const
    });
  }

  if (['PAPER', 'PROMOTION', 'PRODUCTION'].includes(experiment.status)) {
    const event: any = {
      id: '7',
      timestamp: new Date(new Date(experiment.created).getTime() + parseInt(experiment.duration) * 60000 + 60 * 60000).toLocaleString(),
      title: 'Paper Trading',
      icon: <TrendingUp size={14} />,
      status: 'success' as const
    };
    if (experiment.metrics) {
      event.description = `Sharpe: ${experiment.metrics.sharpeRatio?.toFixed(2)}, Max DD: ${(experiment.metrics.maxDrawdown || 0) * 100}%`;
    }
    timelineEvents.push(event);
  }

  if (experiment.status === 'FAILED') {
    timelineEvents.push({
      id: 'fail',
      timestamp: new Date(new Date(experiment.created).getTime() + parseInt(experiment.duration) * 60000).toLocaleString(),
      title: 'Training Failed',
      description: 'NaN loss detected at epoch 45',
      icon: <AlertCircle size={14} />,
      status: 'failure' as const
    });
  }

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

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-[var(--color-mq-bg-secondary)] border border-[var(--color-mq-border)] rounded-[var(--radius-minimal)] w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
        <div className="flex items-center justify-between p-4 border-b border-[var(--color-mq-border)]">
          <div className="flex items-center gap-3">
            <h2 className="text-[var(--font-size-h4)] font-bold text-[var(--color-mq-text-primary)]">
              {experiment.runId}
            </h2>
            <MQStatusBadge status={statusMap[experiment.status]} label={experiment.status} />
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
              <MQPanel title="Run Metadata">
                <div className="space-y-3">
                  <div>
                    <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)] mb-1">
                      Algorithm
                    </div>
                    <div className="text-[var(--font-size-body)] font-mono text-[var(--color-mq-text-primary)]">
                      {experiment.algorithm}
                    </div>
                  </div>
                  <div>
                    <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)] mb-1">
                      Dataset
                    </div>
                    <div className="text-[var(--font-size-body)] font-mono text-[var(--color-mq-text-primary)]">
                      {experiment.dataset}
                    </div>
                  </div>
                  <div>
                    <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)] mb-1">
                      Feature Version
                    </div>
                    <div className="text-[var(--font-size-body)] font-mono text-[var(--color-mq-text-primary)]">
                      {experiment.featureVersion}
                    </div>
                  </div>
                  <div>
                    <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)] mb-1">
                      Duration
                    </div>
                    <div className="text-[var(--font-size-body)] font-mono text-[var(--color-mq-text-primary)]">
                      {experiment.duration}
                    </div>
                  </div>
                  <div>
                    <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)] mb-1">
                      Created
                    </div>
                    <div className="text-[var(--font-size-body)] font-mono text-[var(--color-mq-text-primary)]">
                      {new Date(experiment.created).toLocaleString()}
                    </div>
                  </div>
                </div>
              </MQPanel>

              <MQPanel title="Hyperparameters">
                <div className="space-y-3">
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)] mb-1">
                        Epochs
                      </div>
                      <div className="text-[var(--font-size-body)] font-mono text-[var(--color-mq-text-primary)]">
                        {experiment.metadata.epochs}
                      </div>
                    </div>
                    <div>
                      <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)] mb-1">
                        Batch Size
                      </div>
                      <div className="text-[var(--font-size-body)] font-mono text-[var(--color-mq-text-primary)]">
                        {experiment.metadata.batchSize}
                      </div>
                    </div>
                    <div>
                      <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)] mb-1">
                        Learning Rate
                      </div>
                      <div className="text-[var(--font-size-body)] font-mono text-[var(--color-mq-text-primary)]">
                        {experiment.metadata.learningRate}
                      </div>
                    </div>
                    <div>
                      <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)] mb-1">
                        Optimizer
                      </div>
                      <div className="text-[var(--font-size-body)] font-mono text-[var(--color-mq-text-primary)]">
                        {experiment.metadata.optimizer}
                      </div>
                    </div>
                    <div className="col-span-2">
                      <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)] mb-1">
                        Loss Function
                      </div>
                      <div className="text-[var(--font-size-body)] font-mono text-[var(--color-mq-text-primary)]">
                        {experiment.metadata.loss}
                      </div>
                    </div>
                  </div>
                </div>
              </MQPanel>

              {experiment.metrics && (
                <MQPanel title="Training Metrics">
                  <div className="space-y-3">
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)] mb-1">
                          Train Loss
                        </div>
                        <div className="text-[var(--font-size-body)] font-mono text-[var(--color-mq-text-primary)]">
                          {experiment.metrics.trainLoss.toFixed(3)}
                        </div>
                      </div>
                      <div>
                        <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)] mb-1">
                          Val Loss
                        </div>
                        <div className="text-[var(--font-size-body)] font-mono text-[var(--color-mq-text-primary)]">
                          {experiment.metrics.valLoss.toFixed(3)}
                        </div>
                      </div>
                      {experiment.metrics.sharpeRatio && (
                        <div>
                          <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)] mb-1">
                            Sharpe Ratio
                          </div>
                          <div className="text-[var(--font-size-body)] font-mono text-[var(--color-mq-success)]">
                            {experiment.metrics.sharpeRatio.toFixed(2)}
                          </div>
                        </div>
                      )}
                      {experiment.metrics.maxDrawdown && (
                        <div>
                          <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)] mb-1">
                            Max Drawdown
                          </div>
                          <div className="text-[var(--font-size-body)] font-mono text-[var(--color-mq-warning)]">
                            {(experiment.metrics.maxDrawdown * 100).toFixed(1)}%
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                </MQPanel>
              )}
            </div>

            <div>
              <MQPanel title="Research Timeline">
                <MQTimeline events={timelineEvents} />
              </MQPanel>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
