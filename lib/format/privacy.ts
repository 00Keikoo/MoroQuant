/**
 * Privacy Mode masking helpers.
 *
 * Pure functions (no React, no hooks) so they can be called inside render
 * expressions, table-cell formatters, and `useMemo` blocks without extra
 * component overhead. Pair with `useIsPrivacyMode()` from the privacy store
 * at the top of a component:
 *
 *   const privacy = useIsPrivacyMode();
 *   const value = maskOr(fmtUsd(equity), MASK_MONETARY, privacy);
 *
 * `maskOr` returns the original formatted string when privacy is OFF, the
 * mask string when ON, and `emptyText` ("—" by default) for null/undefined
 * input regardless of mode — mirroring how the dashboard already treats
 * missing values.
 */

/** Default mask for monetary / PnL values (e.g. balances, net PnL, fees). */
export const MASK_MONETARY = '•••••';

/** Mask for percentage-style values (e.g. ROI %, PnL %). */
export const MASK_PERCENT = '•••%';

/** Mask for price-style values (entry/exit/mark). */
export const MASK_PRICE = '••••';

/** Mask for chart Y-axis ticks. */
export const MASK_AXIS = '•••';

/** Empty-value placeholder, consistent with existing dashboard rendering. */
export const EMPTY = '—';

/**
 * Return `value` when privacy is off, `mask` when on, and `emptyText` when
 * the input is null/undefined/empty (in any mode).
 */
export function maskOr(
  value: string | number | null | undefined,
  mask: string = MASK_MONETARY,
  privacy: boolean,
  emptyText: string = EMPTY,
): string {
  if (value === null || value === undefined || value === '') {
    return emptyText;
  }
  return privacy ? mask : String(value);
}
