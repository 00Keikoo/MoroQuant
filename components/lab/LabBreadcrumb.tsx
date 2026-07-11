'use client';

import React from 'react';
import Link from 'next/link';
import { ChevronRight } from 'lucide-react';

export interface BreadcrumbItem {
  label: string;
  href?: string;
}

interface LabBreadcrumbProps {
  items: BreadcrumbItem[];
  className?: string;
}

export function LabBreadcrumb({ items, className = '' }: LabBreadcrumbProps) {
  return (
    <nav aria-label="Breadcrumb" className={`flex items-center gap-1 ${className}`}>
      {items.map((item, index) => (
        <React.Fragment key={index}>
          {index > 0 && (
            <ChevronRight
              size={14}
              className="text-[var(--color-mq-text-muted)]"
            />
          )}
          {item.href ? (
            <Link
              href={item.href}
              className="text-[var(--font-size-small)] text-[var(--color-mq-text-secondary)] hover:text-[var(--color-mq-accent)] transition-colors"
            >
              {item.label}
            </Link>
          ) : (
            <span className="text-[var(--font-size-small)] text-[var(--color-mq-text-primary)]">
              {item.label}
            </span>
          )}
        </React.Fragment>
      ))}
    </nav>
  );
}
