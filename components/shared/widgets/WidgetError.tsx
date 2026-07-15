import { normalizeError } from '@/lib/utils/errorNormalization';

export interface WidgetErrorProps {
  error: unknown;
  onRetry?: () => void;
  title?: string;
}

export default function WidgetError({ error, onRetry, title }: WidgetErrorProps) {
  const normalized = normalizeError(error);

  return (
    <div className="flex flex-col items-center gap-3 py-6">
      <div className="text-center">
        <p className="text-sm font-semibold text-error mb-1">{title || normalized.title}</p>
        <p className="text-xs text-secondary">{normalized.message}</p>
      </div>
      {normalized.retryable && onRetry && (
        <button
          onClick={onRetry}
          className="px-3 py-1.5 text-xs bg-surface-container border border-outline-variant hover:border-primary transition-colors"
        >
          Retry
        </button>
      )}
    </div>
  );
}
