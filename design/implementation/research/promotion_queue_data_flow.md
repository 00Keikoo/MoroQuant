# Promotion Queue Data Flow

## Flow Diagram
```
`active_compatibility_check.json` -> promotion workflow checks -> API -> Frontend queue
```

## Description
A model is promoted. The backend triggers compatibility checks (e.g. `check_active_compatibility.py`) and returns results to update the visual checklist.

## Details
- **Source**: Raw events, API responses, or system metrics.
- **Transformation**: Data parsed, calculated, or grouped (e.g. by timeframe, sector, or fold).
- **Storage**: Persisted to SQLite (`trading.db` or `experiments` tables) or saved in active configuration files.
- **Caching**: React-query hook cache state on client or memory buffers on backend.
- **Consumers**: Frontend charts, grid visualizers, and monitor panels.
