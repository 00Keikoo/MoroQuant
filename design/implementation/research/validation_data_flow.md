# Validation Data Flow

## Flow Diagram
```
Cross Validation Engine -> validation_results.json -> API -> Walk-forward visualizers
```

## Description
Validation engine splits historical data into purged walk-forward folds. It runs evaluations and generates validation JSONs, parsed by API and rendered on the client.

## Details
- **Source**: Raw events, API responses, or system metrics.
- **Transformation**: Data parsed, calculated, or grouped (e.g. by timeframe, sector, or fold).
- **Storage**: Persisted to SQLite (`trading.db` or `experiments` tables) or saved in active configuration files.
- **Caching**: React-query hook cache state on client or memory buffers on backend.
- **Consumers**: Frontend charts, grid visualizers, and monitor panels.
