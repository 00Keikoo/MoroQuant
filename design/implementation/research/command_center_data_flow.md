# Research Command Center Data Flow

## Flow Diagram
```
FastAPI Subprocess Manager -> Scheduler Engine -> Database Job State -> API -> Client telemetry
```

## Description
Triggering a job sends a POST request. The backend spawns a training script and monitors logs, updating status in real-time.

## Details
- **Source**: Raw events, API responses, or system metrics.
- **Transformation**: Data parsed, calculated, or grouped (e.g. by timeframe, sector, or fold).
- **Storage**: Persisted to SQLite (`trading.db` or `experiments` tables) or saved in active configuration files.
- **Caching**: React-query hook cache state on client or memory buffers on backend.
- **Consumers**: Frontend charts, grid visualizers, and monitor panels.
