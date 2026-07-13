import { Position } from '@/lib/mock-data/trades';
import { DirectionBadge, DataTable } from '@/components/trading/shared';

interface PositionsTableProps {
  positions: Position[];
}

export function PositionsTable({ positions }: PositionsTableProps) {
  return (
    <DataTable
      columns={[
        { header: 'INSTRUMENT', align: 'left' },
        { header: 'SIDE', align: 'left' },
        { header: 'SIZE', align: 'right' },
        { header: 'ENTRY', align: 'right' },
        { header: 'MARK', align: 'right' },
        { header: 'UNREALIZED PNL', align: 'right' },
        { header: 'PNL %', align: 'right' }
      ]}
    >
      {positions.map((position) => (
        <tr key={position.id} className="border-b border-outline-variant hover:bg-surface-container-low transition-colors">
          <td className="px-3 py-2 font-data-tabular text-data-tabular text-on-surface">{position.instrument}</td>
          <td className="px-3 py-2">
            <DirectionBadge direction={position.side} />
          </td>
          <td className="px-3 py-2 text-right font-data-tabular text-data-tabular text-on-surface">{position.size.toLocaleString()}</td>
          <td className="px-3 py-2 text-right font-data-tabular text-data-tabular text-on-surface">${position.entryPrice.toLocaleString()}</td>
          <td className="px-3 py-2 text-right font-data-tabular text-data-tabular text-on-surface">${position.markPrice.toLocaleString()}</td>
          <td className={`px-3 py-2 text-right font-data-tabular text-data-tabular ${
            position.unrealizedPnl >= 0 ? 'text-primary' : 'text-error'
          }`}>
            {position.unrealizedPnl >= 0 ? '+' : ''}${position.unrealizedPnl.toLocaleString()}
          </td>
          <td className={`px-3 py-2 text-right font-data-tabular text-data-tabular ${
            position.pnlPercent >= 0 ? 'text-primary' : 'text-error'
          }`}>
            {position.pnlPercent >= 0 ? '+' : ''}{position.pnlPercent}%
          </td>
        </tr>
      ))}
    </DataTable>
  );
}
