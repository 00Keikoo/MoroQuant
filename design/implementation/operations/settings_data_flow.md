# Settings Data Flow

## Flow Diagram
```
`ml_service/config.yaml` -> Configuration Manager -> Settings API -> Client settings form
```

## Description
Settings are loaded from `config.yaml` on the backend. When the user edits and clicks save, the parameters are validated and written back to the file.

## Details
- **Source**: Raw events, API responses, or system metrics.
- **Transformation**: Data parsed, calculated, or grouped (e.g. by timeframe, sector, or fold).
- **Storage**: Persisted to SQLite (`trading.db` or `experiments` tables) or saved in active configuration files.
- **Caching**: React-query hook cache state on client or memory buffers on backend.
- **Consumers**: Frontend charts, grid visualizers, and monitor panels.
