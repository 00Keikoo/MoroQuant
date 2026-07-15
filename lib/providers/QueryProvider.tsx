'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState } from 'react';

export function QueryProvider({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            refetchOnWindowFocus: false,
            retry: (failureCount, error: any) => {
              // AbortError: no retry
              if (error?.name === 'AbortError' || error?.name === 'TimeoutError') {
                return false;
              }

              // 4xx responses: no retry
              if (error?.status >= 400 && error?.status < 500) {
                return false;
              }
              if (error?.message?.includes('Client error:')) {
                return false;
              }

              // Network errors: max 2 retries
              if (
                error?.message?.includes('Network') ||
                error?.message?.includes('fetch failed') ||
                error?.message?.includes('Failed to fetch') ||
                error instanceof TypeError
              ) {
                return failureCount < 2;
              }

              // Default: 1 retry
              return failureCount < 1;
            },
            retryDelay: (attemptIndex) => {
              // Exponential backoff: 1s, 2s, 4s (capped at 4s)
              return Math.min(1000 * Math.pow(2, attemptIndex), 4000);
            },
            staleTime: 30_000,
            networkMode: 'online',
          },
        },
      })
  );

  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}
