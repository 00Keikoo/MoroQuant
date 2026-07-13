'use client';

import { useIsPrivacyMode } from '@/lib/stores/privacyStore';

interface InventoryPosition {
  instrument: string;
  side: 'LONG' | 'SHORT';
  size: number;
  entryPrice: number;
  markPrice: number;
  unrealizedPnl: number;
}

interface ActiveInventoryTableProps {
  positions: InventoryPosition[];
}

export default function ActiveInventoryTable({ positions }: ActiveInventoryTableProps) {
  const isPrivacyMode = useIsPrivacyMode();

  const formatValue = (value: number, prefix = '') => {
    if (isPrivacyMode) return '•••••';
    return `${prefix}${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const formatPnl = (pnl: number) => {
    if (isPrivacyMode) return '•••••';
    const sign = pnl >= 0 ? '+' : '';
    return `${sign}$${pnl.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  return (
    <div className="bg-surface-container border border-outline-variant flex flex-col overflow-hidden">
      <div className="flex items-center justify-between px-3 py-2 border-b border-outline-variant bg-surface-container-low">
        <p className="font-header-md text-header-md text-on-surface">Active Inventory</p>
        <div className="flex items-center gap-2">
          <span className="text-label-caps text-secondary">REAL-TIME DATA FEED</span>
          <div className="w-1.5 h-1.5 rounded-full bg-[#00FF94] animate-pulse"></div>
        </div>
      </div>
      <div className="flex-1 overflow-y-auto">
        <table className="w-full border-collapse">
          <thead className="sticky top-0 bg-surface-container text-label-caps text-secondary text-left border-b border-outline-variant">
            <tr>
              <th className="p-2 font-bold">INSTRUMENT</th>
              <th className="p-2 font-bold">SIDE</th>
              <th className="p-2 font-bold">SIZE</th>
              <th className="p-2 font-bold">ENTRY</th>
              <th className="p-2 font-bold">MARK</th>
              <th className="p-2 font-bold text-right">UNREALIZED PNL</th>
              <th className="p-2 font-bold text-right">ACTION</th>
            </tr>
          </thead>
          <tbody className="font-data-tabular text-body-base divide-y divide-outline-variant/20">
            {positions.map((position, index) => (
              <tr key={index} className="hover:bg-surface-container-high transition-colors">
                <td className="p-2 font-bold text-on-surface">{position.instrument}</td>
                <td className={`p-2 ${position.side === 'LONG' ? 'text-[#00FF94]' : 'text-[#FF3B30]'}`}>
                  {position.side}
                </td>
                <td className="p-2">{formatValue(position.size)}</td>
                <td className="p-2">{formatValue(position.entryPrice)}</td>
                <td className="p-2">{formatValue(position.markPrice)}</td>
                <td className={`p-2 text-right ${position.unrealizedPnl >= 0 ? 'text-[#00FF94]' : 'text-[#FF3B30]'}`}>
                  {formatPnl(position.unrealizedPnl)}
                </td>
                <td className="p-2 text-right">
                  <button className="text-[10px] border border-outline-variant px-2 py-1 hover:border-primary transition-colors">
                    CLOSE
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
