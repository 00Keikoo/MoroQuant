# Trade Forensics Data Flow

## Flow Diagram
```
Filled trades -> entry timestamps -> database query -> point-in-time feature values -> Forensics API -> Client drilldown
```

## Description
Select a trade -> endpoint queries entry time -> extracts values of features from DB at that precise second -> shows feature state chart at order execution time.

## Details
- **Source**: Raw events, API responses, or system metrics.
- **Transformation**: Data parsed, calculated, or grouped (e.g. by timeframe, sector, or fold).
- **Storage**: Persisted to SQLite (`trading.db` or `experiments` tables) or saved in active configuration files.
- **Caching**: React-query hook cache state on client or memory buffers on backend.
- **Consumers**: Frontend charts, grid visualizers, and monitor panels.
