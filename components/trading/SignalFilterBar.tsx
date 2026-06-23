'use client';

import { Search, ArrowUpDown } from 'lucide-react';

export type DirectionFilter = 'all' | 'long' | 'short' | 'neutral';
export type SortField = 'symbol' | 'confidence' | 'direction';
export type SortOrder = 'asc' | 'desc';

interface SignalFilterBarProps {
  direction: DirectionFilter;
  onDirectionChange: (d: DirectionFilter) => void;
  minConfidence: number;
  onMinConfidenceChange: (v: number) => void;
  search: string;
  onSearchChange: (v: string) => void;
  sortField: SortField;
  sortOrder: SortOrder;
  onSortChange: (field: SortField) => void;
}

export default function SignalFilterBar({
  direction,
  onDirectionChange,
  minConfidence,
  onMinConfidenceChange,
  search,
  onSearchChange,
  sortField,
  sortOrder,
  onSortChange,
}: SignalFilterBarProps) {
  const directions: { value: DirectionFilter; label: string }[] = [
    { value: 'all', label: 'All' },
    { value: 'long', label: 'Long' },
    { value: 'short', label: 'Short' },
    { value: 'neutral', label: 'Neutral' },
  ];

  const toggleSort = () => {
    onSortChange(sortField === 'confidence' && sortOrder === 'desc' ? 'symbol' : 'confidence');
  };

  const isConfidenceSort = sortField === 'confidence';
  const sortLabel = isConfidenceSort ? `Confidence ${sortOrder === 'desc' ? '↓' : '↑'}` : 'Sort by Confidence';

  return (
    <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 p-3 bg-gray-900/50 backdrop-blur-sm border border-gray-800 rounded-xl">
      {/* Search */}
      <div className="relative flex-1 min-w-0">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
        <input
          type="text"
          value={search}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder="Search symbol..."
          className="w-full pl-9 pr-3 py-2 bg-gray-800/50 border border-gray-700 rounded-lg text-sm text-white placeholder-gray-500 focus:outline-none focus:border-mq-accent/50 transition-colors"
        />
      </div>

      {/* Direction filter pills */}
      <div className="flex items-center gap-1.5 shrink-0">
        {directions.map(({ value, label }) => (
          <button
            key={value}
            onClick={() => onDirectionChange(value)}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all duration-200 ${
              direction === value
                ? value === 'long'
                  ? 'bg-mq-long/20 text-mq-long border border-mq-long/40'
                  : value === 'short'
                  ? 'bg-mq-short/20 text-mq-short border border-mq-short/40'
                  : value === 'neutral'
                  ? 'bg-gray-600/20 text-gray-300 border border-gray-500/40'
                  : 'bg-mq-accent/20 text-mq-accent border border-mq-accent/40'
                : 'bg-gray-800/50 text-gray-400 border border-gray-700/50 hover:bg-gray-700/50'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Confidence slider */}
      <div className="flex items-center gap-2 shrink-0">
        <label className="text-xs text-gray-400 whitespace-nowrap">Min Conf ≥{minConfidence}</label>
        <input
          type="range"
          min={0}
          max={100}
          step={5}
          value={minConfidence}
          onChange={(e) => onMinConfidenceChange(Number(e.target.value))}
          className="w-24 accent-cyan-400 h-1"
        />
      </div>

      {/* Sort toggle */}
      <button
        onClick={toggleSort}
        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all duration-200 shrink-0 ${
          isConfidenceSort
            ? 'bg-mq-accent/20 text-mq-accent border border-mq-accent/40'
            : 'bg-gray-800/50 text-gray-400 border border-gray-700/50 hover:bg-gray-700/50'
        }`}
      >
        <ArrowUpDown className="w-3 h-3" />
        {sortLabel}
      </button>
    </div>
  );
}
