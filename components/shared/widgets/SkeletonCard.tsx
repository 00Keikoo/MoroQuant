export interface SkeletonCardProps {
  label?: string;
  height?: string;
}

export default function SkeletonCard({ label, height = 'h-24' }: SkeletonCardProps) {
  return (
    <div className={`bg-surface-container p-md border border-outline-variant flex flex-col justify-between ${height}`}>
      {label && <p className="font-label-caps text-label-caps text-secondary">{label}</p>}
      <div className="flex items-end justify-between mt-sm">
        <div className="h-8 w-32 bg-outline-variant/50 animate-pulse rounded"></div>
        <div className="h-4 w-16 bg-outline-variant/50 animate-pulse rounded"></div>
      </div>
    </div>
  );
}
