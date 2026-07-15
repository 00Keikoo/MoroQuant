export interface SkeletonChartProps {
  height?: string;
  message?: string;
}

export default function SkeletonChart({ height = 'h-64', message = 'Loading chart data...' }: SkeletonChartProps) {
  return (
    <div className={`${height} relative bg-surface-container-lowest`}>
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
        <div className="w-full h-px bg-outline-variant/30 top-1/4 absolute"></div>
        <div className="w-full h-px bg-outline-variant/30 top-2/4 absolute"></div>
        <div className="w-full h-px bg-outline-variant/30 top-3/4 absolute"></div>
      </div>
      <div className="absolute inset-0 flex items-center justify-center">
        <div className="flex flex-col items-center gap-2">
          <div className="w-8 h-8 border-2 border-outline-variant border-t-primary rounded-full animate-spin"></div>
          <span className="text-xs text-secondary/50">{message}</span>
        </div>
      </div>
    </div>
  );
}
