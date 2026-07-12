'use client';

import React from 'react';
import { MQPanel, MQStatusBadge } from '@/components/mqds';
import { Zap } from 'lucide-react';

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

interface TradeInspectorProps {
  trade: Trade;
  onClose: () => void;
}

export function TradeInspector({ trade, onClose }: TradeInspectorProps) {
  const statusMap: Record<string, 'success' | 'failure' | 'warning' | 'running' | 'pending'> = {
    PROFIT: 'success',
    LOSS: 'failure',
    BREAKEVEN: 'warning',
    OPEN: 'running',
    PARTIAL: 'pending'
  };

  const getPnLColor = (pnl: number) => {
    if (pnl > 0) return 'var(--color-mq-success)';
    if (pnl < 0) return 'var(--color-mq-failure)';
    return 'var(--color-mq-text-secondary)';
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-[var(--color-mq-bg-secondary)] border border-[var(--color-mq-border)] rounded-[var(--radius-minimal)] w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
        <div className="flex items-center justify-between p-4 border-b border-[var(--color-mq-border)]">
          <div className="flex items-center gap-3">
            <h2 className="text-[var(--font-size-h4)] font-bold text-[var(--color-mq-text-primary)] font-mono">
              {trade.id}
            </h2>
            <span className="text-[var(--font-size-body)] text-[var(--color-mq-text-secondary)] font-mono">
              {trade.symbol}
            </span>
            <MQStatusBadge status={statusMap[trade.status]} label={trade.status} />
          </div>
          <button
            onClick={onClose}
            className="text-[var(--color-mq-text-secondary)] hover:text-[var(--color-mq-text-primary)] transition-colors"
          >
            ✕
          </button>
        </div>

        <div className="flex-1 overflow-auto p-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div className="space-y-4">
              <MQPanel title="Trade Details">
                <div className="space-y-3">
                  <div>
                    <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)] mb-1">
                      Trade ID
                    </div>
                    <div className="text-[var(--font-size-body)] font-mono text-[var(--color-mq-text-primary)]">
                      {trade.id}
                    </div>
                  </div>
                  <div>
                    <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)] mb-1">
                      Symbol
                    </div>
                    <div className="text-[var(--font-size-body)] font-mono text-[var(--color-mq-text-primary)]">
                      {trade.symbol}
                    </div>
                  </div>
                  <div>
                    <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)] mb-1">
                      Side
                    </div>
                    <div className="text-[var(--font-size-body)] font-mono" style={{ color: trade.side === 'BUY' ? 'var(--color-mq-success)' : 'var(--color-mq-failure)' }}>
                      {trade.side}
                    </div>
                  </div>
                  <div>
                    <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)] mb-1">
                      Quantity
                    </div>
                    <div className="text-[var(--font-size-body)] font-mono text-[var(--color-mq-text-primary)]">
                      {trade.quantity}
                    </div>
                  </div>
                  <div>
                    <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)] mb-1">
                      Model
                    </div>
                    <div className="text-[var(--font-size-body)] font-mono text-[var(--color-mq-text-primary)]">
                      {trade.modelId}
                    </div>
                  </div>
                  <div>
                    <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)] mb-1">
                      Duration
                    </div>
                    <div className="text-[var(--font-size-body)] font-mono text-[var(--color-mq-text-primary)]">
                      {trade.duration}
                    </div>
                  </div>
                  <div>
                    <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)] mb-1">
                      Timestamp
                    </div>
                    <div className="text-[var(--font-size-body)] font-mono text-[var(--color-mq-text-primary)]">
                      {new Date(trade.timestamp).toLocaleString()}
                    </div>
                  </div>
                </div>
              </MQPanel>
            </div>

            <div className="space-y-4">
              <MQPanel title="Trade Performance">
                <div className="space-y-3">
                  <div>
                    <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)] mb-1">
                      Entry Price
                    </div>
                    <div className="text-[var(--font-size-h4)] font-mono text-[var(--color-mq-text-primary)]">
                      ${trade.entryPrice.toFixed(2)}
                    </div>
                  </div>
                  <div>
                    <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)] mb-1">
                      Exit Price
                    </div>
                    <div className="text-[var(--font-size-h4)] font-mono text-[var(--color-mq-text-primary)]">
                      {trade.exitPrice > 0 ? `$${trade.exitPrice.toFixed(2)}` : 'N/A'}
                    </div>
                  </div>
                  <div className="pt-3 border-t border-[var(--color-mq-border)]">
                    <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)] mb-2">
                      Profit & Loss
                    </div>
                    <div className="text-[var(--font-size-h3)] font-mono mb-1" style={{ color: getPnLColor(trade.pnl) }}>
                      ${trade.pnl.toFixed(2)}
                    </div>
                    <div className="text-[var(--font-size-h4)] font-mono" style={{ color: getPnLColor(trade.pnl) }}>
                      {trade.pnlPercent > 0 ? '+' : ''}{trade.pnlPercent.toFixed(2)}%
                    </div>
                  </div>
                </div>
              </MQPanel>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
