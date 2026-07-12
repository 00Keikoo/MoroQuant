'use client';

import { useState } from 'react';
import { MQPanel, MQTable, MQStatusBadge, MQSearch, MQButton, MQChartContainer } from '@/components/mqds';
import { mockDatasets, Dataset } from '@/lib/mock-data/datasets';
import { DatasetInspector } from '@/components/lab/DatasetInspector';
import { Filter, TrendingUp } from 'lucide-react';

export default function DatasetsPage() {
  const [selectedDataset, setSelectedDataset] = useState<Dataset | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [assetClassFilter, setAssetClassFilter] = useState<string>('ALL');
  const [exchangeFilter, setExchangeFilter] = useState<string>('ALL');
  const [timeframeFilter, setTimeframeFilter] = useState<string>('ALL');
  const [qualityFilter, setQualityFilter] = useState<string>('ALL');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');

  const filteredDatasets = mockDatasets.filter(ds => {
    const matchesSearch = ds.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         ds.version.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         ds.exchange.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesAssetClass = assetClassFilter === 'ALL' || ds.assetClass === assetClassFilter;
    const matchesExchange = exchangeFilter === 'ALL' || ds.exchange === exchangeFilter;
    const matchesTimeframe = timeframeFilter === 'ALL' || ds.timeframe === timeframeFilter;
    const matchesStatus = statusFilter === 'ALL' || ds.status === statusFilter;

    let matchesQuality = true;
    if (qualityFilter === 'HIGH') matchesQuality = ds.qualityScore >= 99;
    else if (qualityFilter === 'MEDIUM') matchesQuality = ds.qualityScore >= 97 && ds.qualityScore < 99;
    else if (qualityFilter === 'LOW') matchesQuality = ds.qualityScore < 97;

    return matchesSearch && matchesAssetClass && matchesExchange && matchesTimeframe && matchesQuality && matchesStatus;
  });

  const statusMap: Record<string, 'success' | 'failure' | 'warning' | 'running' | 'pending'> = {
    FROZEN: 'success',
    BUILDING: 'running',
    VALIDATING: 'warning',
    FAILED: 'failure',
    ARCHIVED: 'pending'
  };

  const assetClasses = ['ALL', ...Array.from(new Set(mockDatasets.map(ds => ds.assetClass)))];
  const exchanges = ['ALL', ...Array.from(new Set(mockDatasets.map(ds => ds.exchange)))];
  const timeframes = ['ALL', ...Array.from(new Set(mockDatasets.map(ds => ds.timeframe)))];

  const statusCounts = mockDatasets.reduce((acc, ds) => {
    acc[ds.status] = (acc[ds.status] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const assetClassCounts = mockDatasets.reduce((acc, ds) => {
    acc[ds.assetClass] = (acc[ds.assetClass] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const getQualityColor = (score: number) => {
    if (score >= 99) return 'text-[var(--color-mq-success)]';
    if (score >= 97) return 'text-[var(--color-mq-warning)]';
    return 'text-[var(--color-mq-failure)]';
  };

  const coverageTimeline = [
    { month: 'Jan', datasets: 18 },
    { month: 'Feb', datasets: 20 },
    { month: 'Mar', datasets: 22 },
    { month: 'Apr', datasets: 25 },
    { month: 'May', datasets: 27 },
    { month: 'Jun', datasets: 30 },
    { month: 'Jul', datasets: 32 }
  ];

  const missingValueTrend = [
    { month: 'Jan', avg: 0.18 },
    { month: 'Feb', avg: 0.16 },
    { month: 'Mar', avg: 0.14 },
    { month: 'Apr', avg: 0.12 },
    { month: 'May', avg: 0.11 },
    { month: 'Jun', avg: 0.10 },
    { month: 'Jul', avg: 0.09 }
  ];

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-2 flex-1">
          <MQSearch
            value={searchQuery}
            onSearch={setSearchQuery}
            placeholder="Search datasets..."
            className="w-[300px]"
          />
          <Filter size={16} className="text-[var(--color-mq-text-secondary)]" />

          <select
            value={assetClassFilter}
            onChange={(e) => setAssetClassFilter(e.target.value)}
            className="bg-[var(--color-mq-bg-secondary)] border border-[var(--color-mq-border)] rounded-[var(--radius-minimal)] px-2 h-8 text-[var(--font-size-small)] text-[var(--color-mq-text-primary)] font-mono"
          >
            {assetClasses.map(ac => (
              <option key={ac} value={ac}>
                {ac === 'ALL' ? `All Assets (${mockDatasets.length})` : `${ac} (${assetClassCounts[ac] || 0})`}
              </option>
            ))}
          </select>

          <select
            value={exchangeFilter}
            onChange={(e) => setExchangeFilter(e.target.value)}
            className="bg-[var(--color-mq-bg-secondary)] border border-[var(--color-mq-border)] rounded-[var(--radius-minimal)] px-2 h-8 text-[var(--font-size-small)] text-[var(--color-mq-text-primary)] font-mono"
          >
            {exchanges.map(ex => (
              <option key={ex} value={ex}>{ex}</option>
            ))}
          </select>

          <select
            value={timeframeFilter}
            onChange={(e) => setTimeframeFilter(e.target.value)}
            className="bg-[var(--color-mq-bg-secondary)] border border-[var(--color-mq-border)] rounded-[var(--radius-minimal)] px-2 h-8 text-[var(--font-size-small)] text-[var(--color-mq-text-primary)] font-mono"
          >
            {timeframes.map(tf => (
              <option key={tf} value={tf}>{tf}</option>
            ))}
          </select>

          <select
            value={qualityFilter}
            onChange={(e) => setQualityFilter(e.target.value)}
            className="bg-[var(--color-mq-bg-secondary)] border border-[var(--color-mq-border)] rounded-[var(--radius-minimal)] px-2 h-8 text-[var(--font-size-small)] text-[var(--color-mq-text-primary)] font-mono"
          >
            <option value="ALL">All Quality</option>
            <option value="HIGH">High (≥99%)</option>
            <option value="MEDIUM">Medium (97-99%)</option>
            <option value="LOW">Low (&lt;97%)</option>
          </select>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-[var(--color-mq-bg-secondary)] border border-[var(--color-mq-border)] rounded-[var(--radius-minimal)] px-2 h-8 text-[var(--font-size-small)] text-[var(--color-mq-text-primary)] font-mono"
          >
            <option value="ALL">All Status ({mockDatasets.length})</option>
            <option value="FROZEN">Frozen ({statusCounts.FROZEN || 0})</option>
            <option value="BUILDING">Building ({statusCounts.BUILDING || 0})</option>
            <option value="VALIDATING">Validating ({statusCounts.VALIDATING || 0})</option>
            <option value="FAILED">Failed ({statusCounts.FAILED || 0})</option>
            <option value="ARCHIVED">Archived ({statusCounts.ARCHIVED || 0})</option>
          </select>
        </div>
        <MQButton>
          Create Dataset
        </MQButton>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <MQChartContainer title="Coverage Timeline" className="lg:col-span-1">
          <div className="h-[120px] flex items-end gap-1">
            {coverageTimeline.map((point, idx) => (
              <div key={idx} className="flex-1 flex flex-col items-center gap-1">
                <div
                  className="w-full bg-[var(--color-mq-accent)] rounded-t"
                  style={{ height: `${(point.datasets / 32) * 100}%` }}
                />
                <span className="text-[var(--font-size-caption)] text-[var(--color-mq-text-muted)] font-mono">
                  {point.month}
                </span>
              </div>
            ))}
          </div>
        </MQChartContainer>

        <MQChartContainer title="Missing Value Trend" className="lg:col-span-1">
          <div className="h-[120px] flex items-end gap-1">
            {missingValueTrend.map((point, idx) => (
              <div key={idx} className="flex-1 flex flex-col items-center gap-1">
                <div
                  className="w-full rounded-t"
                  style={{
                    height: `${(point.avg / 0.2) * 100}%`,
                    backgroundColor: point.avg < 0.1 ? 'var(--color-mq-success)' : point.avg < 0.15 ? 'var(--color-mq-warning)' : 'var(--color-mq-failure)'
                  }}
                />
                <span className="text-[var(--font-size-caption)] text-[var(--color-mq-text-muted)] font-mono">
                  {point.month}
                </span>
              </div>
            ))}
          </div>
        </MQChartContainer>

        <MQChartContainer title="Dataset Growth" className="lg:col-span-1">
          <div className="h-[120px] flex flex-col justify-center items-center gap-2">
            <TrendingUp size={32} className="text-[var(--color-mq-accent)]" />
            <div className="text-center">
              <div className="text-[var(--font-size-h3)] font-mono text-[var(--color-mq-text-primary)]">
                {mockDatasets.length}
              </div>
              <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)]">
                Total Datasets
              </div>
            </div>
          </div>
        </MQChartContainer>
      </div>

      <MQPanel title={`Datasets (${filteredDatasets.length})`}>
        <MQTable
          columns={[
            {
              key: 'name',
              header: 'Dataset Name',
              render: (row) => (
                <button
                  onClick={() => setSelectedDataset(row)}
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
              render: (row) => `v${row.version}`,
              width: 'w-[80px]'
            },
            {
              key: 'exchange',
              header: 'Exchange',
              render: (row) => row.exchange,
              width: 'w-[100px]'
            },
            {
              key: 'assetClass',
              header: 'Asset Class',
              render: (row) => row.assetClass,
              width: 'w-[100px]'
            },
            {
              key: 'timeframe',
              header: 'Timeframe',
              render: (row) => row.timeframe,
              width: 'w-[80px]'
            },
            {
              key: 'rows',
              header: 'Rows',
              align: 'right',
              render: (row) => row.rows.toLocaleString(),
              width: 'w-[100px]'
            },
            {
              key: 'features',
              header: 'Features',
              align: 'right',
              render: (row) => row.features,
              width: 'w-[80px]'
            },
            {
              key: 'missingPct',
              header: 'Missing %',
              align: 'right',
              render: (row) => (
                <span className={row.missingPct < 5 ? 'text-[var(--color-mq-success)]' : row.missingPct < 15 ? 'text-[var(--color-mq-warning)]' : 'text-[var(--color-mq-failure)]'}>
                  {row.missingPct.toFixed(2)}%
                </span>
              ),
              width: 'w-[90px]'
            },
            {
              key: 'qualityScore',
              header: 'Quality Score',
              align: 'right',
              render: (row) => (
                <span className={getQualityColor(row.qualityScore)}>
                  {row.qualityScore.toFixed(1)}%
                </span>
              ),
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
              width: 'w-[100px]'
            }
          ]}
          data={filteredDatasets}
          keyExtractor={(row) => row.id}
        />
      </MQPanel>

      {selectedDataset && (
        <DatasetInspector
          dataset={selectedDataset}
          onClose={() => setSelectedDataset(null)}
        />
      )}
    </div>
  );
}
