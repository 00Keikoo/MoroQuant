/**
 * Global refresh hook for invalidating all dashboard queries simultaneously.
 * Provides centralized refresh control across all widgets.
 */

import { useQueryClient } from '@tanstack/react-query';
import { performanceKeys } from './usePerformanceData';

export function useGlobalRefresh() {
  const queryClient = useQueryClient();

  const refreshAll = () => {
    // Invalidate all performance queries at once
    queryClient.invalidateQueries({ queryKey: performanceKeys.all });
  };

  return { refreshAll };
}
