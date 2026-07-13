# Feature Registry Data Flow

## Flow Diagram
```
Features Config (Python files) -> Feature Engine -> metadata extraction -> Feature Registry API -> Client
```

## Description
Features are defined in python files. A metadata parser extracts names and relationships, exposing them through `/api/features` to show Gini importances.

## Details
- **Source**: Raw events, API responses, or system metrics.
- **Transformation**: Data parsed, calculated, or grouped (e.g. by timeframe, sector, or fold).
- **Storage**: Persisted to SQLite (`trading.db` or `experiments` tables) or saved in active configuration files.
- **Caching**: React-query hook cache state on client or memory buffers on backend.
- **Consumers**: Frontend charts, grid visualizers, and monitor panels.
