# Portfolio Data Flow

## Flow Diagram
```
Database -> equity_repository -> paper_analytics_service -> API -> Client allocation view
```

## Description
Positions are read from SQLite. Actual weights are computed from live valuations. Rebalance targets are posted, saved, and processed by the paper engine.

## Details
- **Source**: Raw events, API responses, or system metrics.
- **Transformation**: Data parsed, calculated, or grouped (e.g. by timeframe, sector, or fold).
- **Storage**: Persisted to SQLite (`trading.db` or `experiments` tables) or saved in active configuration files.
- **Caching**: React-query hook cache state on client or memory buffers on backend.
- **Consumers**: Frontend charts, grid visualizers, and monitor panels.
