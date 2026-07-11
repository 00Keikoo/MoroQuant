import React from 'react';

interface MQTimelineEvent {
  id: string;
  timestamp: string;
  title: string;
  description?: string;
  icon?: React.ReactNode;
  status?: 'success' | 'failure' | 'warning' | 'running';
}

interface MQTimelineProps {
  events: MQTimelineEvent[];
  className?: string;
}

export function MQTimeline({ events, className = '' }: MQTimelineProps) {
  const statusColors = {
    success: 'bg-[var(--color-mq-success)]',
    failure: 'bg-[var(--color-mq-failure)]',
    warning: 'bg-[var(--color-mq-warning)]',
    running: 'bg-[var(--color-mq-running)]'
  };

  return (
    <div className={`space-y-4 ${className}`}>
      {events.map((event, index) => (
        <div key={event.id} className="flex gap-3">
          <div className="flex flex-col items-center">
            <div
              className={`w-2 h-2 rounded-full ${
                event.status ? statusColors[event.status] : 'bg-[var(--color-mq-border)]'
              }`}
            />
            {index < events.length - 1 && (
              <div className="w-px flex-1 bg-[var(--color-mq-border)] mt-1" />
            )}
          </div>
          <div className="flex-1 pb-4">
            <div className="flex items-center gap-2 mb-1">
              {event.icon && (
                <div className="text-[var(--color-mq-text-muted)]">
                  {event.icon}
                </div>
              )}
              <span className="text-[var(--font-size-caption)] text-[var(--color-mq-text-muted)] font-mono">
                {event.timestamp}
              </span>
            </div>
            <div className="text-[var(--font-size-body)] text-[var(--color-mq-text-primary)] font-medium mb-1">
              {event.title}
            </div>
            {event.description && (
              <div className="text-[var(--font-size-small)] text-[var(--color-mq-text-secondary)]">
                {event.description}
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
