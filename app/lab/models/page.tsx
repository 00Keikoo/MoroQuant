'use client';

import { useState } from 'react';
import { MQPanel, MQTable, MQStatusBadge, MQSearch, MQButton, MQChartContainer } from '@/components/mqds';
import { Filter, Clock } from 'lucide-react';
import { ModelInspector } from '@/components/lab/ModelInspector';

type Model = {
  id: string;
  name: string;
  version: string;
  architecture: string;
  framework: string;
  accuracy: number;
  parameters: number;
  trainingTime: string;
  deployments: number;
  status: 'PRODUCTION' | 'STAGING' | 'EXPERIMENTAL' | 'DEPRECATED' | 'ARCHIVED';
  created: string;
};

const mockModels: Model[] = [
  {
    id: 'mdl_001',
    name: 'LSTM Market Predictor',
    version: 'v2.3',
    architecture: 'LSTM',
    framework: 'PyTorch',
    accuracy: 0.712,
    parameters: 8500000,
    trainingTime: '14.2h',
    deployments: 3,
    status: 'PRODUCTION',
    created: '2026-01-10'
  },
  {
    id: 'mdl_002',
    name: 'RandomForest Classifier',
    version: 'v1.8',
    architecture: 'Random Forest',
    framework: 'Scikit-learn',
    accuracy: 0.678,
    parameters: 2100000,
    trainingTime: '3.5h',
    deployments: 2,
    status: 'PRODUCTION',
    created: '2025-11-22'
  },
  {
    id: 'mdl_003',
    name: 'XGBoost Ensemble',
    version: 'v3.1',
    architecture: 'XGBoost',
    framework: 'XGBoost',
    accuracy: 0.645,
    parameters: 4200000,
    trainingTime: '6.8h',
    deployments: 1,
    status: 'STAGING',
    created: '2026-02-01'
  },
  {
    id: 'mdl_004',
    name: 'Ensemble Multi-Strategy',
    version: 'v1.2',
    architecture: 'Ensemble',
    framework: 'Custom',
    accuracy: 0.734,
    parameters: 15300000,
    trainingTime: '28.4h',
    deployments: 2,
    status: 'PRODUCTION',
    created: '2026-03-05'
  },
  {
    id: 'mdl_005',
    name: 'GRU Volatility Model',
    version: 'v1.5',
    architecture: 'GRU',
    framework: 'TensorFlow',
    accuracy: 0.598,
    parameters: 6800000,
    trainingTime: '11.2h',
    deployments: 0,
    status: 'DEPRECATED',
    created: '2025-09-15'
  },
  {
    id: 'mdl_006',
    name: 'Transformer Attention',
    version: 'v2.0',
    architecture: 'Transformer',
    framework: 'PyTorch',
    accuracy: 0.689,
    parameters: 12400000,
    trainingTime: '22.6h',
    deployments: 1,
    status: 'EXPERIMENTAL',
    created: '2026-05-10'
  },
  {
    id: 'mdl_007',
    name: 'CNN Feature Extractor',
    version: 'v1.0',
    architecture: 'CNN',
    framework: 'PyTorch',
    accuracy: 0.0,
    parameters: 5200000,
    trainingTime: '0h',
    deployments: 0,
    status: 'ARCHIVED',
    created: '2025-07-20'
  }
];

export default function ModelsPage() {
  const [selectedModel, setSelectedModel] = useState<Model | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [architectureFilter, setArchitectureFilter] = useState<string>('ALL');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [accuracyFilter, setAccuracyFilter] = useState<string>('ALL');

  const filteredModels = mockModels.filter(model => {
    const matchesSearch = model.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         model.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         model.architecture.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesArchitecture = architectureFilter === 'ALL' || model.architecture === architectureFilter;
    const matchesStatus = statusFilter === 'ALL' || model.status === statusFilter;

    let matchesAccuracy = true;
    if (accuracyFilter === 'HIGH') matchesAccuracy = model.accuracy >= 0.70;
    else if (accuracyFilter === 'MEDIUM') matchesAccuracy = model.accuracy >= 0.60 && model.accuracy < 0.70;
    else if (accuracyFilter === 'LOW') matchesAccuracy = model.accuracy < 0.60;

    return matchesSearch && matchesArchitecture && matchesStatus && matchesAccuracy;
  });

  const statusMap: Record<string, 'success' | 'failure' | 'warning' | 'running' | 'pending'> = {
    PRODUCTION: 'success',
    STAGING: 'warning',
    EXPERIMENTAL: 'running',
    DEPRECATED: 'pending',
    ARCHIVED: 'pending'
  };

  const architectures = ['ALL', ...Array.from(new Set(mockModels.map(m => m.architecture)))];

  const statusCounts = mockModels.reduce((acc, m) => {
    acc[m.status] = (acc[m.status] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const getAccuracyColor = (score: number) => {
    if (score >= 0.70) return 'text-[var(--color-mq-success)]';
    if (score >= 0.60) return 'text-[var(--color-mq-warning)]';
    return 'text-[var(--color-mq-failure)]';
  };

  const accuracyDistribution = [
    { range: '0.7+', count: mockModels.filter(m => m.accuracy >= 0.7).length },
    { range: '0.65-0.7', count: mockModels.filter(m => m.accuracy >= 0.65 && m.accuracy < 0.7).length },
    { range: '0.6-0.65', count: mockModels.filter(m => m.accuracy >= 0.6 && m.accuracy < 0.65).length },
    { range: '0.55-0.6', count: mockModels.filter(m => m.accuracy >= 0.55 && m.accuracy < 0.6).length },
    { range: '<0.55', count: mockModels.filter(m => m.accuracy < 0.55).length }
  ];

  const architectureDistribution = architectures.slice(1).map(arch => ({
    architecture: arch,
    count: mockModels.filter(m => m.architecture === arch).length
  }));

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-2 flex-1">
          <MQSearch
            value={searchQuery}
            onSearch={setSearchQuery}
            placeholder="Search models..."
            className="w-[300px]"
          />
          <Filter size={16} className="text-[var(--color-mq-text-secondary)]" />

          <select
            value={architectureFilter}
            onChange={(e) => setArchitectureFilter(e.target.value)}
            className="bg-[var(--color-mq-bg-secondary)] border border-[var(--color-mq-border)] rounded-[var(--radius-minimal)] px-2 h-8 text-[var(--font-size-small)] text-[var(--color-mq-text-primary)] font-mono"
          >
            {architectures.map(arch => (
              <option key={arch} value={arch}>{arch}</option>
            ))}
          </select>

          <select
            value={accuracyFilter}
            onChange={(e) => setAccuracyFilter(e.target.value)}
            className="bg-[var(--color-mq-bg-secondary)] border border-[var(--color-mq-border)] rounded-[var(--radius-minimal)] px-2 h-8 text-[var(--font-size-small)] text-[var(--color-mq-text-primary)] font-mono"
          >
            <option value="ALL">All Accuracy</option>
            <option value="HIGH">High (≥70%)</option>
            <option value="MEDIUM">Medium (60-70%)</option>
            <option value="LOW">Low (&lt;60%)</option>
          </select>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-[var(--color-mq-bg-secondary)] border border-[var(--color-mq-border)] rounded-[var(--radius-minimal)] px-2 h-8 text-[var(--font-size-small)] text-[var(--color-mq-text-primary)] font-mono"
          >
            <option value="ALL">All Status ({mockModels.length})</option>
            <option value="PRODUCTION">Production ({statusCounts.PRODUCTION || 0})</option>
            <option value="STAGING">Staging ({statusCounts.STAGING || 0})</option>
            <option value="EXPERIMENTAL">Experimental ({statusCounts.EXPERIMENTAL || 0})</option>
            <option value="DEPRECATED">Deprecated ({statusCounts.DEPRECATED || 0})</option>
            <option value="ARCHIVED">Archived ({statusCounts.ARCHIVED || 0})</option>
          </select>
        </div>
        <MQButton>
          Register Model
        </MQButton>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <MQChartContainer title="Accuracy Distribution" className="lg:col-span-1">
          <div className="h-[120px] flex items-end gap-1">
            {accuracyDistribution.map((point, idx) => (
              <div key={idx} className="flex-1 flex flex-col items-center gap-1">
                <div
                  className="w-full rounded-t"
                  style={{
                    height: `${(point.count / Math.max(...accuracyDistribution.map(p => p.count))) * 100}%`,
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

        <MQChartContainer title="Architecture Distribution" className="lg:col-span-1">
          <div className="h-[120px] flex items-end gap-1">
            {architectureDistribution.map((point, idx) => (
              <div key={idx} className="flex-1 flex flex-col items-center gap-1">
                <div
                  className="w-full bg-[var(--color-mq-accent)] rounded-t"
                  style={{ height: `${(point.count / Math.max(...architectureDistribution.map(p => p.count))) * 100}%` }}
                />
                <span className="text-[var(--font-size-caption)] text-[var(--color-mq-text-muted)] font-mono">
                  {point.architecture}
                </span>
              </div>
            ))}
          </div>
        </MQChartContainer>

        <MQChartContainer title="Model Registry" className="lg:col-span-1">
          <div className="h-[120px] flex flex-col justify-center items-center gap-2">
            <Clock size={32} className="text-[var(--color-mq-accent)]" />
            <div className="text-center">
              <div className="text-[var(--font-size-h3)] font-mono text-[var(--color-mq-text-primary)]">
                {mockModels.length}
              </div>
              <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)]">
                Total Models
              </div>
            </div>
          </div>
        </MQChartContainer>
      </div>

      <MQPanel title={`Models (${filteredModels.length})`}>
        <MQTable
          columns={[
            {
              key: 'name',
              header: 'Model Name',
              render: (row) => (
                <button
                  onClick={() => setSelectedModel(row)}
                  className="text-[var(--color-mq-accent)] hover:underline text-left font-mono"
                >
                  {row.name}
                </button>
              ),
              width: 'w-[220px]'
            },
            {
              key: 'version',
              header: 'Version',
              render: (row) => row.version,
              width: 'w-[80px]'
            },
            {
              key: 'architecture',
              header: 'Architecture',
              render: (row) => row.architecture,
              width: 'w-[140px]'
            },
            {
              key: 'framework',
              header: 'Framework',
              render: (row) => row.framework,
              width: 'w-[120px]'
            },
            {
              key: 'accuracy',
              header: 'Accuracy',
              align: 'right',
              render: (row) => (
                <span className={getAccuracyColor(row.accuracy)}>
                  {(row.accuracy * 100).toFixed(1)}%
                </span>
              ),
              width: 'w-[90px]'
            },
            {
              key: 'parameters',
              header: 'Parameters',
              align: 'right',
              render: (row) => `${(row.parameters / 1000000).toFixed(1)}M`,
              width: 'w-[100px]'
            },
            {
              key: 'trainingTime',
              header: 'Training',
              align: 'right',
              render: (row) => row.trainingTime,
              width: 'w-[90px]'
            },
            {
              key: 'deployments',
              header: 'Deploys',
              align: 'right',
              render: (row) => row.deployments,
              width: 'w-[80px]'
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
          data={filteredModels}
          keyExtractor={(row) => row.id}
        />
      </MQPanel>

      {selectedModel && (
        <ModelInspector
          model={selectedModel}
          onClose={() => setSelectedModel(null)}
        />
      )}
    </div>
  );
}
