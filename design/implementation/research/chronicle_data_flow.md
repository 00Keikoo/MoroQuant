# Research Chronicle Data Flow

## Flow Diagram
```
Job Step Event Ingestor -> SQLite (experiments database) -> API -> Chronicle Timeline
```

## Description
As pipelines run, they record steps. The chronicle fetches steps in chronological order and exposes step logs on click.

## Details
- **Source**: Raw events, API responses, or system metrics.
- **Transformation**: Data parsed, calculated, or grouped (e.g. by timeframe, sector, or fold).
- **Storage**: Persisted to SQLite (`trading.db` or `experiments` tables) or saved in active configuration files.
- **Caching**: React-query hook cache state on client or memory buffers on backend.
- **Consumers**: Frontend charts, grid visualizers, and monitor panels.
