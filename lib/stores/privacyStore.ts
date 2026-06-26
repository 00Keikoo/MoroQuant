import { create } from 'zustand';
import { persist } from 'zustand/middleware';

/**
 * Global Privacy Mode state.
 *
 * When enabled, sensitive monetary values across the dashboard (balances,
 * PnL, prices, equity curves) are masked with "•••••" so the app is safe to
 * screen-share, screenshot, present, or stream. Non-sensitive analytics
 * (winrate, Sharpe, trade counts, regime, signals) remain visible.
 *
 * Persists across refreshes via localStorage (key: "moroquant-privacy-mode").
 * Matches the established Zustand store pattern used by the other four stores
 * in lib/stores/, with the addition of the `persist` middleware for survival
 * across reloads.
 */
interface PrivacyState {
  privacyMode: boolean;
  setPrivacyMode: (enabled: boolean) => void;
  togglePrivacyMode: () => void;
}

export const usePrivacyStore = create<PrivacyState>()(
  persist(
    (set) => ({
      privacyMode: false,
      setPrivacyMode: (enabled) => set({ privacyMode: enabled }),
      togglePrivacyMode: () => set((state) => ({ privacyMode: !state.privacyMode })),
    }),
    {
      name: 'moroquant-privacy-mode',
      // Only the boolean flag is persisted, never actions.
      partialize: (state) => ({ privacyMode: state.privacyMode }),
    },
  ),
);

/**
 * Minimal selector hook for components that only need the boolean flag.
 * Returns the primitive directly so components rerender only when the flag
 * flips — not on unrelated store changes.
 */
export function useIsPrivacyMode(): boolean {
  return usePrivacyStore((state) => state.privacyMode);
}

/**
 * Primary hook for the toggle UI and any consumer needing both the flag and
 * the toggle action. Matches the spec's PrivacyContextType API shape:
 *   { isPrivacyMode, togglePrivacyMode }
 */
export function usePrivacy() {
  const isPrivacyMode = usePrivacyStore((state) => state.privacyMode);
  const togglePrivacyMode = usePrivacyStore((state) => state.togglePrivacyMode);
  return { isPrivacyMode, togglePrivacyMode };
}
