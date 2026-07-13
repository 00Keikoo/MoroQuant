import { PortfolioPosition } from '@/lib/mock-data/portfolio';
import { DirectionBadge, DataTable } from '@/components/trading/shared';

interface PortfolioPositionsTableProps {
  positions: PortfolioPosition[];
}

export function PortfolioPositionsTable({ positions }: PortfolioPositionsTableProps) {
  return (
    <DataTable
      title="Portfolio Positions"
      columns={[
        { header: 'INSTRUMENT', align: 'left' },
        { header: 'SIDE', align: 'left' },
        { header: 'SIZE', align: 'right' },
        { header: 'ENTRY', align: 'right' },
        { header: 'MARK', align: 'right' },
        { header: 'UNREALIZED PNL', align: 'right' },
        { header: 'LEVERAGE', align: 'right' },
        { header: 'WEIGHT', align: 'right' }
      ]}
    >
      {positions.map((position, idx) => (
        <tr key={idx} className="border-b border-outline-variant hover:bg-surface-container-low transition-colors">
          <td className="px-3 py-2 font-mono-data text-mono-data text-on-surface">{position.instrument}</td>
          <td className="px-3 py-2">
            <DirectionBadge direction={position.side} />
          </td>
          <td className="px-3 py-2 text-right font-mono-data text-mono-data text-on-surface">{position.size.toLocaleString()}</td>
          <td className="px-3 py-2 text-right font-mono-data text-mono-data text-on-surface">${position.entryPrice.toLocaleString()}</td>
          <td className="px-3 py-2 text-right font-mono-data text-mono-data text-on-surface">${position.markPrice.toLocaleString()}</td>
          <td className={`px-3 py-2 text-right font-mono-data text-mono-data ${
            position.unrealizedPnl >= 0 ? 'text-primary' : 'text-error'
          }`}>
            {position.unrealizedPnl >= 0 ? '+' : ''}${position.unrealizedPnl.toLocaleString()}
          </td>
          <td className="px-3 py-2 text-right font-mono-data text-mono-data text-on-surface">{position.leverage}</td>
          <td className="px-3 py-2 text-right font-mono-data text-mono-data text-on-surface">{(position.weight * 100).toFixed(0)}%</td>
        </tr>
      ))}
    </DataTable>
  );
}
