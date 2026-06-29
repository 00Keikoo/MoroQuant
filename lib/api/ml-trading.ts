import { MLSignal, MLSymbolsResponse, MLDbInfo, BacktestResults, ClosedTrade, TradeHistoryResponse, TradingModeResponse, TradingModeUpdate, PaperAccount, PaperPosition, PaperPortfolioSummary } from '@/lib/types/ml';

const ML_API_BASE = typeof window !== 'undefined' ? `http://${window.location.hostname}:8000/api` : 'http://localhost:8000/api';

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
      signal: AbortSignal.timeout(45000),
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

    const data = await response.json();

    if (data.error === 'no_data') {
      return {
        symbol,
        timeframe,
        equity_curve: [],
        trades: [],
        trade_count: 0,
        error: 'no_data',
        message: data.message,
      } as BacktestResults;
    }

    return data;
  } catch (error) {
    if (error instanceof TypeError && error.message.includes('fetch')) {
      throw new Error('ML API is offline. Please start the FastAPI server on port 8000.');
    }
    throw error;
  }
}

export async function getAllBacktestResults(symbols: string[], timeframe: string): Promise<BacktestResults[]> {
  const results = await Promise.all(
    symbols.map(async (symbol) => {
      try {
        return await getBacktestResults(symbol, timeframe);
      } catch (error) {
        return {
          symbol,
          timeframe,
          equity_curve: [],
          trades: [],
          trade_count: 0,
          error: 'Failed to load',
        } as BacktestResults;
      }
    })
  );
  return results;
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

// ── Trading Mode Manager ──────────────────────────────────────────────

export async function getTradingMode(): Promise<TradingModeResponse> {
  try {
    const response = await fetch(`${ML_API_BASE}/trading/mode`, {
      signal: AbortSignal.timeout(10000),
    });

    if (!response.ok) {
      throw new Error(`Failed to fetch trading mode: ${response.statusText}`);
    }

    return response.json();
  } catch (error) {
    if (error instanceof TypeError && error.message.includes('fetch')) {
      throw new Error('ML API is offline.');
    }
    throw error;
  }
}

export async function setTradingMode(mode: string): Promise<TradingModeUpdate> {
  try {
    const response = await fetch(`${ML_API_BASE}/trading/mode`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode }),
      signal: AbortSignal.timeout(10000),
    });

    if (!response.ok) {
      throw new Error(`Failed to set trading mode: ${response.statusText}`);
    }

    return response.json();
  } catch (error) {
    if (error instanceof TypeError && error.message.includes('fetch')) {
      throw new Error('ML API is offline.');
    }
    throw error;
  }
}

export async function emergencyStop(): Promise<TradingModeUpdate> {
  try {
    const response = await fetch(`${ML_API_BASE}/trading/emergency-stop`, {
      method: 'POST',
      signal: AbortSignal.timeout(10000),
    });

    if (!response.ok) {
      throw new Error(`Failed to execute emergency stop: ${response.statusText}`);
    }

    return response.json();
  } catch (error) {
    if (error instanceof TypeError && error.message.includes('fetch')) {
      throw new Error('ML API is offline.');
    }
    throw error;
  }
}

// ── Paper Broker ──────────────────────────────────────────────────────

export async function getPaperAccount(): Promise<PaperAccount> {
  try {
    const response = await fetch(`${ML_API_BASE}/paper/account`, {
      signal: AbortSignal.timeout(10000),
    });
    if (!response.ok) throw new Error(`Failed to fetch paper account: ${response.statusText}`);
    const data = await response.json();
    return data.account;
  } catch (error) {
    if (error instanceof TypeError && error.message.includes('fetch')) {
      throw new Error('ML API is offline.');
    }
    throw error;
  }
}

export async function getPaperOpenPositions(): Promise<PaperPosition[]> {
  try {
    const response = await fetch(`${ML_API_BASE}/paper/positions/open`, {
      signal: AbortSignal.timeout(10000),
    });
    if (!response.ok) throw new Error(`Failed to fetch open positions: ${response.statusText}`);
    const data = await response.json();
    return data.positions || [];
  } catch (error) {
    if (error instanceof TypeError && error.message.includes('fetch')) {
      throw new Error('ML API is offline.');
    }
    throw error;
  }
}

export async function getPaperClosedPositions(limit = 100): Promise<PaperPosition[]> {
  try {
    const response = await fetch(`${ML_API_BASE}/paper/positions/closed?limit=${limit}`, {
      signal: AbortSignal.timeout(10000),
    });
    if (!response.ok) throw new Error(`Failed to fetch closed positions: ${response.statusText}`);
    const data = await response.json();
    return data.positions || [];
  } catch (error) {
    if (error instanceof TypeError && error.message.includes('fetch')) {
      throw new Error('ML API is offline.');
    }
    throw error;
  }
}

export async function getPaperSummary(): Promise<PaperPortfolioSummary> {
  try {
    const response = await fetch(`${ML_API_BASE}/paper/summary`, {
      signal: AbortSignal.timeout(10000),
    });
    if (!response.ok) throw new Error(`Failed to fetch paper summary: ${response.statusText}`);
    return response.json();
  } catch (error) {
    if (error instanceof TypeError && error.message.includes('fetch')) {
      throw new Error('ML API is offline.');
    }
    throw error;
  }
}
