import { Trade } from '@/lib/mock-data/trades';
import { DirectionBadge, DataTable } from '@/components/trading/shared';

interface TradeHistoryTableProps {
  trades: Trade[];
}

export function TradeHistoryTable({ trades }: TradeHistoryTableProps) {
  return (
    <DataTable
      columns={[
        { header: 'INSTRUMENT', align: 'left' },
        { header: 'SIDE', align: 'left' },
        { header: 'ENTRY', align: 'right' },
        { header: 'EXIT', align: 'right' },
        { header: 'SIZE', align: 'right' },
        { header: 'REALIZED PNL', align: 'right' },
        { header: 'DURATION', align: 'right' }
      ]}
    >
      {trades.map((trade) => (
        <tr key={trade.id} className="border-b border-outline-variant hover:bg-surface-container-low transition-colors">
          <td className="px-3 py-2 font-data-tabular text-data-tabular text-on-surface">{trade.instrument}</td>
          <td className="px-3 py-2">
            <DirectionBadge direction={trade.side} />
          </td>
          <td className="px-3 py-2 text-right font-data-tabular text-data-tabular text-on-surface">${trade.entryPrice.toLocaleString()}</td>
          <td className="px-3 py-2 text-right font-data-tabular text-data-tabular text-on-surface">${trade.exitPrice.toLocaleString()}</td>
          <td className="px-3 py-2 text-right font-data-tabular text-data-tabular text-on-surface">{trade.size.toLocaleString()}</td>
          <td className={`px-3 py-2 text-right font-data-tabular text-data-tabular ${
            trade.realizedPnl >= 0 ? 'text-primary' : 'text-error'
          }`}>
            {trade.realizedPnl >= 0 ? '+' : ''}${trade.realizedPnl.toLocaleString()}
          </td>
          <td className="px-3 py-2 text-right font-data-tabular text-data-tabular text-on-surface">{trade.duration}</td>
        </tr>
      ))}
    </DataTable>
  );
}
