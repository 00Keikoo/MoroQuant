import { ReactNode } from 'react';
import WidgetError from './WidgetError';
import WidgetEmpty from './WidgetEmpty';

export interface WidgetContainerProps {
  title: string;
  children: ReactNode;
  actions?: ReactNode;
  className?: string;
  loading?: boolean;
  loadingComponent?: ReactNode;
  error?: unknown;
  onRetry?: () => void;
  empty?: boolean;
  emptyMessage?: string;
  emptyDescription?: string;
}

export default function WidgetContainer({
  title,
  children,
  actions,
  className = '',
  loading = false,
  loadingComponent,
  error,
  onRetry,
  empty = false,
  emptyMessage,
  emptyDescription,
}: WidgetContainerProps) {
  return (
    <section className={`glass-card overflow-hidden flex flex-col ${className}`}>
      <div className="flex items-center justify-between px-4 py-3 border-b border-mq-panel-border bg-black/40">
        <h2 className="text-sm font-bold tracking-wider text-white uppercase">{title}</h2>
        {actions && <div className="flex items-center gap-2">{actions}</div>}
      </div>
      <div className="p-4 flex-1">
        {loading ? (
          loadingComponent || children
        ) : error ? (
          <WidgetError error={error} onRetry={onRetry} />
        ) : empty ? (
          <WidgetEmpty message={emptyMessage} description={emptyDescription} />
        ) : (
          children
        )}
      </div>
    </section>
  );
}
