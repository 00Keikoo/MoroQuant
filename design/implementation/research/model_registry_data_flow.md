# Model Registry Data Flow

## Flow Diagram
```
`active_models.json` & `production_model_audit_results.json` -> Model API -> Client Registry table
```

## Description
Models are created during training. They register in the catalog. The API exposes them and allows setting deployment flags (Active vs Shadow).

## Details
- **Source**: Raw events, API responses, or system metrics.
- **Transformation**: Data parsed, calculated, or grouped (e.g. by timeframe, sector, or fold).
- **Storage**: Persisted to SQLite (`trading.db` or `experiments` tables) or saved in active configuration files.
- **Caching**: React-query hook cache state on client or memory buffers on backend.
- **Consumers**: Frontend charts, grid visualizers, and monitor panels.
