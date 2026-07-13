import { StressTest } from '@/lib/mock-data/risk';
import { DataTable } from '@/components/trading/shared';

interface StressTestTableProps {
  tests: StressTest[];
}

export function StressTestTable({ tests }: StressTestTableProps) {
  return (
    <DataTable
      title="Stress Test Scenarios"
      columns={[
        { header: 'SCENARIO', align: 'left' },
        { header: 'PORTFOLIO IMPACT', align: 'right' },
        { header: 'IMPACT %', align: 'right' },
        { header: 'PROBABILITY', align: 'right' }
      ]}
    >
      {tests.map((test, idx) => (
        <tr key={idx} className="border-b border-outline-variant hover:bg-surface-container-low transition-colors">
          <td className="px-3 py-2 font-mono-data text-mono-data text-on-surface">{test.scenario}</td>
          <td className="px-3 py-2 text-right font-mono-data text-mono-data text-error">${test.portfolioImpact.toLocaleString()}</td>
          <td className="px-3 py-2 text-right font-mono-data text-mono-data text-error">{test.impactPercent.toFixed(1)}%</td>
          <td className="px-3 py-2 text-right font-mono-data text-mono-data text-on-surface">{(test.probability * 100).toFixed(0)}%</td>
        </tr>
      ))}
    </DataTable>
  );
}
