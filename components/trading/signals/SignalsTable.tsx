import { Signal } from '@/lib/mock-data/signals';
import { DirectionBadge, DataTable } from '@/components/trading/shared';

interface SignalsTableProps {
  signals: Signal[];
}

export function SignalsTable({ signals }: SignalsTableProps) {
  return (
    <DataTable
      columns={[
        { header: 'SYMBOL', align: 'left' },
        { header: 'DIRECTION', align: 'left' },
        { header: 'CONFIDENCE', align: 'right' },
        { header: 'ENTRY', align: 'right' },
        { header: 'TARGET', align: 'right' },
        { header: 'STOP LOSS', align: 'right' },
        { header: 'MODEL', align: 'left' },
        { header: 'TIMESTAMP', align: 'left' }
      ]}
    >
      {signals.map((signal) => (
        <tr key={signal.id} className="border-b border-outline-variant hover:bg-surface-container-low transition-colors">
          <td className="px-3 py-2 font-data-tabular text-data-tabular text-on-surface">{signal.symbol}</td>
          <td className="px-3 py-2">
            <DirectionBadge direction={signal.direction} />
          </td>
          <td className="px-3 py-2 text-right font-data-tabular text-data-tabular text-on-surface">
            {(signal.confidence * 100).toFixed(0)}%
          </td>
          <td className="px-3 py-2 text-right font-data-tabular text-data-tabular text-on-surface">
            ${signal.entryPrice.toLocaleString()}
          </td>
          <td className="px-3 py-2 text-right font-data-tabular text-data-tabular text-primary">
            ${signal.targetPrice.toLocaleString()}
          </td>
          <td className="px-3 py-2 text-right font-data-tabular text-data-tabular text-error">
            ${signal.stopLoss.toLocaleString()}
          </td>
          <td className="px-3 py-2 font-data-tabular text-data-tabular text-on-surface-variant text-[10px]">
            {signal.model}
          </td>
          <td className="px-3 py-2 font-data-tabular text-data-tabular text-on-surface-variant text-[10px]">
            {new Date(signal.timestamp).toLocaleTimeString()}
          </td>
        </tr>
      ))}
    </DataTable>
  );
}
