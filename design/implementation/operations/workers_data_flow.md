# Workers Data Flow

## Flow Diagram
```
System metrics library (psutil / GPUtil) -> host stats collector -> API endpoint -> Client hardware metrics
```

## Description
FastAPI runs system queries (RAM, CPU, GPUtil loads). It formats them into metrics and serves them to the frontend to draw gauge charts.

## Details
- **Source**: Raw events, API responses, or system metrics.
- **Transformation**: Data parsed, calculated, or grouped (e.g. by timeframe, sector, or fold).
- **Storage**: Persisted to SQLite (`trading.db` or `experiments` tables) or saved in active configuration files.
- **Caching**: React-query hook cache state on client or memory buffers on backend.
- **Consumers**: Frontend charts, grid visualizers, and monitor panels.
