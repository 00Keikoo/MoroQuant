# Logs Data Flow

## Flow Diagram
```
Log files (backtest.log, retrain.log) -> File Tail Service -> API logs endpoint -> Client console
```

## Description
The frontend opens a WebSocket or tails the endpoint. The backend reads log paths, filters text, and returns lines dynamically.

## Details
- **Source**: Raw events, API responses, or system metrics.
- **Transformation**: Data parsed, calculated, or grouped (e.g. by timeframe, sector, or fold).
- **Storage**: Persisted to SQLite (`trading.db` or `experiments` tables) or saved in active configuration files.
- **Caching**: React-query hook cache state on client or memory buffers on backend.
- **Consumers**: Frontend charts, grid visualizers, and monitor panels.
