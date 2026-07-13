# Scheduler Data Flow

## Flow Diagram
```
`ml_service/scheduler.py` (process/cron loops) -> status output -> FastAPI API -> Client DAG viewer
```

## Description
The scheduler process runs cron loops. The API queries its queue and active subprocess lists, serving a node state tree to the client.

## Details
- **Source**: Raw events, API responses, or system metrics.
- **Transformation**: Data parsed, calculated, or grouped (e.g. by timeframe, sector, or fold).
- **Storage**: Persisted to SQLite (`trading.db` or `experiments` tables) or saved in active configuration files.
- **Caching**: React-query hook cache state on client or memory buffers on backend.
- **Consumers**: Frontend charts, grid visualizers, and monitor panels.
