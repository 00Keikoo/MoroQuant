import { Order } from '@/lib/mock-data/execution';
import { DirectionBadge, StatusBadge, DataTable } from '@/components/trading/shared';

interface OrdersTableProps {
  orders: Order[];
}

export function OrdersTable({ orders }: OrdersTableProps) {
  return (
    <DataTable
      title="Active Orders"
      columns={[
        { header: 'ORDER ID', align: 'left' },
        { header: 'INSTRUMENT', align: 'left' },
        { header: 'SIDE', align: 'left' },
        { header: 'TYPE', align: 'left' },
        { header: 'PRICE', align: 'right' },
        { header: 'SIZE', align: 'right' },
        { header: 'FILLED', align: 'right' },
        { header: 'STATUS', align: 'left' }
      ]}
    >
      {orders.map((order) => (
        <tr key={order.id} className="border-b border-outline-variant hover:bg-surface-container-low transition-colors">
          <td className="px-3 py-2 font-mono-data text-mono-data text-on-surface-variant">{order.id}</td>
          <td className="px-3 py-2 font-mono-data text-mono-data text-on-surface">{order.instrument}</td>
          <td className="px-3 py-2">
            <DirectionBadge direction={order.side} />
          </td>
          <td className="px-3 py-2 font-mono-data text-mono-data text-on-surface">{order.type}</td>
          <td className="px-3 py-2 text-right font-mono-data text-mono-data text-on-surface">${order.price.toLocaleString()}</td>
          <td className="px-3 py-2 text-right font-mono-data text-mono-data text-on-surface">{order.size.toLocaleString()}</td>
          <td className="px-3 py-2 text-right font-mono-data text-mono-data text-primary">{order.filled.toLocaleString()}</td>
          <td className="px-3 py-2">
            <StatusBadge
              status={order.status}
              variant={order.status === 'FILLED' ? 'success' : order.status === 'PARTIAL' ? 'warning' : 'neutral'}
            />
          </td>
        </tr>
      ))}
    </DataTable>
  );
}
