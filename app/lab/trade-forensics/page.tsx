'use client';

import { useState } from 'react';
import { MQPanel, MQTable, MQStatusBadge, MQSearch, MQButton } from '@/components/mqds';
import { Filter, Zap } from 'lucide-react';
import { TradeInspector } from '@/components/lab/TradeInspector';

type Trade = {
  id: string;
  symbol: string;
  side: 'BUY' | 'SELL';
  entryPrice: number;
  exitPrice: number;
  quantity: number;
  pnl: number;
  pnlPercent: number;
  modelId: string;
  timestamp: string;
  duration: string;
  status: 'PROFIT' | 'LOSS' | 'BREAKEVEN' | 'OPEN' | 'PARTIAL';
};

const mockTrades: Trade[] = [
  {
    id: 'trd_001',
    symbol: 'BTCUSDT',
    side: 'BUY',
    entryPrice: 64230.50,
    exitPrice: 65890.20,
    quantity: 0.5,
    pnl: 829.85,
    pnlPercent: 2.58,
    modelId: 'LSTM_v2.3',
    timestamp: '2026-07-12T08:30:00Z',
    duration: '4h 15m',
    status: 'PROFIT'
  },
  {
    id: 'trd_002',
    symbol: 'ETHUSDT',
    side: 'SELL',
    entryPrice: 3420.80,
    exitPrice: 3380.50,
    quantity: 2.5,
    pnl: 100.75,
    pnlPercent: 1.18,
    modelId: 'RandomForest_v1.8',
    timestamp: '2026-07-12T06:15:00Z',
    duration: '2h 45m',
    status: 'PROFIT'
  },
  {
    id: 'trd_003',
    symbol: 'SOLUSDT',
    side: 'BUY',
    entryPrice: 145.20,
    exitPrice: 139.80,
    quantity: 10,
    pnl: -54.00,
    pnlPercent: -3.72,
    modelId: 'XGBoost_v3.1',
    timestamp: '2026-07-12T04:00:00Z',
    duration: '6h 30m',
    status: 'LOSS'
  },
  {
    id: 'trd_004',
    symbol: 'BTCUSDT',
    side: 'SELL',
    entryPrice: 65200.00,
    exitPrice: 62100.30,
    quantity: 0.3,
    pnl: 929.91,
    pnlPercent: 4.75,
    modelId: 'Ensemble_v1.2',
    timestamp: '2026-07-11T22:00:00Z',
    duration: '8h 20m',
    status: 'PROFIT'
  },
  {
    id: 'trd_005',
    symbol: 'ADAUSDT',
    side: 'BUY',
    entryPrice: 0.4580,
    exitPrice: 0.4575,
    quantity: 1000,
    pnl: -5.00,
    pnlPercent: -0.11,
    modelId: 'GRU_v1.5',
    timestamp: '2026-07-11T20:30:00Z',
    duration: '1h 15m',
    status: 'BREAKEVEN'
  },
  {
    id: 'trd_006',
    symbol: 'ETHUSDT',
    side: 'BUY',
    entryPrice: 3390.00,
    exitPrice: 0,
    quantity: 1.5,
    pnl: 0,
    pnlPercent: 0,
    modelId: 'Transformer_v2.0',
    timestamp: '2026-07-12T14:00:00Z',
    duration: '3h 00m',
    status: 'OPEN'
  },
  {
    id: 'trd_007',
    symbol: 'BNBUSDT',
    side: 'SELL',
    entryPrice: 582.30,
    exitPrice: 578.90,
    quantity: 5,
    pnl: 17.00,
    pnlPercent: 0.58,
    modelId: 'LSTM_v2.3',
    timestamp: '2026-07-12T12:45:00Z',
    duration: '4h 15m',
    status: 'PROFIT'
  },
  {
    id: 'trd_008',
    symbol: 'DOGEUSDT',
    side: 'BUY',
    entryPrice: 0.1245,
    exitPrice: 0.1198,
    quantity: 5000,
    pnl: -23.50,
    pnlPercent: -3.77,
    modelId: 'RandomForest_v1.8',
    timestamp: '2026-07-12T10:00:00Z',
    duration: '7h 00m',
    status: 'LOSS'
  }
];

export default function TradeForensicsPage() {
  const [selectedTrade, setSelectedTrade] = useState<Trade | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');

  const filteredTrades = mockTrades.filter(trade => {
    const matchesSearch = trade.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         trade.symbol.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         trade.modelId.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = statusFilter === 'ALL' || trade.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const statusMap: Record<string, 'success' | 'failure' | 'warning' | 'running' | 'pending'> = {
    PROFIT: 'success',
    LOSS: 'failure',
    BREAKEVEN: 'warning',
    OPEN: 'running',
    PARTIAL: 'pending'
  };

  const statusCounts = mockTrades.reduce((acc, trade) => {
    acc[trade.status] = (acc[trade.status] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <MQSearch
            value={searchQuery}
            onSearch={setSearchQuery}
            placeholder="Search trades..."
          />
          <div className="flex items-center gap-2">
            <Filter size={16} className="text-[var(--color-mq-text-secondary)]" />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="bg-[var(--color-mq-bg-secondary)] border border-[var(--color-mq-border)] rounded-[var(--radius-minimal)] px-2 h-8 text-[var(--font-size-small)] text-[var(--color-mq-text-primary)] font-mono"
            >
              <option value="ALL">All ({mockTrades.length})</option>
              <option value="PROFIT">Profit ({statusCounts.PROFIT || 0})</option>
              <option value="LOSS">Loss ({statusCounts.LOSS || 0})</option>
              <option value="BREAKEVEN">Breakeven ({statusCounts.BREAKEVEN || 0})</option>
              <option value="OPEN">Open ({statusCounts.OPEN || 0})</option>
              <option value="PARTIAL">Partial ({statusCounts.PARTIAL || 0})</option>
            </select>
          </div>
        </div>
        <MQButton>
          Export Trades
        </MQButton>
      </div>

      <MQPanel title={`Trade History (${filteredTrades.length})`}>
        <MQTable
          columns={[
            {
              key: 'id',
              header: 'Trade ID',
              render: (row) => (
                <button
                  onClick={() => setSelectedTrade(row)}
                  className="text-[var(--color-mq-accent)] hover:underline text-left font-mono"
                >
                  {row.id}
                </button>
              ),
              width: 'w-[120px]'
            },
            {
              key: 'status',
              header: 'Status',
              render: (row) => (
                <MQStatusBadge status={statusMap[row.status]} label={row.status} />
              ),
              width: 'w-[100px]'
            },
            {
              key: 'symbol',
              header: 'Symbol',
              render: (row) => row.symbol,
              width: 'w-[100px]'
            },
            {
              key: 'side',
              header: 'Side',
              render: (row) => (
                <span className={row.side === 'BUY' ? 'text-[var(--color-mq-success)]' : 'text-[var(--color-mq-failure)]'}>
                  {row.side}
                </span>
              ),
              width: 'w-[80px]'
            },
            {
              key: 'entryPrice',
              header: 'Entry',
              align: 'right',
              render: (row) => row.entryPrice.toFixed(2),
              width: 'w-[100px]'
            },
            {
              key: 'exitPrice',
              header: 'Exit',
              align: 'right',
              render: (row) => row.exitPrice > 0 ? row.exitPrice.toFixed(2) : '-',
              width: 'w-[100px]'
            },
            {
              key: 'pnl',
              header: 'PnL',
              align: 'right',
              render: (row) => (
                <span className={row.pnl > 0 ? 'text-[var(--color-mq-success)]' : row.pnl < 0 ? 'text-[var(--color-mq-failure)]' : 'text-[var(--color-mq-text-secondary)]'}>
                  ${row.pnl.toFixed(2)}
                </span>
              ),
              width: 'w-[100px]'
            },
            {
              key: 'pnlPercent',
              header: 'PnL %',
              align: 'right',
              render: (row) => (
                <span className={row.pnlPercent > 0 ? 'text-[var(--color-mq-success)]' : row.pnlPercent < 0 ? 'text-[var(--color-mq-failure)]' : 'text-[var(--color-mq-text-secondary)]'}>
                  {row.pnlPercent > 0 ? '+' : ''}{row.pnlPercent.toFixed(2)}%
                </span>
              ),
              width: 'w-[90px]'
            },
            {
              key: 'modelId',
              header: 'Model',
              render: (row) => row.modelId,
              width: 'w-[160px]'
            },
            {
              key: 'duration',
              header: 'Duration',
              align: 'right',
              render: (row) => row.duration,
              width: 'w-[100px]'
            },
            {
              key: 'timestamp',
              header: 'Timestamp',
              render: (row) => new Date(row.timestamp).toLocaleString(),
              width: 'w-[180px]'
            }
          ]}
          data={filteredTrades}
          keyExtractor={(row) => row.id}
        />
      </MQPanel>

      {selectedTrade && (
        <TradeInspector
          trade={selectedTrade}
          onClose={() => setSelectedTrade(null)}
        />
      )}
    </div>
  );
}
