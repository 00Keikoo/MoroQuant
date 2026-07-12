'use client';

import React from 'react';
import { MQPanel, MQStatusBadge, MQProgressBar } from '@/components/mqds';
import { TrendingUp, Target, BarChart3, Activity } from 'lucide-react';

type CalibrationRun = {
  id: string;
  name: string;
  model: string;
  method: string;
  dataset: string;
  brierScore: number;
  ece: number;
  mce: number;
  logLoss: number;
  bins: number;
  status: 'CALIBRATED' | 'NEEDS_RECALIBRATION' | 'CALIBRATING' | 'FAILED' | 'PENDING';
  created: string;
};

interface CalibrationInspectorProps {
  calibration: CalibrationRun;
  onClose: () => void;
}

export function CalibrationInspector({ calibration, onClose }: CalibrationInspectorProps) {
  const statusMap: Record<string, 'success' | 'failure' | 'warning' | 'running' | 'pending'> = {
    CALIBRATED: 'success',
    NEEDS_RECALIBRATION: 'warning',
    CALIBRATING: 'running',
    FAILED: 'failure',
    PENDING: 'pending'
  };

  const getECEColor = (score: number) => {
    if (score <= 0.025) return 'var(--color-mq-success)';
    if (score <= 0.04) return 'var(--color-mq-warning)';
    return 'var(--color-mq-failure)';
  };

  const getBrierColor = (score: number) => {
    if (score <= 0.15) return 'var(--color-mq-success)';
    if (score <= 0.20) return 'var(--color-mq-warning)';
    return 'var(--color-mq-failure)';
  };

  const getLogLossColor = (score: number) => {
    if (score <= 0.35) return 'var(--color-mq-success)';
    if (score <= 0.50) return 'var(--color-mq-warning)';
    return 'var(--color-mq-failure)';
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-[var(--color-mq-bg-secondary)] border border-[var(--color-mq-border)] rounded-[var(--radius-minimal)] w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
        <div className="flex items-center justify-between p-4 border-b border-[var(--color-mq-border)]">
          <div className="flex items-center gap-3">
            <h2 className="text-[var(--font-size-h4)] font-bold text-[var(--color-mq-text-primary)] font-mono">
              {calibration.name}
            </h2>
            <MQStatusBadge status={statusMap[calibration.status]} label={calibration.status} />
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
              <MQPanel title="Calibration Metadata">
                <div className="space-y-3">
                  <div>
                    <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)] mb-1">
                      Calibration ID
                    </div>
                    <div className="text-[var(--font-size-body)] font-mono text-[var(--color-mq-text-primary)]">
                      {calibration.id}
                    </div>
                  </div>
                  <div>
                    <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)] mb-1">
                      Model
                    </div>
                    <div className="text-[var(--font-size-body)] font-mono text-[var(--color-mq-text-primary)]">
                      {calibration.model}
                    </div>
                  </div>
                  <div>
                    <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)] mb-1">
                      Method
                    </div>
                    <div className="text-[var(--font-size-body)] font-mono text-[var(--color-mq-text-primary)]">
                      {calibration.method}
                    </div>
                  </div>
                  <div>
                    <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)] mb-1">
                      Dataset
                    </div>
                    <div className="text-[var(--font-size-body)] font-mono text-[var(--color-mq-text-primary)]">
                      {calibration.dataset}
                    </div>
                  </div>
                  <div>
                    <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)] mb-1">
                      Bins
                    </div>
                    <div className="text-[var(--font-size-body)] font-mono text-[var(--color-mq-text-primary)]">
                      {calibration.bins}
                    </div>
                  </div>
                  <div>
                    <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)] mb-1">
                      Created
                    </div>
                    <div className="text-[var(--font-size-body)] font-mono text-[var(--color-mq-text-primary)]">
                      {new Date(calibration.created).toLocaleString()}
                    </div>
                  </div>
                </div>
              </MQPanel>
            </div>

            <div className="space-y-4">
              <MQPanel title="Calibration Metrics">
                <div className="space-y-4">
                  <div>
                    <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)] mb-2">
                      Expected Calibration Error (ECE)
                    </div>
                    <div className="text-[var(--font-size-h3)] font-mono mb-2" style={{ color: getECEColor(calibration.ece) }}>
                      {(calibration.ece * 100).toFixed(2)}%
                    </div>
                    <MQProgressBar
                      value={calibration.ece * 100}
                      max={10}
                      color={getECEColor(calibration.ece)}
                    />
                  </div>
                  <div>
                    <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)] mb-2">
                      Brier Score
                    </div>
                    <div className="text-[var(--font-size-h4)] font-mono mb-2" style={{ color: getBrierColor(calibration.brierScore) }}>
                      {calibration.brierScore.toFixed(3)}
                    </div>
                    <MQProgressBar
                      value={calibration.brierScore * 100}
                      max={50}
                      color={getBrierColor(calibration.brierScore)}
                    />
                  </div>
                  <div className="pt-2 border-t border-[var(--color-mq-border)]">
                    <div className="space-y-3">
                      <div className="flex justify-between">
                        <span className="text-[var(--font-size-small)] text-[var(--color-mq-text-secondary)]">
                          Maximum Calibration Error (MCE)
                        </span>
                        <span className="text-[var(--font-size-small)] font-mono text-[var(--color-mq-text-primary)]">
                          {(calibration.mce * 100).toFixed(2)}%
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-[var(--font-size-small)] text-[var(--color-mq-text-secondary)]">
                          Log Loss
                        </span>
                        <span className="text-[var(--font-size-small)] font-mono" style={{ color: getLogLossColor(calibration.logLoss) }}>
                          {calibration.logLoss.toFixed(3)}
                        </span>
                      </div>
                    </div>
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
