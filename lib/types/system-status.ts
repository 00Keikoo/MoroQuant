export type SystemComponentStatus =
  | 'RUNNING'
  | 'STOPPED'
  | 'CONNECTED'
  | 'DISCONNECTED'
  | 'HEALTHY'
  | 'DOWN'
  | 'UNKNOWN';

export interface SystemComponent {
  component: string;
  status: SystemComponentStatus;
  latency_ms?: number;
  last_update?: string;
  message?: string;
}

export interface SystemStatusResponse {
  api: SystemComponentStatus;
  db: SystemComponentStatus;
  scheduler: SystemComponentStatus;
  paper_broker: SystemComponentStatus;
  market_data: SystemComponentStatus;
  binance_ws?: SystemComponentStatus;
  latency_ms?: number;
  last_candle?: string;
  timestamp: string;
}
