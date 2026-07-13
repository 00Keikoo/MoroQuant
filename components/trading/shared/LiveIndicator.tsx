interface LiveIndicatorProps {
  label?: string;
  className?: string;
}

export function LiveIndicator({ label = 'Live', className = '' }: LiveIndicatorProps) {
  return (
    <div className={`flex items-center gap-2 px-2 py-1 bg-surface-container-lowest border border-outline-variant ${className}`}>
      <div className="w-2 h-2 rounded-full bg-primary-container animate-pulse"></div>
      <span className="font-mono-data text-mono-data text-primary uppercase">{label}</span>
    </div>
  );
}
