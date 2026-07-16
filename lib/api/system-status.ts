import { SystemStatusResponse } from '@/lib/types/system-status';

const API_BASE = typeof window !== 'undefined'
  ? `${process.env.NEXT_PUBLIC_API_URL || `http://${window.location.hostname}:8000`}/api`
  : 'http://localhost:8000/api';

export async function getSystemStatus(): Promise<SystemStatusResponse> {
  try {
    const response = await fetch(`${API_BASE}/system/status`, {
      signal: AbortSignal.timeout(5000),
    });

    if (!response.ok) {
      throw new Error(`Failed to fetch system status: ${response.statusText}`);
    }

    return response.json();
  } catch (error) {
    // Return UNKNOWN status if backend is unreachable
    return {
      api: 'UNKNOWN',
      db: 'UNKNOWN',
      scheduler: 'UNKNOWN',
      paper_broker: 'UNKNOWN',
      market_data: 'UNKNOWN',
      binance_ws: 'UNKNOWN',
      timestamp: new Date().toISOString(),
    };
  }
}
