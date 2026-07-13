# Calibration Data Flow

## Flow Diagram
```
Signals + Outcomes DB -> Calibration calculator -> API bin coordinates -> Client reliability chart
```

## Description
The system maps signal confidence levels into probability bins (0-10%), checks what percentage of signals in each bin hit the profit target, and returns the points.

## Details
- **Source**: Raw events, API responses, or system metrics.
- **Transformation**: Data parsed, calculated, or grouped (e.g. by timeframe, sector, or fold).
- **Storage**: Persisted to SQLite (`trading.db` or `experiments` tables) or saved in active configuration files.
- **Caching**: React-query hook cache state on client or memory buffers on backend.
- **Consumers**: Frontend charts, grid visualizers, and monitor panels.
