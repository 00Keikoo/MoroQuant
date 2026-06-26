'use client';

import React from 'react';
import { useIsPrivacyMode } from '@/lib/stores/privacyStore';
import { MASK_MONETARY, EMPTY } from '@/lib/format/privacy';

export interface SensitiveValueProps {
  /** Raw value to render. If a formatter is given, this is passed to it. */
  value?: number | string | null;
  /** Optional formatter applied to `value` before display (privacy OFF only). */
  formatter?: (value: number | string) => string;
  /** Mask shown when Privacy Mode is ON. Defaults to "•••••". */
  mask?: string;
  /** Text shown when `value` is null/undefined (any mode). Defaults to "—". */
  emptyText?: string;
  /** Optional className applied to the rendered span. */
  className?: string;
  /**
   * Optional inline children for privacy-aware rendering. When provided and
   * Privacy Mode is OFF, children render instead of `value`/`formatter`.
   * When Privacy Mode is ON, the mask renders and children are ignored.
   */
  children?: React.ReactNode;
}

/**
 * Render a sensitive value that respects global Privacy Mode.
 *
 * - Privacy OFF → renders `formatter(value)` (or `value`, or `children`).
 * - Privacy ON  → renders the `mask` ("•••••" by default).
 * - Missing value (null/undefined) → renders `emptyText` ("—" by default).
 *
 * Subscribes to the privacy store via a primitive selector so only the flag
 * flip triggers a rerender, not unrelated store updates. Use freely in tables,
 * KPI cards, tooltips, and anywhere a single value needs masking.
 *
 * @example
 * <SensitiveValue value={equity} formatter={(v) => `$${Number(v).toFixed(2)}`} />
 */
export default function SensitiveValue({
  value,
  formatter,
  mask = MASK_MONETARY,
  emptyText = EMPTY,
  className,
  children,
}: SensitiveValueProps) {
  const privacy = useIsPrivacyMode();

  if (value === null || value === undefined) {
    return <span className={className}>{emptyText}</span>;
  }

  if (privacy) {
    return <span className={className}>{mask}</span>;
  }

  if (children !== undefined && children !== null) {
    return <span className={className}>{children}</span>;
  }

  const rendered = formatter ? formatter(value) : String(value);
  return <span className={className}>{rendered}</span>;
}
