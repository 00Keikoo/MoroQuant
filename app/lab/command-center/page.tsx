'use client';

import { MQPanel, MQMetricCard, MQTable, MQTimeline, MQStatusBadge, MQSparkline, MQProgressBar } from '@/components/mqds';
import { mockExperiments } from '@/lib/mock-data/experiments';
import { Activity, Zap, TrendingUp, AlertTriangle, Database, GitBranch } from 'lucide-react';

export default function CommandCenterPage() {
  const activeExperiments = mockExperiments.filter(e => ['TRAINING', 'VALIDATING', 'CALIBRATING'].includes(e.status));
  const promotionQueue = mockExperiments.filter(e => e.status === 'PROMOTION');
  const productionModels = mockExperiments.filter(e => e.status === 'PRODUCTION');
  const failedExperiments = mockExperiments.filter(e => e.status === 'FAILED');
  const paperTrading = mockExperiments.filter(e => e.status === 'PAPER');

  const recentActivity = mockExperiments
    .slice(0, 10)
    .sort((a, b) => new Date(b.created).getTime() - new Date(a.created).getTime());

  const mockSparklineData = [65, 68, 70, 72, 69, 73, 75, 78, 76, 80];
  const successRate = 0.82;

  return (
    <div className="p-4 space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
        <MQMetricCard
          label="Active Experiments"
          value={activeExperiments.length}
          delta={{ value: 12, direction: 'up' }}
          sparkline={<MQSparkline data={mockSparklineData} />}
        />
        <MQMetricCard
          label="Production Models"
          value={productionModels.length}
          sparkline={<MQSparkline data={[70, 72, 71, 73, 75, 74, 76, 78, 77, 79]} />}
        />
        <MQMetricCard
          label="Promotion Queue"
          value={promotionQueue.length}
          delta={{ value: 8, direction: 'up' }}
        />
        <MQMetricCard
          label="Paper Trading"
          value={paperTrading.length}
          sparkline={<MQSparkline data={[12, 14, 13, 15, 16, 15, 17, 18, 16, 19]} />}
        />
        <MQMetricCard
          label="Success Rate"
          value={`${(successRate * 100).toFixed(0)}%`}
          delta={{ value: 3, direction: 'up' }}
        />
        <MQMetricCard
          label="Failed (24h)"
          value={failedExperiments.length}
          delta={{ value: -15, direction: 'down' }}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <MQPanel title="Active Training Runs">
          <div className="space-y-3">
            {activeExperiments.slice(0, 5).map(exp => (
              <div key={exp.runId} className="flex items-center justify-between p-2 bg-[var(--color-mq-bg-primary)] rounded-[var(--radius-minimal)]">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-[var(--font-size-small)] font-mono text-[var(--color-mq-text-primary)]">
                      {exp.runId}
                    </span>
                    <MQStatusBadge
                      status={exp.status === 'TRAINING' ? 'running' : 'warning'}
                      label={exp.status}
                    />
                  </div>
                  <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)]">
                    {exp.algorithm} · {exp.dataset}
                  </div>
                  <div className="mt-2">
                    <MQProgressBar
                      value={exp.status === 'TRAINING' ? 65 : 100}
                      color={exp.status === 'TRAINING' ? 'var(--color-mq-running)' : 'var(--color-mq-warning)'}
                    />
                  </div>
                </div>
                <div className="text-right ml-4">
                  <div className="text-[var(--font-size-small)] font-mono text-[var(--color-mq-text-primary)]">
                    {exp.duration}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </MQPanel>

        <MQPanel title="Promotion Queue">
          <div className="space-y-3">
            {promotionQueue.map(exp => (
              <div key={exp.runId} className="flex items-center justify-between p-2 bg-[var(--color-mq-bg-primary)] rounded-[var(--radius-minimal)]">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-[var(--font-size-small)] font-mono text-[var(--color-mq-text-primary)]">
                      {exp.runId}
                    </span>
                    <MQStatusBadge status="success" label="READY" />
                  </div>
                  <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)]">
                    {exp.algorithm} · Score: {exp.score?.toFixed(2)}
                  </div>
                </div>
                <div className="text-right ml-4">
                  <div className="text-[var(--font-size-small)] font-mono text-[var(--color-mq-success)]">
                    +{((exp.score || 0) * 10).toFixed(1)}%
                  </div>
                </div>
              </div>
            ))}
          </div>
        </MQPanel>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2">
          <MQPanel title="Recent Research Activity">
            <MQTable
              columns={[
                {
                  key: 'runId',
                  header: 'Run ID',
                  render: (row) => (
                    <span className="text-[var(--color-mq-text-primary)]">{row.runId}</span>
                  )
                },
                {
                  key: 'status',
                  header: 'Status',
                  render: (row) => {
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
                    return <MQStatusBadge status={statusMap[row.status]} label={row.status} />;
                  }
                },
                {
                  key: 'algorithm',
                  header: 'Algorithm',
                  render: (row) => row.algorithm
                },
                {
                  key: 'score',
                  header: 'Score',
                  align: 'right',
                  render: (row) => row.score?.toFixed(2) || '-'
                },
                {
                  key: 'duration',
                  header: 'Duration',
                  align: 'right',
                  render: (row) => row.duration
                }
              ]}
              data={recentActivity}
              keyExtractor={(row) => row.runId}
              compact
            />
          </MQPanel>
        </div>

        <MQPanel title="System Health">
          <div className="space-y-4">
            <div>
              <div className="flex justify-between items-center mb-2">
                <span className="text-[var(--font-size-small)] text-[var(--color-mq-text-secondary)]">
                  GPU Utilization
                </span>
                <span className="text-[var(--font-size-small)] font-mono text-[var(--color-mq-text-primary)]">
                  87%
                </span>
              </div>
              <MQProgressBar value={87} color="var(--color-mq-success)" />
            </div>

            <div>
              <div className="flex justify-between items-center mb-2">
                <span className="text-[var(--font-size-small)] text-[var(--color-mq-text-secondary)]">
                  Dataset Freshness
                </span>
                <span className="text-[var(--font-size-small)] font-mono text-[var(--color-mq-text-primary)]">
                  92%
                </span>
              </div>
              <MQProgressBar value={92} color="var(--color-mq-success)" />
            </div>

            <div>
              <div className="flex justify-between items-center mb-2">
                <span className="text-[var(--font-size-small)] text-[var(--color-mq-text-secondary)]">
                  Feature Drift
                </span>
                <span className="text-[var(--font-size-small)] font-mono text-[var(--color-mq-warning)]">
                  12%
                </span>
              </div>
              <MQProgressBar value={12} color="var(--color-mq-warning)" />
            </div>

            <div className="pt-4 border-t border-[var(--color-mq-border)]">
              <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)] mb-3">
                Recent Events
              </div>
              <div className="space-y-2">
                <div className="flex items-start gap-2">
                  <AlertTriangle size={14} className="text-[var(--color-mq-warning)] mt-0.5" />
                  <div className="flex-1">
                    <div className="text-[var(--font-size-small)] text-[var(--color-mq-text-primary)]">
                      Feature drift detected
                    </div>
                    <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-muted)]">
                      2h ago
                    </div>
                  </div>
                </div>
                <div className="flex items-start gap-2">
                  <GitBranch size={14} className="text-[var(--color-mq-success)] mt-0.5" />
                  <div className="flex-1">
                    <div className="text-[var(--font-size-small)] text-[var(--color-mq-text-primary)]">
                      Model promoted to production
                    </div>
                    <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-muted)]">
                      5h ago
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </MQPanel>
      </div>
    </div>
  );
}
