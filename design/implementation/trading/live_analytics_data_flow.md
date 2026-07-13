# Live Analytics Data Flow

## Flow Diagram
```
SQLite (trades and equity) -> trade_repository & equity_repository -> paper_analytics_service -> API -> Frontend charts
```

## Description
The analytics service reads historic trade data, processes distributions, computes Sharpe/Sortino ratios, and returns them to the frontend for charting.

## Details
- **Source**: Raw events, API responses, or system metrics.
- **Transformation**: Data parsed, calculated, or grouped (e.g. by timeframe, sector, or fold).
- **Storage**: Persisted to SQLite (`trading.db` or `experiments` tables) or saved in active configuration files.
- **Caching**: React-query hook cache state on client or memory buffers on backend.
- **Consumers**: Frontend charts, grid visualizers, and monitor panels.
