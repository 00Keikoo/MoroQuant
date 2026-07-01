import type { TradingMode } from '@/lib/types/ml';
import type { TradingDataProvider } from './types';
import { LiveProvider } from './liveProvider';
import { PaperProvider } from './paperProvider';

export function getDataProvider(mode: TradingMode | null): TradingDataProvider {
  if (mode === 'PAPER') {
    return new PaperProvider();
  }
  return new LiveProvider();
}

export type { TradingDataProvider };
export * from './types';
