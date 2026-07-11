import React from 'react';

interface MQTableColumn<T> {
  key: string;
  header: string;
  render: (row: T) => React.ReactNode;
  align?: 'left' | 'center' | 'right';
  width?: string;
}

interface MQTableProps<T> {
  columns: MQTableColumn<T>[];
  data: T[];
  keyExtractor: (row: T, index: number) => string | number;
  className?: string;
  compact?: boolean;
}

export function MQTable<T>({
  columns,
  data,
  keyExtractor,
  className = '',
  compact = false
}: MQTableProps<T>) {
  const rowHeight = compact ? 'h-[20px]' : 'h-[var(--row-height)]';

  return (
    <div className={`w-full overflow-auto ${className}`}>
      <table className="w-full border-collapse">
        <thead className="sticky top-0 bg-[var(--color-mq-bg-secondary)] border-b border-[var(--color-mq-border)]">
          <tr>
            {columns.map((column) => (
              <th
                key={column.key}
                className={`h-[var(--header-height)] px-2 text-[var(--font-size-caption)] font-medium text-[var(--color-mq-text-secondary)] text-${column.align || 'left'} ${column.width || ''}`}
              >
                {column.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, index) => (
            <tr
              key={keyExtractor(row, index)}
              className="border-b border-[var(--color-mq-border)] hover:bg-[var(--color-mq-accent-dim)] transition-colors"
            >
              {columns.map((column) => (
                <td
                  key={column.key}
                  className={`${rowHeight} px-2 text-[var(--font-size-small)] font-mono text-[var(--color-mq-text-primary)] text-${column.align || 'left'}`}
                >
                  {column.render(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
