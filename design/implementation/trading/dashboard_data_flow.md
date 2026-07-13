# Trading Dashboard Data Flow

## Flow Diagram
```
Binance / Paper Engine -> Exchange Sync -> SQLite (trading.db) -> equity_repository -> paper_analytics_service -> API -> Frontend
```

## Description
Real-time or polled price feeds update the portfolio value. The sync service stores daily equity snapshots in SQLite. The frontend pulls these snapshots to render the equity curve.

## Details
- **Source**: Raw events, API responses, or system metrics.
- **Transformation**: Data parsed, calculated, or grouped (e.g. by timeframe, sector, or fold).
- **Storage**: Persisted to SQLite (`trading.db` or `experiments` tables) or saved in active configuration files.
- **Caching**: React-query hook cache state on client or memory buffers on backend.
- **Consumers**: Frontend charts, grid visualizers, and monitor panels.
