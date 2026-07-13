# Datasets Data Flow

## Flow Diagram
```
SQLite / Parquet files -> Data Ingestion Validator -> DB Info -> API -> Client dataset catalog
```

## Description
The backend scans the database tables and folder storage. It builds a summary of records, timeframe limits, and validation status, serving it via `/api/db/info`.

## Details
- **Source**: Raw events, API responses, or system metrics.
- **Transformation**: Data parsed, calculated, or grouped (e.g. by timeframe, sector, or fold).
- **Storage**: Persisted to SQLite (`trading.db` or `experiments` tables) or saved in active configuration files.
- **Caching**: React-query hook cache state on client or memory buffers on backend.
- **Consumers**: Frontend charts, grid visualizers, and monitor panels.
