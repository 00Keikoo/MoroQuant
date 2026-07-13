# Experiments Data Flow

## Flow Diagram
```
Optuna / MLflow -> Experiment DB -> experiment_repository -> experiment_service -> API -> Run comparison charts
```

## Description
Researchers run grid search/optimization. Results are saved in the experiments database. The API returns details for comparing configurations.

## Details
- **Source**: Raw events, API responses, or system metrics.
- **Transformation**: Data parsed, calculated, or grouped (e.g. by timeframe, sector, or fold).
- **Storage**: Persisted to SQLite (`trading.db` or `experiments` tables) or saved in active configuration files.
- **Caching**: React-query hook cache state on client or memory buffers on backend.
- **Consumers**: Frontend charts, grid visualizers, and monitor panels.
