import { ReactNode } from 'react';

interface Column {
  header: string;
  align?: 'left' | 'right';
  className?: string;
}

interface DataTableProps {
  title?: string;
  columns: Column[];
  children: ReactNode;
  className?: string;
}

export function DataTable({ title, columns, children, className = '' }: DataTableProps) {
  return (
    <div className={`bg-surface-dim border border-outline-variant ${className}`}>
      {title && (
        <div className="px-4 py-2 border-b border-outline-variant bg-surface-container-low">
          <span className="font-mono-label text-mono-label text-on-surface uppercase">{title}</span>
        </div>
      )}
      <table className="w-full">
        <thead className="bg-surface-container-low border-b border-outline-variant">
          <tr>
            {columns.map((col, idx) => (
              <th
                key={idx}
                className={`px-3 py-2 font-mono-label text-mono-label text-on-surface-variant ${
                  col.align === 'right' ? 'text-right' : 'text-left'
                } ${col.className || ''}`}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {children}
        </tbody>
      </table>
    </div>
  );
}
