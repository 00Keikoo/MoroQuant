export interface WidgetEmptyProps {
  message?: string;
  description?: string;
}

export default function WidgetEmpty({ message = 'No data available', description }: WidgetEmptyProps) {
  return (
    <div className="flex flex-col items-center gap-2 text-center py-6 px-4">
      <span className="text-xs text-secondary/50">{message}</span>
      {description && <span className="text-[10px] text-secondary/30">{description}</span>}
    </div>
  );
}
