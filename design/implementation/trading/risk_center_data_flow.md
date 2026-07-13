# Risk Center Data Flow

## Flow Diagram
```
Historical Returns -> paper_analytics_service (Monte Carlo Simulator) -> FastAPI API -> Client dashboard
```

## Description
Historical returns are loaded by the service. The service simulates 1,000 futures trajectories to calculate VaR at 95% and 99%. Results are served to the frontend.

## Details
- **Source**: Raw events, API responses, or system metrics.
- **Transformation**: Data parsed, calculated, or grouped (e.g. by timeframe, sector, or fold).
- **Storage**: Persisted to SQLite (`trading.db` or `experiments` tables) or saved in active configuration files.
- **Caching**: React-query hook cache state on client or memory buffers on backend.
- **Consumers**: Frontend charts, grid visualizers, and monitor panels.
