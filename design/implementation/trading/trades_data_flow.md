# Trades Data Flow

## Flow Diagram
```
Order Execution System -> SQLite (trading.db) -> trade_repository -> paper_analytics_service -> API -> Frontend
```

## Description
Execution service writes filled orders to the database. The frontend queries the trade history API to render open positions and the transaction ledger.

## Details
- **Source**: Raw events, API responses, or system metrics.
- **Transformation**: Data parsed, calculated, or grouped (e.g. by timeframe, sector, or fold).
- **Storage**: Persisted to SQLite (`trading.db` or `experiments` tables) or saved in active configuration files.
- **Caching**: React-query hook cache state on client or memory buffers on backend.
- **Consumers**: Frontend charts, grid visualizers, and monitor panels.
