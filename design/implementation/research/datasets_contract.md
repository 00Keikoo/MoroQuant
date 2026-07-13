# Datasets Contract
    
## Purpose
Catalog of versioned datasets, data integrity checks, data lineage, and OHLCV counts.

## Responsibilities
- **Frontend / Client**: Client displays data health summaries, version tags, and data lineage graphs. Backend checks files and validates timestamps.
- **Backend / Server**: Manages database reads/writes, calculates aggregations, and serves JSON payloads via FastAPI.

## Widgets
- Datasets list with size, rows, and timeframe details\n- Data integrity alerts (missing candles, NaN counts)\n- Database records distribution chart

## Dependencies
- **UI Components**: MQDS Components
- **Libraries**: Recharts, lucide-react

## Required APIs
- GET `/api/db/info` (Returns database records and OHLCV statistics)\nGET `/api/datasets` (Returns dataset catalog and integrity report)

## Repository Layer
- **Location**: `ml_service/repositories/`
- **Functions**: `signal_repository.py` (tracks available market data ranges)

## Service Layer
- **Location**: `ml_service/services/`
- **Classes**: `explorer_query_service.py` (scans parquet and database sizes)

## Analytics Layer
- **Location**: `ml_service/analytics/` or `ml_service/services/paper_analytics_service.py`
- **Features**: Performs math and data transformation for rendering.

## Frontend Components
- **Location**: `components/`
- **Files**: Reusable components matching Stitch design markers.

## Mock Status
- **Status**: READY

## Production Status
- **Status**: PARTIAL (data integrity health reports need complete cron wiring)

## Future Integration Notes
Ensure mock JSON responses match the schema returned by the corresponding FastAPI endpoints. Map endpoint fields exactly to avoid breaking client charts.
