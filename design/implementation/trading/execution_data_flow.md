# Execution Data Flow

## Flow Diagram
```
Exchange API / WebSocket -> execution_intelligence (latency & slippage math) -> FastAPI -> Frontend telemetry
```

## Description
Every order event is logged with microsecond timestamps. The execution service calculates round-trip latency and slippage, streaming the metrics to the frontend.

## Details
- **Source**: Raw events, API responses, or system metrics.
- **Transformation**: Data parsed, calculated, or grouped (e.g. by timeframe, sector, or fold).
- **Storage**: Persisted to SQLite (`trading.db` or `experiments` tables) or saved in active configuration files.
- **Caching**: React-query hook cache state on client or memory buffers on backend.
- **Consumers**: Frontend charts, grid visualizers, and monitor panels.
