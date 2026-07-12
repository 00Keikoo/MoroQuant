'use client';

import React from 'react';
import { MQPanel, MQStatusBadge, MQProgressBar } from '@/components/mqds';
import { Feature } from '@/lib/mock-data/features';
import { Cpu, Clock, Database, TrendingUp, Hash, Activity } from 'lucide-react';

interface FeatureInspectorProps {
  feature: Feature;
  onClose: () => void;
}

export function FeatureInspector({ feature, onClose }: FeatureInspectorProps) {
  const statusMap: Record<string, 'success' | 'failure' | 'warning' | 'running' | 'pending'> = {
    ACTIVE: 'success',
    EXPERIMENTAL: 'warning',
    VALIDATING: 'running',
    DEPRECATED: 'pending',
    FAILED: 'failure',
    ARCHIVED: 'pending'
  };

  const getImportanceColor = (score: number) => {
    if (score >= 0.8) return 'var(--color-mq-success)';
    if (score >= 0.6) return 'var(--color-mq-warning)';
    return 'var(--color-mq-failure)';
  };

  const getNullRateColor = (rate: number) => {
    if (rate < 0.05) return 'var(--color-mq-success)';
    if (rate < 0.15) return 'var(--color-mq-warning)';
    return 'var(--color-mq-failure)';
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-[var(--color-mq-bg-secondary)] border border-[var(--color-mq-border)] rounded-[var(--radius-minimal)] w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
        <div className="flex items-center justify-between p-4 border-b border-[var(--color-mq-border)]">
          <div className="flex items-center gap-3">
            <h2 className="text-[var(--font-size-h4)] font-bold text-[var(--color-mq-text-primary)] font-mono">
              {feature.name}
            </h2>
            <span className="text-[var(--font-size-body)] text-[var(--color-mq-text-secondary)] font-mono">
              {feature.version}
            </span>
            <MQStatusBadge status={statusMap[feature.status]} label={feature.status} />
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
              <MQPanel title="Feature Metadata">
                <div className="space-y-3">
                  <div>
                    <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)] mb-1">
                      Feature ID
                    </div>
                    <div className="text-[var(--font-size-body)] font-mono text-[var(--color-mq-text-primary)]">
                      {feature.id}
                    </div>
                  </div>
                  <div>
                    <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)] mb-1">
                      Category
                    </div>
                    <div className="text-[var(--font-size-body)] font-mono text-[var(--color-mq-text-primary)]">
                      {feature.category}
                    </div>
                  </div>
                  <div>
                    <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)] mb-1">
                      Type
                    </div>
                    <div className="text-[var(--font-size-body)] font-mono text-[var(--color-mq-text-primary)]">
                      {feature.type}
                    </div>
                  </div>
                  <div>
                    <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)] mb-1">
                      Created
                    </div>
                    <div className="text-[var(--font-size-body)] font-mono text-[var(--color-mq-text-primary)]">
                      {new Date(feature.created).toLocaleString()}
                    </div>
                  </div>
                  <div>
                    <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)] mb-1">
                      Description
                    </div>
                    <div className="text-[var(--font-size-small)] text-[var(--color-mq-text-secondary)]">
                      {feature.description}
                    </div>
                  </div>
                </div>
              </MQPanel>

              <MQPanel title="Usage Statistics">
                <div className="space-y-3">
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)] mb-1">
                        Used by Datasets
                      </div>
                      <div className="text-[var(--font-size-h4)] font-mono text-[var(--color-mq-text-primary)]">
                        {feature.usedByDatasets}
                      </div>
                    </div>
                    <div>
                      <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)] mb-1">
                        Used by Experiments
                      </div>
                      <div className="text-[var(--font-size-h4)] font-mono text-[var(--color-mq-text-primary)]">
                        {feature.usedByExperiments}
                      </div>
                    </div>
                  </div>
                  {feature.computeTime && (
                    <div>
                      <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)] mb-1">
                        Compute Time
                      </div>
                      <div className="text-[var(--font-size-body)] font-mono text-[var(--color-mq-text-primary)]">
                        {feature.computeTime}
                      </div>
                    </div>
                  )}
                </div>
              </MQPanel>

              {feature.dependencies && feature.dependencies.length > 0 && (
                <MQPanel title="Dependencies">
                  <div className="space-y-2">
                    {feature.dependencies.map((dep, idx) => (
                      <div key={idx} className="text-[var(--font-size-small)] font-mono text-[var(--color-mq-text-secondary)]">
                        • {dep}
                      </div>
                    ))}
                  </div>
                </MQPanel>
              )}
            </div>

            <div className="space-y-4">
              <MQPanel title="Quality Metrics">
                <div className="space-y-4">
                  <div>
                    <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)] mb-2">
                      Feature Importance
                    </div>
                    <div className="text-[var(--font-size-h3)] font-mono mb-2" style={{ color: getImportanceColor(feature.importance) }}>
                      {(feature.importance * 100).toFixed(1)}%
                    </div>
                    <MQProgressBar
                      value={feature.importance * 100}
                      max={100}
                      color={getImportanceColor(feature.importance)}
                    />
                  </div>
                  <div>
                    <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)] mb-2">
                      Null Rate
                    </div>
                    <div className="text-[var(--font-size-h4)] font-mono mb-2" style={{ color: getNullRateColor(feature.nullRate) }}>
                      {(feature.nullRate * 100).toFixed(2)}%
                    </div>
                    <MQProgressBar
                      value={feature.nullRate * 100}
                      max={100}
                      color={getNullRateColor(feature.nullRate)}
                    />
                  </div>
                  {feature.correlation !== undefined && (
                    <div className="pt-2 border-t border-[var(--color-mq-border)]">
                      <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)] mb-2">
                        Target Correlation
                      </div>
                      <div className="text-[var(--font-size-body)] font-mono text-[var(--color-mq-text-primary)]">
                        {feature.correlation.toFixed(2)}
                      </div>
                    </div>
                  )}
                </div>
              </MQPanel>

              {feature.statistics && (
                <MQPanel title="Statistics">
                  <div className="space-y-3">
                    {feature.statistics.mean !== undefined && (
                      <div className="flex justify-between">
                        <span className="text-[var(--font-size-small)] text-[var(--color-mq-text-secondary)]">
                          Mean
                        </span>
                        <span className="text-[var(--font-size-small)] font-mono text-[var(--color-mq-text-primary)]">
                          {feature.statistics.mean.toFixed(2)}
                        </span>
                      </div>
                    )}
                    {feature.statistics.std !== undefined && (
                      <div className="flex justify-between">
                        <span className="text-[var(--font-size-small)] text-[var(--color-mq-text-secondary)]">
                          Std Dev
                        </span>
                        <span className="text-[var(--font-size-small)] font-mono text-[var(--color-mq-text-primary)]">
                          {feature.statistics.std.toFixed(2)}
                        </span>
                      </div>
                    )}
                    {feature.statistics.min !== undefined && (
                      <div className="flex justify-between">
                        <span className="text-[var(--font-size-small)] text-[var(--color-mq-text-secondary)]">
                          Min
                        </span>
                        <span className="text-[var(--font-size-small)] font-mono text-[var(--color-mq-text-primary)]">
                          {feature.statistics.min.toFixed(2)}
                        </span>
                      </div>
                    )}
                    {feature.statistics.max !== undefined && (
                      <div className="flex justify-between">
                        <span className="text-[var(--font-size-small)] text-[var(--color-mq-text-secondary)]">
                          Max
                        </span>
                        <span className="text-[var(--font-size-small)] font-mono text-[var(--color-mq-text-primary)]">
                          {feature.statistics.max.toFixed(2)}
                        </span>
                      </div>
                    )}
                    {feature.statistics.uniqueValues !== undefined && (
                      <div className="flex justify-between">
                        <span className="text-[var(--font-size-small)] text-[var(--color-mq-text-secondary)]">
                          Unique Values
                        </span>
                        <span className="text-[var(--font-size-small)] font-mono text-[var(--color-mq-text-primary)]">
                          {feature.statistics.uniqueValues}
                        </span>
                      </div>
                    )}
                  </div>
                </MQPanel>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
