# ML Signals Data Flow

## Flow Diagram
```
Features Engine -> Model Inference -> signal_repository (trading.db) -> main.py (FastAPI) -> Next.js client
```

## Description
Scheduler triggers retraining or inference -> predictions saved in signal database -> API fetches signal details -> client updates active signals and features charts.

## Details
- **Source**: Raw events, API responses, or system metrics.
- **Transformation**: Data parsed, calculated, or grouped (e.g. by timeframe, sector, or fold).
- **Storage**: Persisted to SQLite (`trading.db` or `experiments` tables) or saved in active configuration files.
- **Caching**: React-query hook cache state on client or memory buffers on backend.
- **Consumers**: Frontend charts, grid visualizers, and monitor panels.
