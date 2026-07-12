'use client';

import React from 'react';
import { MQPanel, MQStatusBadge, MQProgressBar } from '@/components/mqds';
import { Dataset } from '@/lib/mock-data/datasets';
import { Database, Calendar, HardDrive, Hash, Activity, TrendingUp } from 'lucide-react';

interface DatasetInspectorProps {
  dataset: Dataset;
  onClose: () => void;
}

export function DatasetInspector({ dataset, onClose }: DatasetInspectorProps) {
  const statusMap: Record<string, 'success' | 'failure' | 'warning' | 'running' | 'pending'> = {
    FROZEN: 'success',
    BUILDING: 'running',
    VALIDATING: 'warning',
    FAILED: 'failure',
    ARCHIVED: 'pending'
  };

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${(bytes / Math.pow(k, i)).toFixed(2)} ${sizes[i]}`;
  };

  const getQualityColor = (score: number) => {
    if (score >= 99) return 'var(--color-mq-success)';
    if (score >= 97) return 'var(--color-mq-warning)';
    return 'var(--color-mq-failure)';
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-[var(--color-mq-bg-secondary)] border border-[var(--color-mq-border)] rounded-[var(--radius-minimal)] w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
        <div className="flex items-center justify-between p-4 border-b border-[var(--color-mq-border)]">
          <div className="flex items-center gap-3">
            <h2 className="text-[var(--font-size-h4)] font-bold text-[var(--color-mq-text-primary)] font-mono">
              {dataset.name}
            </h2>
            <span className="text-[var(--font-size-body)] text-[var(--color-mq-text-secondary)] font-mono">
              v{dataset.version}
            </span>
            <MQStatusBadge status={statusMap[dataset.status]} label={dataset.status} />
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
              <MQPanel title="Dataset Metadata">
                <div className="space-y-3">
                  <div>
                    <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)] mb-1">
                      Dataset ID
                    </div>
                    <div className="text-[var(--font-size-body)] font-mono text-[var(--color-mq-text-primary)]">
                      {dataset.id}
                    </div>
                  </div>
                  <div>
                    <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)] mb-1">
                      Exchange
                    </div>
                    <div className="text-[var(--font-size-body)] font-mono text-[var(--color-mq-text-primary)]">
                      {dataset.exchange}
                    </div>
                  </div>
                  <div>
                    <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)] mb-1">
                      Asset Class
                    </div>
                    <div className="text-[var(--font-size-body)] font-mono text-[var(--color-mq-text-primary)]">
                      {dataset.assetClass}
                    </div>
                  </div>
                  <div>
                    <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)] mb-1">
                      Timeframe
                    </div>
                    <div className="text-[var(--font-size-body)] font-mono text-[var(--color-mq-text-primary)]">
                      {dataset.timeframe}
                    </div>
                  </div>
                  <div>
                    <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)] mb-1">
                      Created
                    </div>
                    <div className="text-[var(--font-size-body)] font-mono text-[var(--color-mq-text-primary)]">
                      {new Date(dataset.created).toLocaleString()}
                    </div>
                  </div>
                  {dataset.fingerprint && (
                    <div>
                      <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)] mb-1">
                        Fingerprint
                      </div>
                      <div className="text-[var(--font-size-caption)] font-mono text-[var(--color-mq-text-muted)]">
                        {dataset.fingerprint}
                      </div>
                    </div>
                  )}
                </div>
              </MQPanel>

              <MQPanel title="Schema">
                <div className="space-y-3">
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)] mb-1">
                        Total Rows
                      </div>
                      <div className="text-[var(--font-size-h4)] font-mono text-[var(--color-mq-text-primary)]">
                        {dataset.rows.toLocaleString()}
                      </div>
                    </div>
                    <div>
                      <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)] mb-1">
                        Feature Count
                      </div>
                      <div className="text-[var(--font-size-h4)] font-mono text-[var(--color-mq-text-primary)]">
                        {dataset.features}
                      </div>
                    </div>
                  </div>
                  {dataset.sizeBytes && (
                    <div>
                      <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)] mb-1">
                        Storage Size
                      </div>
                      <div className="text-[var(--font-size-body)] font-mono text-[var(--color-mq-text-primary)]">
                        {formatBytes(dataset.sizeBytes)}
                      </div>
                    </div>
                  )}
                </div>
              </MQPanel>

              <MQPanel title="Coverage">
                <div className="space-y-3">
                  {dataset.startDate && dataset.endDate && (
                    <>
                      <div>
                        <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)] mb-1">
                          Start Date
                        </div>
                        <div className="text-[var(--font-size-body)] font-mono text-[var(--color-mq-text-primary)]">
                          {dataset.startDate}
                        </div>
                      </div>
                      <div>
                        <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)] mb-1">
                          End Date
                        </div>
                        <div className="text-[var(--font-size-body)] font-mono text-[var(--color-mq-text-primary)]">
                          {dataset.endDate}
                        </div>
                      </div>
                    </>
                  )}
                </div>
              </MQPanel>
            </div>

            <div className="space-y-4">
              <MQPanel title="Quality Metrics">
                <div className="space-y-4">
                  <div>
                    <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)] mb-2">
                      Quality Score
                    </div>
                    <div className="text-[var(--font-size-h3)] font-mono mb-2" style={{ color: getQualityColor(dataset.qualityScore) }}>
                      {dataset.qualityScore.toFixed(1)}%
                    </div>
                    <MQProgressBar
                      value={dataset.qualityScore}
                      max={100}
                      color={getQualityColor(dataset.qualityScore)}
                    />
                  </div>
                  <div>
                    <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)] mb-2">
                      Missing Values
                    </div>
                    <div className="text-[var(--font-size-h4)] font-mono mb-2 text-[var(--color-mq-text-primary)]">
                      {dataset.missingPct.toFixed(2)}%
                    </div>
                    <MQProgressBar
                      value={dataset.missingPct}
                      max={100}
                      color={dataset.missingPct < 5 ? 'var(--color-mq-success)' : dataset.missingPct < 15 ? 'var(--color-mq-warning)' : 'var(--color-mq-failure)'}
                    />
                  </div>
                  <div className="pt-2 border-t border-[var(--color-mq-border)]">
                    <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)] mb-2">
                      Data Completeness
                    </div>
                    <div className="text-[var(--font-size-body)] font-mono text-[var(--color-mq-text-primary)]">
                      {(100 - dataset.missingPct).toFixed(2)}%
                    </div>
                  </div>
                </div>
              </MQPanel>

              {dataset.versionHistory && dataset.versionHistory.length > 0 && (
                <MQPanel title="Version History">
                  <div className="space-y-3">
                    {dataset.versionHistory.map((version, idx) => (
                      <div key={idx} className="pb-3 border-b border-[var(--color-mq-border)] last:border-0 last:pb-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-[var(--font-size-body)] font-mono text-[var(--color-mq-accent)]">
                            v{version.version}
                          </span>
                          <span className="text-[var(--font-size-caption)] text-[var(--color-mq-text-muted)] font-mono">
                            {new Date(version.created).toLocaleDateString()}
                          </span>
                        </div>
                        <div className="text-[var(--font-size-small)] text-[var(--color-mq-text-secondary)]">
                          {version.changes}
                        </div>
                      </div>
                    ))}
                  </div>
                </MQPanel>
              )}

              <MQPanel title="Statistics">
                <div className="space-y-3">
                  <div className="flex justify-between">
                    <span className="text-[var(--font-size-small)] text-[var(--color-mq-text-secondary)]">
                      Avg Row Density
                    </span>
                    <span className="text-[var(--font-size-small)] font-mono text-[var(--color-mq-text-primary)]">
                      {(100 - dataset.missingPct).toFixed(1)}%
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[var(--font-size-small)] text-[var(--color-mq-text-secondary)]">
                      Duplicate Rows
                    </span>
                    <span className="text-[var(--font-size-small)] font-mono text-[var(--color-mq-success)]">
                      0
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[var(--font-size-small)] text-[var(--color-mq-text-secondary)]">
                      Outliers Detected
                    </span>
                    <span className="text-[var(--font-size-small)] font-mono text-[var(--color-mq-text-primary)]">
                      {Math.floor(dataset.rows * 0.001)}
                    </span>
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
