'use client';

import { MQPanel, MQStatusBadge } from '@/components/mqds';
import { TimelineEvent } from '@/lib/mock-data/chronicle';
import { Clock, User, Database, Tag, FileText } from 'lucide-react';

type TimelineInspectorProps = {
  event: TimelineEvent | null;
};

export function TimelineInspector({ event }: TimelineInspectorProps) {
  if (!event) {
    return (
      <MQPanel title="Event Inspector">
        <div className="h-[500px] flex items-center justify-center">
          <div className="text-center">
            <FileText size={48} className="mx-auto mb-3 text-[var(--color-mq-text-muted)]" />
            <div className="text-[var(--font-size-body)] text-[var(--color-mq-text-secondary)] font-mono">
              Select an event to inspect
            </div>
          </div>
        </div>
      </MQPanel>
    );
  }

  const statusMap: Record<string, 'success' | 'failure' | 'warning' | 'running' | 'pending'> = {
    SUCCESS: 'success',
    FAILED: 'failure',
    WARNING: 'warning',
    INFO: 'pending'
  };

  return (
    <MQPanel title="Event Inspector">
      <div className="space-y-4">
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1">
            <div className="text-[var(--font-size-h4)] text-[var(--color-mq-text-primary)] font-mono font-medium mb-2">
              {event.entity}
            </div>
            <div className="text-[var(--font-size-body)] text-[var(--color-mq-text-secondary)] font-mono">
              {event.action}
            </div>
          </div>
          <MQStatusBadge status={statusMap[event.status]} label={event.status} />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="p-3 bg-[var(--color-mq-bg-secondary)] border border-[var(--color-mq-border)] rounded-[var(--radius-minimal)]">
            <div className="flex items-center gap-2 mb-1">
              <Clock size={14} className="text-[var(--color-mq-text-muted)]" />
              <span className="text-[var(--font-size-small)] text-[var(--color-mq-text-muted)] font-mono">
                Timestamp
              </span>
            </div>
            <div className="text-[var(--font-size-body)] text-[var(--color-mq-text-primary)] font-mono">
              {new Date(event.timestamp).toLocaleString()}
            </div>
          </div>

          <div className="p-3 bg-[var(--color-mq-bg-secondary)] border border-[var(--color-mq-border)] rounded-[var(--radius-minimal)]">
            <div className="flex items-center gap-2 mb-1">
              <User size={14} className="text-[var(--color-mq-text-muted)]" />
              <span className="text-[var(--font-size-small)] text-[var(--color-mq-text-muted)] font-mono">
                User
              </span>
            </div>
            <div className="text-[var(--font-size-body)] text-[var(--color-mq-text-primary)] font-mono">
              {event.user}
            </div>
          </div>

          <div className="p-3 bg-[var(--color-mq-bg-secondary)] border border-[var(--color-mq-border)] rounded-[var(--radius-minimal)]">
            <div className="flex items-center gap-2 mb-1">
              <Tag size={14} className="text-[var(--color-mq-text-muted)]" />
              <span className="text-[var(--font-size-small)] text-[var(--color-mq-text-muted)] font-mono">
                Event Type
              </span>
            </div>
            <div className="text-[var(--font-size-body)] text-[var(--color-mq-text-primary)] font-mono">
              {event.eventType}
            </div>
          </div>

          <div className="p-3 bg-[var(--color-mq-bg-secondary)] border border-[var(--color-mq-border)] rounded-[var(--radius-minimal)]">
            <div className="flex items-center gap-2 mb-1">
              <Database size={14} className="text-[var(--color-mq-text-muted)]" />
              <span className="text-[var(--font-size-small)] text-[var(--color-mq-text-muted)] font-mono">
                Entity ID
              </span>
            </div>
            <div className="text-[var(--font-size-body)] text-[var(--color-mq-text-primary)] font-mono">
              {event.entityId}
            </div>
          </div>
        </div>

        <div className="p-3 bg-[var(--color-mq-bg-secondary)] border border-[var(--color-mq-border)] rounded-[var(--radius-minimal)]">
          <div className="text-[var(--font-size-small)] text-[var(--color-mq-text-muted)] font-mono mb-2">
            Metadata
          </div>
          <div className="text-[var(--font-size-body)] text-[var(--color-mq-text-primary)] font-mono">
            {event.metadata}
          </div>
        </div>

        {event.details?.metrics && Object.keys(event.details.metrics).length > 0 && (
          <div className="p-3 bg-[var(--color-mq-bg-secondary)] border border-[var(--color-mq-border)] rounded-[var(--radius-minimal)]">
            <div className="text-[var(--font-size-small)] text-[var(--color-mq-text-muted)] font-mono mb-2">
              Metrics
            </div>
            <div className="space-y-1">
              {Object.entries(event.details.metrics).map(([key, value]) => (
                <div key={key} className="flex items-center justify-between">
                  <span className="text-[var(--font-size-small)] text-[var(--color-mq-text-secondary)] font-mono">
                    {key}
                  </span>
                  <span className="text-[var(--font-size-small)] text-[var(--color-mq-text-primary)] font-mono font-medium">
                    {value}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {event.details?.logs && event.details.logs.length > 0 && (
          <div className="p-3 bg-[var(--color-mq-bg-secondary)] border border-[var(--color-mq-border)] rounded-[var(--radius-minimal)]">
            <div className="text-[var(--font-size-small)] text-[var(--color-mq-text-muted)] font-mono mb-2">
              Logs
            </div>
            <div className="space-y-1">
              {event.details.logs.map((log, index) => (
                <div key={index} className="text-[var(--font-size-small)] text-[var(--color-mq-text-primary)] font-mono">
                  {log}
                </div>
              ))}
            </div>
          </div>
        )}

        {event.details?.artifacts && event.details.artifacts.length > 0 && (
          <div className="p-3 bg-[var(--color-mq-bg-secondary)] border border-[var(--color-mq-border)] rounded-[var(--radius-minimal)]">
            <div className="text-[var(--font-size-small)] text-[var(--color-mq-text-muted)] font-mono mb-2">
              Artifacts
            </div>
            <div className="space-y-1">
              {event.details.artifacts.map((artifact, index) => (
                <div key={index} className="text-[var(--font-size-small)] text-[var(--color-mq-accent)] font-mono hover:underline cursor-pointer">
                  {artifact}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </MQPanel>
  );
}
