'use client';

import { MQStatusBadge } from '@/components/mqds';
import { ResearchJourney, TimelineEvent } from '@/lib/mock-data/chronicle';
import { CheckCircle2, XCircle, AlertCircle, Pause } from 'lucide-react';

type ResearchTimelineProps = {
  journey: ResearchJourney;
  onEventSelect: (event: TimelineEvent) => void;
  selectedEventId?: string;
};

export function ResearchTimeline({ journey, onEventSelect, selectedEventId }: ResearchTimelineProps) {
  const statusIcon = {
    COMPLETED: <CheckCircle2 size={16} className="text-[var(--color-mq-success)]" />,
    FAILED: <XCircle size={16} className="text-[var(--color-mq-failure)]" />,
    IN_PROGRESS: <AlertCircle size={16} className="text-[var(--color-mq-warning)]" />,
    PAUSED: <Pause size={16} className="text-[var(--color-mq-text-secondary)]" />
  };

  const statusMap: Record<string, 'success' | 'failure' | 'warning' | 'running' | 'pending'> = {
    SUCCESS: 'success',
    FAILED: 'failure',
    WARNING: 'warning',
    INFO: 'pending'
  };

  const journeyStatusMap: Record<string, 'success' | 'failure' | 'warning' | 'running' | 'pending'> = {
    COMPLETED: 'success',
    FAILED: 'failure',
    IN_PROGRESS: 'running',
    PAUSED: 'warning'
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between p-3 bg-[var(--color-mq-bg-secondary)] border border-[var(--color-mq-border)] rounded-[var(--radius-minimal)]">
        <div className="flex items-center gap-3">
          {statusIcon[journey.status]}
          <div>
            <div className="text-[var(--font-size-body)] text-[var(--color-mq-text-primary)] font-mono font-medium">
              {journey.title}
            </div>
            <div className="text-[var(--font-size-small)] text-[var(--color-mq-text-secondary)] font-mono">
              {journey.researcher} • {new Date(journey.startDate).toLocaleDateString()} - {new Date(journey.endDate).toLocaleDateString()}
            </div>
          </div>
        </div>
        <MQStatusBadge status={journeyStatusMap[journey.status]} label={journey.status} />
      </div>

      <div className="relative pl-6">
        <div className="absolute left-2 top-0 bottom-0 w-[2px] bg-[var(--color-mq-border)]" />

        <div className="space-y-3">
          {journey.events.map((event, index) => {
            const isSelected = selectedEventId === event.id;
            const isLast = index === journey.events.length - 1;

            return (
              <div key={event.id} className="relative">
                <div
                  className={`absolute left-[-20px] top-3 w-3 h-3 rounded-full border-2 ${
                    isSelected
                      ? 'bg-[var(--color-mq-accent)] border-[var(--color-mq-accent)]'
                      : 'bg-[var(--color-mq-bg-primary)] border-[var(--color-mq-border)]'
                  }`}
                />

                <button
                  onClick={() => onEventSelect(event)}
                  className={`w-full text-left p-3 rounded-[var(--radius-minimal)] border transition-all ${
                    isSelected
                      ? 'bg-[var(--color-mq-bg-tertiary)] border-[var(--color-mq-accent)]'
                      : 'bg-[var(--color-mq-bg-secondary)] border-[var(--color-mq-border)] hover:border-[var(--color-mq-text-secondary)]'
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-[var(--font-size-small)] text-[var(--color-mq-text-secondary)] font-mono">
                          {new Date(event.timestamp).toLocaleTimeString()}
                        </span>
                        <span className="px-2 py-0.5 bg-[var(--color-mq-bg-primary)] border border-[var(--color-mq-border)] rounded text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)] font-mono">
                          {event.eventType}
                        </span>
                      </div>
                      <div className="text-[var(--font-size-body)] text-[var(--color-mq-text-primary)] font-mono font-medium mb-1">
                        {event.entity}
                      </div>
                      <div className="text-[var(--font-size-small)] text-[var(--color-mq-text-secondary)] font-mono">
                        {event.action}
                      </div>
                    </div>
                    <MQStatusBadge status={statusMap[event.status]} label={event.status} />
                  </div>
                </button>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
