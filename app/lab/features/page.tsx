'use client';

import { useState } from 'react';
import { MQPanel, MQTable, MQStatusBadge, MQSearch, MQButton, MQChartContainer } from '@/components/mqds';
import { mockFeatures, Feature } from '@/lib/mock-data/features';
import { FeatureInspector } from '@/components/lab/FeatureInspector';
import { Filter, TrendingUp } from 'lucide-react';

export default function FeaturesPage() {
  const [selectedFeature, setSelectedFeature] = useState<Feature | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<string>('ALL');
  const [typeFilter, setTypeFilter] = useState<string>('ALL');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [importanceFilter, setImportanceFilter] = useState<string>('ALL');

  const filteredFeatures = mockFeatures.filter(feat => {
    const matchesSearch = feat.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         feat.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         feat.category.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCategory = categoryFilter === 'ALL' || feat.category === categoryFilter;
    const matchesType = typeFilter === 'ALL' || feat.type === typeFilter;
    const matchesStatus = statusFilter === 'ALL' || feat.status === statusFilter;

    let matchesImportance = true;
    if (importanceFilter === 'HIGH') matchesImportance = feat.importance >= 0.8;
    else if (importanceFilter === 'MEDIUM') matchesImportance = feat.importance >= 0.6 && feat.importance < 0.8;
    else if (importanceFilter === 'LOW') matchesImportance = feat.importance < 0.6;

    return matchesSearch && matchesCategory && matchesType && matchesStatus && matchesImportance;
  });

  const statusMap: Record<string, 'success' | 'failure' | 'warning' | 'running' | 'pending'> = {
    ACTIVE: 'success',
    EXPERIMENTAL: 'warning',
    VALIDATING: 'running',
    DEPRECATED: 'pending',
    FAILED: 'failure',
    ARCHIVED: 'pending'
  };

  const categories = ['ALL', ...Array.from(new Set(mockFeatures.map(f => f.category)))];
  const types = ['ALL', ...Array.from(new Set(mockFeatures.map(f => f.type)))];

  const statusCounts = mockFeatures.reduce((acc, f) => {
    acc[f.status] = (acc[f.status] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const categoryCounts = mockFeatures.reduce((acc, f) => {
    acc[f.category] = (acc[f.category] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const getImportanceColor = (score: number) => {
    if (score >= 0.8) return 'text-[var(--color-mq-success)]';
    if (score >= 0.6) return 'text-[var(--color-mq-warning)]';
    return 'text-[var(--color-mq-failure)]';
  };

  const importanceDistribution = [
    { range: '0.9-1.0', count: mockFeatures.filter(f => f.importance >= 0.9).length },
    { range: '0.8-0.9', count: mockFeatures.filter(f => f.importance >= 0.8 && f.importance < 0.9).length },
    { range: '0.7-0.8', count: mockFeatures.filter(f => f.importance >= 0.7 && f.importance < 0.8).length },
    { range: '0.6-0.7', count: mockFeatures.filter(f => f.importance >= 0.6 && f.importance < 0.7).length },
    { range: '<0.6', count: mockFeatures.filter(f => f.importance < 0.6).length }
  ];

  const typeDistribution = types.slice(1).map(type => ({
    type,
    count: mockFeatures.filter(f => f.type === type).length
  }));

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-2 flex-1">
          <MQSearch
            value={searchQuery}
            onSearch={setSearchQuery}
            placeholder="Search features..."
            className="w-[300px]"
          />
          <Filter size={16} className="text-[var(--color-mq-text-secondary)]" />

          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="bg-[var(--color-mq-bg-secondary)] border border-[var(--color-mq-border)] rounded-[var(--radius-minimal)] px-2 h-8 text-[var(--font-size-small)] text-[var(--color-mq-text-primary)] font-mono"
          >
            {categories.map(cat => (
              <option key={cat} value={cat}>
                {cat === 'ALL' ? `All Categories (${mockFeatures.length})` : `${cat} (${categoryCounts[cat] || 0})`}
              </option>
            ))}
          </select>

          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="bg-[var(--color-mq-bg-secondary)] border border-[var(--color-mq-border)] rounded-[var(--radius-minimal)] px-2 h-8 text-[var(--font-size-small)] text-[var(--color-mq-text-primary)] font-mono"
          >
            {types.map(type => (
              <option key={type} value={type}>{type}</option>
            ))}
          </select>

          <select
            value={importanceFilter}
            onChange={(e) => setImportanceFilter(e.target.value)}
            className="bg-[var(--color-mq-bg-secondary)] border border-[var(--color-mq-border)] rounded-[var(--radius-minimal)] px-2 h-8 text-[var(--font-size-small)] text-[var(--color-mq-text-primary)] font-mono"
          >
            <option value="ALL">All Importance</option>
            <option value="HIGH">High (≥80%)</option>
            <option value="MEDIUM">Medium (60-80%)</option>
            <option value="LOW">Low (&lt;60%)</option>
          </select>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-[var(--color-mq-bg-secondary)] border border-[var(--color-mq-border)] rounded-[var(--radius-minimal)] px-2 h-8 text-[var(--font-size-small)] text-[var(--color-mq-text-primary)] font-mono"
          >
            <option value="ALL">All Status ({mockFeatures.length})</option>
            <option value="ACTIVE">Active ({statusCounts.ACTIVE || 0})</option>
            <option value="EXPERIMENTAL">Experimental ({statusCounts.EXPERIMENTAL || 0})</option>
            <option value="VALIDATING">Validating ({statusCounts.VALIDATING || 0})</option>
            <option value="DEPRECATED">Deprecated ({statusCounts.DEPRECATED || 0})</option>
            <option value="FAILED">Failed ({statusCounts.FAILED || 0})</option>
            <option value="ARCHIVED">Archived ({statusCounts.ARCHIVED || 0})</option>
          </select>
        </div>
        <MQButton>
          Create Feature
        </MQButton>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <MQChartContainer title="Importance Distribution" className="lg:col-span-1">
          <div className="h-[120px] flex items-end gap-1">
            {importanceDistribution.map((point, idx) => (
              <div key={idx} className="flex-1 flex flex-col items-center gap-1">
                <div
                  className="w-full rounded-t"
                  style={{
                    height: `${(point.count / Math.max(...importanceDistribution.map(p => p.count))) * 100}%`,
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

        <MQChartContainer title="Type Distribution" className="lg:col-span-1">
          <div className="h-[120px] flex items-end gap-1">
            {typeDistribution.map((point, idx) => (
              <div key={idx} className="flex-1 flex flex-col items-center gap-1">
                <div
                  className="w-full bg-[var(--color-mq-accent)] rounded-t"
                  style={{ height: `${(point.count / Math.max(...typeDistribution.map(p => p.count))) * 100}%` }}
                />
                <span className="text-[var(--font-size-caption)] text-[var(--color-mq-text-muted)] font-mono">
                  {point.type}
                </span>
              </div>
            ))}
          </div>
        </MQChartContainer>

        <MQChartContainer title="Feature Count" className="lg:col-span-1">
          <div className="h-[120px] flex flex-col justify-center items-center gap-2">
            <TrendingUp size={32} className="text-[var(--color-mq-accent)]" />
            <div className="text-center">
              <div className="text-[var(--font-size-h3)] font-mono text-[var(--color-mq-text-primary)]">
                {mockFeatures.length}
              </div>
              <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)]">
                Total Features
              </div>
            </div>
          </div>
        </MQChartContainer>
      </div>

      <MQPanel title={`Features (${filteredFeatures.length})`}>
        <MQTable
          columns={[
            {
              key: 'name',
              header: 'Feature Name',
              render: (row) => (
                <button
                  onClick={() => setSelectedFeature(row)}
                  className="text-[var(--color-mq-accent)] hover:underline text-left font-mono"
                >
                  {row.name}
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
              key: 'category',
              header: 'Category',
              render: (row) => row.category,
              width: 'w-[160px]'
            },
            {
              key: 'type',
              header: 'Type',
              render: (row) => row.type,
              width: 'w-[100px]'
            },
            {
              key: 'importance',
              header: 'Importance',
              align: 'right',
              render: (row) => (
                <span className={getImportanceColor(row.importance)}>
                  {(row.importance * 100).toFixed(1)}%
                </span>
              ),
              width: 'w-[100px]'
            },
            {
              key: 'nullRate',
              header: 'Null Rate',
              align: 'right',
              render: (row) => (
                <span className={row.nullRate < 0.05 ? 'text-[var(--color-mq-success)]' : row.nullRate < 0.15 ? 'text-[var(--color-mq-warning)]' : 'text-[var(--color-mq-failure)]'}>
                  {(row.nullRate * 100).toFixed(2)}%
                </span>
              ),
              width: 'w-[90px]'
            },
            {
              key: 'usedByDatasets',
              header: 'Datasets',
              align: 'right',
              render: (row) => row.usedByDatasets,
              width: 'w-[80px]'
            },
            {
              key: 'usedByExperiments',
              header: 'Experiments',
              align: 'right',
              render: (row) => row.usedByExperiments,
              width: 'w-[100px]'
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
          data={filteredFeatures}
          keyExtractor={(row) => row.id}
        />
      </MQPanel>

      {selectedFeature && (
        <FeatureInspector
          feature={selectedFeature}
          onClose={() => setSelectedFeature(null)}
        />
      )}
    </div>
  );
}
