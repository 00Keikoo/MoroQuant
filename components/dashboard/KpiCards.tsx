'use client';

interface KpiCardProps {
  label: string;
  value: string;
  subValue: string;
  valueColor?: string;
  subValueColor?: string;
}

function KpiCard({ label, value, subValue, valueColor = 'text-on-surface', subValueColor = 'text-secondary' }: KpiCardProps) {
  return (
    <div className="bg-surface-container p-md border border-outline-variant flex flex-col justify-between">
      <p className="font-label-caps text-label-caps text-secondary">{label}</p>
      <div className="flex items-end justify-between mt-sm">
        <p className={`font-data-tabular text-display-lg ${valueColor}`}>{value}</p>
        <span className={`text-data-tabular ${subValueColor}`}>{subValue}</span>
      </div>
    </div>
  );
}

export default function KpiCards() {
  return (
    <div className="grid grid-cols-4 gap-md shrink-0">
      <KpiCard
        label="NET PNL (DAILY)"
        value="+142,408.20"
        subValue="+1.4%"
        valueColor="text-[#00FF94]"
        subValueColor="text-[#00FF94]"
      />
      <KpiCard
        label="GROSS EXPOSURE"
        value="$12,482,000"
        subValue="72% Limit"
        valueColor="text-on-surface"
        subValueColor="text-secondary"
      />
      <KpiCard
        label="ACTIVE ORDERS"
        value="1,248"
        subValue="92 Executed"
        valueColor="text-primary"
        subValueColor="text-secondary"
      />
      <KpiCard
        label="SHARPE RATIO (30D)"
        value="3.42"
        subValue="Stable"
        valueColor="text-on-surface"
        subValueColor="text-[#00FF94]"
      />
    </div>
  );
}
