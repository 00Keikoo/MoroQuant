# Monitoring Data Flow

## Flow Diagram
```
Connection check loop -> SQLite + Redis + Binance ping status -> Monitoring API -> Client health panel
```

## Description
A cron periodically checks DB connections, Binance API latency, and disk space. The frontend queries the aggregated state to light up indicators.

## Details
- **Source**: Raw events, API responses, or system metrics.
- **Transformation**: Data parsed, calculated, or grouped (e.g. by timeframe, sector, or fold).
- **Storage**: Persisted to SQLite (`trading.db` or `experiments` tables) or saved in active configuration files.
- **Caching**: React-query hook cache state on client or memory buffers on backend.
- **Consumers**: Frontend charts, grid visualizers, and monitor panels.
