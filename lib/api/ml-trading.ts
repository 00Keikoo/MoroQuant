import { MLSignal, MLSymbolsResponse, MLDbInfo, BacktestResults, ClosedTrade, TradeHistoryResponse } from '@/lib/types/ml';

const ML_API_BASE = 'http://localhost:8000/api';

export const SYMBOL_DISPLAY = {
  'ES_proxy': { name: 'SPY', description: 'S&P 500 ETF (ES Futures Proxy)' },
  'NQ_proxy': { name: 'QQQ', description: 'Nasdaq 100 ETF (NQ Futures Proxy)' },
  'GC_proxy': { name: 'GLD', description: 'Gold ETF (GC Futures Proxy)' },
  'CL_proxy': { name: 'USO', description: 'Crude Oil ETF (CL Futures Proxy)' },
  'ZB_proxy': { name: 'TLT', description: '20yr Bond ETF (ZB Futures Proxy)' },
} as const;

export function getDisplayName(symbol: string): string {
  return SYMBOL_DISPLAY[symbol as keyof typeof SYMBOL_DISPLAY]?.name || symbol;
}

export function getDisplayDescription(symbol: string): string | null {
  return SYMBOL_DISPLAY[symbol as keyof typeof SYMBOL_DISPLAY]?.description || null;
}

export async function getSignal(symbol: string, timeframe: string): Promise<MLSignal> {
  try {
    const response = await fetch(`${ML_API_BASE}/signals?symbol=${symbol}&timeframe=${timeframe}`, {
      signal: AbortSignal.timeout(30000),
    });

    if (!response.ok) {
      throw new Error(`Failed to fetch signal: ${response.statusText}`);
    }

    return response.json();
  } catch (error) {
    if (error instanceof TypeError && error.message.includes('fetch')) {
      throw new Error('ML API is offline. Please start the FastAPI server on port 8000.');
    }
    throw error;
  }
}

export async function getSymbols(): Promise<MLSymbolsResponse> {
  try {
    const response = await fetch(`${ML_API_BASE}/symbols`, {
      signal: AbortSignal.timeout(30000),
    });

    if (!response.ok) {
      throw new Error(`Failed to fetch symbols: ${response.statusText}`);
    }

    return response.json();
  } catch (error) {
    if (error instanceof TypeError && error.message.includes('fetch')) {
      throw new Error('ML API is offline. Please start the FastAPI server on port 8000.');
    }
    throw error;
  }
}

export async function getDbInfo(): Promise<MLDbInfo> {
  try {
    const response = await fetch(`${ML_API_BASE}/db/info`, {
      signal: AbortSignal.timeout(30000),
    });

    if (!response.ok) {
      throw new Error(`Failed to fetch DB info: ${response.statusText}`);
    }

    return response.json();
  } catch (error) {
    if (error instanceof TypeError && error.message.includes('fetch')) {
      throw new Error('ML API is offline. Please start the FastAPI server on port 8000.');
    }
    throw error;
  }
}

export async function getBacktestResults(symbol: string, timeframe: string): Promise<BacktestResults> {
  try {
    const response = await fetch(`${ML_API_BASE}/backtest/${symbol}/${timeframe}`, {
      signal: AbortSignal.timeout(60000),
    });

    if (!response.ok) {
      throw new Error(`Failed to fetch backtest results: ${response.statusText}`);
    }

    return response.json();
  } catch (error) {
    if (error instanceof TypeError && error.message.includes('fetch')) {
      throw new Error('ML API is offline. Please start the FastAPI server on port 8000.');
    }
    throw error;
  }
}

export async function closeTrade(trade: ClosedTrade): Promise<{ status: string; message: string; trade_id: number }> {
  try {
    const response = await fetch(`${ML_API_BASE}/trades/close`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(trade),
      signal: AbortSignal.timeout(30000),
    });

    if (!response.ok) {
      throw new Error(`Failed to close trade: ${response.statusText}`);
    }

    return response.json();
  } catch (error) {
    if (error instanceof TypeError && error.message.includes('fetch')) {
      throw new Error('ML API is offline. Please start the FastAPI server on port 8000.');
    }
    throw error;
  }
}

export async function getTradeHistory(): Promise<TradeHistoryResponse> {
  try {
    const response = await fetch(`${ML_API_BASE}/trades/history`, {
      signal: AbortSignal.timeout(30000),
    });

    if (!response.ok) {
      throw new Error(`Failed to fetch trade history: ${response.statusText}`);
    }

    return response.json();
  } catch (error) {
    if (error instanceof TypeError && error.message.includes('fetch')) {
      throw new Error('ML API is offline. Please start the FastAPI server on port 8000.');
    }
    throw error;
  }
}
