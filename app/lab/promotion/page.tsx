'use client';

import { useState } from 'react';
import { MQPanel, MQTable, MQStatusBadge, MQSearch, MQButton, MQChartContainer } from '@/components/mqds';
import { Filter, ArrowUpCircle } from 'lucide-react';
import { PromotionInspector } from '@/components/lab/PromotionInspector';

type PromotionRequest = {
  id: string;
  modelName: string;
  version: string;
  fromEnvironment: string;
  toEnvironment: string;
  requestedBy: string;
  approvalScore: number;
  gatesPassed: number;
  gatesTotal: number;
  riskLevel: string;
  status: 'APPROVED' | 'PENDING' | 'REJECTED' | 'IN_REVIEW' | 'DEPLOYED';
  created: string;
};

const mockPromotions: PromotionRequest[] = [
  {
    id: 'prm_001',
    modelName: 'LSTM Market Predictor',
    version: 'v2.3',
    fromEnvironment: 'STAGING',
    toEnvironment: 'PRODUCTION',
    requestedBy: 'research.team',
    approvalScore: 0.92,
    gatesPassed: 8,
    gatesTotal: 8,
    riskLevel: 'LOW',
    status: 'APPROVED',
    created: '2026-01-15'
  },
  {
    id: 'prm_002',
    modelName: 'RandomForest Classifier',
    version: 'v1.8',
    fromEnvironment: 'EXPERIMENTAL',
    toEnvironment: 'STAGING',
    requestedBy: 'ml.ops',
    approvalScore: 0.85,
    gatesPassed: 7,
    gatesTotal: 8,
    riskLevel: 'MEDIUM',
    status: 'IN_REVIEW',
    created: '2026-02-10'
  },
  {
    id: 'prm_003',
    modelName: 'XGBoost Ensemble',
    version: 'v3.1',
    fromEnvironment: 'STAGING',
    toEnvironment: 'PRODUCTION',
    requestedBy: 'quant.team',
    approvalScore: 0.68,
    gatesPassed: 5,
    gatesTotal: 8,
    riskLevel: 'HIGH',
    status: 'REJECTED',
    created: '2026-02-20'
  },
  {
    id: 'prm_004',
    modelName: 'Ensemble Multi-Strategy',
    version: 'v1.2',
    fromEnvironment: 'STAGING',
    toEnvironment: 'PRODUCTION',
    requestedBy: 'research.team',
    approvalScore: 0.95,
    gatesPassed: 8,
    gatesTotal: 8,
    riskLevel: 'LOW',
    status: 'DEPLOYED',
    created: '2026-03-08'
  },
  {
    id: 'prm_005',
    modelName: 'Transformer Attention',
    version: 'v2.0',
    fromEnvironment: 'EXPERIMENTAL',
    toEnvironment: 'STAGING',
    requestedBy: 'ml.ops',
    approvalScore: 0.78,
    gatesPassed: 6,
    gatesTotal: 8,
    riskLevel: 'MEDIUM',
    status: 'PENDING',
    created: '2026-05-12'
  },
  {
    id: 'prm_006',
    modelName: 'GRU Volatility Model',
    version: 'v1.6',
    fromEnvironment: 'EXPERIMENTAL',
    toEnvironment: 'STAGING',
    requestedBy: 'quant.team',
    approvalScore: 0.82,
    gatesPassed: 7,
    gatesTotal: 8,
    riskLevel: 'MEDIUM',
    status: 'IN_REVIEW',
    created: '2026-06-18'
  },
  {
    id: 'prm_007',
    modelName: 'CNN Feature Extractor',
    version: 'v1.1',
    fromEnvironment: 'EXPERIMENTAL',
    toEnvironment: 'STAGING',
    requestedBy: 'research.team',
    approvalScore: 0.0,
    gatesPassed: 0,
    gatesTotal: 8,
    riskLevel: 'HIGH',
    status: 'PENDING',
    created: '2026-07-05'
  }
];

export default function PromotionPage() {
  const [selectedPromotion, setSelectedPromotion] = useState<PromotionRequest | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [environmentFilter, setEnvironmentFilter] = useState<string>('ALL');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [riskFilter, setRiskFilter] = useState<string>('ALL');

  const filteredPromotions = mockPromotions.filter(promo => {
    const matchesSearch = promo.modelName.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         promo.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         promo.requestedBy.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesEnvironment = environmentFilter === 'ALL' || promo.toEnvironment === environmentFilter;
    const matchesStatus = statusFilter === 'ALL' || promo.status === statusFilter;
    const matchesRisk = riskFilter === 'ALL' || promo.riskLevel === riskFilter;

    return matchesSearch && matchesEnvironment && matchesStatus && matchesRisk;
  });

  const statusMap: Record<string, 'success' | 'failure' | 'warning' | 'running' | 'pending'> = {
    APPROVED: 'success',
    DEPLOYED: 'success',
    REJECTED: 'failure',
    IN_REVIEW: 'warning',
    PENDING: 'pending'
  };

  const environments = ['ALL', 'PRODUCTION', 'STAGING', 'EXPERIMENTAL'];

  const statusCounts = mockPromotions.reduce((acc, p) => {
    acc[p.status] = (acc[p.status] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const getScoreColor = (score: number) => {
    if (score >= 0.85) return 'text-[var(--color-mq-success)]';
    if (score >= 0.70) return 'text-[var(--color-mq-warning)]';
    return 'text-[var(--color-mq-failure)]';
  };

  const scoreDistribution = [
    { range: '0.9+', count: mockPromotions.filter(p => p.approvalScore >= 0.9).length },
    { range: '0.85-0.9', count: mockPromotions.filter(p => p.approvalScore >= 0.85 && p.approvalScore < 0.9).length },
    { range: '0.75-0.85', count: mockPromotions.filter(p => p.approvalScore >= 0.75 && p.approvalScore < 0.85).length },
    { range: '0.7-0.75', count: mockPromotions.filter(p => p.approvalScore >= 0.7 && p.approvalScore < 0.75).length },
    { range: '<0.7', count: mockPromotions.filter(p => p.approvalScore < 0.7).length }
  ];

  const riskDistribution = ['LOW', 'MEDIUM', 'HIGH'].map(risk => ({
    risk,
    count: mockPromotions.filter(p => p.riskLevel === risk).length
  }));

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-2 flex-1">
          <MQSearch
            value={searchQuery}
            onSearch={setSearchQuery}
            placeholder="Search promotion requests..."
            className="w-[300px]"
          />
          <Filter size={16} className="text-[var(--color-mq-text-secondary)]" />

          <select
            value={environmentFilter}
            onChange={(e) => setEnvironmentFilter(e.target.value)}
            className="bg-[var(--color-mq-bg-secondary)] border border-[var(--color-mq-border)] rounded-[var(--radius-minimal)] px-2 h-8 text-[var(--font-size-small)] text-[var(--color-mq-text-primary)] font-mono"
          >
            {environments.map(env => (
              <option key={env} value={env}>{env}</option>
            ))}
          </select>

          <select
            value={riskFilter}
            onChange={(e) => setRiskFilter(e.target.value)}
            className="bg-[var(--color-mq-bg-secondary)] border border-[var(--color-mq-border)] rounded-[var(--radius-minimal)] px-2 h-8 text-[var(--font-size-small)] text-[var(--color-mq-text-primary)] font-mono"
          >
            <option value="ALL">All Risk</option>
            <option value="LOW">Low</option>
            <option value="MEDIUM">Medium</option>
            <option value="HIGH">High</option>
          </select>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-[var(--color-mq-bg-secondary)] border border-[var(--color-mq-border)] rounded-[var(--radius-minimal)] px-2 h-8 text-[var(--font-size-small)] text-[var(--color-mq-text-primary)] font-mono"
          >
            <option value="ALL">All Status ({mockPromotions.length})</option>
            <option value="APPROVED">Approved ({statusCounts.APPROVED || 0})</option>
            <option value="DEPLOYED">Deployed ({statusCounts.DEPLOYED || 0})</option>
            <option value="IN_REVIEW">In Review ({statusCounts.IN_REVIEW || 0})</option>
            <option value="REJECTED">Rejected ({statusCounts.REJECTED || 0})</option>
            <option value="PENDING">Pending ({statusCounts.PENDING || 0})</option>
          </select>
        </div>
        <MQButton>
          New Promotion Request
        </MQButton>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <MQChartContainer title="Approval Score Distribution" className="lg:col-span-1">
          <div className="h-[120px] flex items-end gap-1">
            {scoreDistribution.map((point, idx) => (
              <div key={idx} className="flex-1 flex flex-col items-center gap-1">
                <div
                  className="w-full rounded-t"
                  style={{
                    height: `${(point.count / Math.max(...scoreDistribution.map(p => p.count))) * 100}%`,
                    backgroundColor: idx === 0 ? 'var(--color-mq-success)' : idx === 1 ? 'var(--color-mq-success)' : idx === 2 ? 'var(--color-mq-warning)' : 'var(--color-mq-failure)'
                  }}
                />
                <span className="text-[var(--font-size-caption)] text-[var(--color-mq-text-muted)] font-mono">
                  {point.range}
                </span>
              </div>
            ))}
          </div>
        </MQChartContainer>

        <MQChartContainer title="Risk Distribution" className="lg:col-span-1">
          <div className="h-[120px] flex items-end gap-1">
            {riskDistribution.map((point, idx) => (
              <div key={idx} className="flex-1 flex flex-col items-center gap-1">
                <div
                  className="w-full bg-[var(--color-mq-accent)] rounded-t"
                  style={{ height: `${(point.count / Math.max(...riskDistribution.map(p => p.count))) * 100}%` }}
                />
                <span className="text-[var(--font-size-caption)] text-[var(--color-mq-text-muted)] font-mono">
                  {point.risk}
                </span>
              </div>
            ))}
          </div>
        </MQChartContainer>

        <MQChartContainer title="Promotion Queue" className="lg:col-span-1">
          <div className="h-[120px] flex flex-col justify-center items-center gap-2">
            <ArrowUpCircle size={32} className="text-[var(--color-mq-accent)]" />
            <div className="text-center">
              <div className="text-[var(--font-size-h3)] font-mono text-[var(--color-mq-text-primary)]">
                {mockPromotions.length}
              </div>
              <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)]">
                Total Requests
              </div>
            </div>
          </div>
        </MQChartContainer>
      </div>

      <MQPanel title={`Promotion Requests (${filteredPromotions.length})`}>
        <MQTable
          columns={[
            {
              key: 'modelName',
              header: 'Model Name',
              render: (row) => (
                <button
                  onClick={() => setSelectedPromotion(row)}
                  className="text-[var(--color-mq-accent)] hover:underline text-left font-mono"
                >
                  {row.modelName}
                </button>
              ),
              width: 'w-[200px]'
            },
            {
              key: 'version',
              header: 'Version',
              render: (row) => row.version,
              width: 'w-[80px]'
            },
            {
              key: 'promotion',
              header: 'Promotion',
              render: (row) => `${row.fromEnvironment} → ${row.toEnvironment}`,
              width: 'w-[200px]'
            },
            {
              key: 'approvalScore',
              header: 'Score',
              align: 'right',
              render: (row) => (
                <span className={getScoreColor(row.approvalScore)}>
                  {(row.approvalScore * 100).toFixed(0)}%
                </span>
              ),
              width: 'w-[80px]'
            },
            {
              key: 'gates',
              header: 'Gates',
              align: 'right',
              render: (row) => `${row.gatesPassed}/${row.gatesTotal}`,
              width: 'w-[80px]'
            },
            {
              key: 'riskLevel',
              header: 'Risk',
              render: (row) => (
                <span className={
                  row.riskLevel === 'LOW' ? 'text-[var(--color-mq-success)]' :
                  row.riskLevel === 'MEDIUM' ? 'text-[var(--color-mq-warning)]' :
                  'text-[var(--color-mq-failure)]'
                }>
                  {row.riskLevel}
                </span>
              ),
              width: 'w-[80px]'
            },
            {
              key: 'requestedBy',
              header: 'Requested By',
              render: (row) => row.requestedBy,
              width: 'w-[120px]'
            },
            {
              key: 'created',
              header: 'Created',
              render: (row) => new Date(row.created).toLocaleDateString(),
              width: 'w-[100px]'
            },
            {
              key: 'status',
              header: 'Status',
              render: (row) => (
                <MQStatusBadge status={statusMap[row.status]} label={row.status} />
              ),
              width: 'w-[120px]'
            }
          ]}
          data={filteredPromotions}
          keyExtractor={(row) => row.id}
        />
      </MQPanel>

      {selectedPromotion && (
        <PromotionInspector
          promotion={selectedPromotion}
          onClose={() => setSelectedPromotion(null)}
        />
      )}
    </div>
  );
}
