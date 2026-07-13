# Monitoring Contract
    
## Purpose
System-wide alerts, heartbeat triggers, database size limits, and exchange connection checks.

## Responsibilities
- **Frontend / Client**: Client renders warning alerts and connection heartbeats. Backend checks network APIs and database sizes.
- **Backend / Server**: Manages database reads/writes, calculates aggregations, and serves JSON payloads via FastAPI.

## Widgets
- Connection heartbeat grid\n- Unresolved alerts table\n- DB size limit warning progress bar

## Dependencies
- **UI Components**: MQDS Components
- **Libraries**: lucide-react

## Required APIs
- GET `/api/monitoring/heartbeat` (Returns API and DB status ping results)

## Repository Layer
- **Location**: `ml_service/repositories/`
- **Functions**: None

## Service Layer
- **Location**: `ml_service/services/`
- **Classes**: `explorer_query_service.py` (performs connection checks and pings)

## Analytics Layer
- **Location**: `ml_service/analytics/` or `ml_service/services/paper_analytics_service.py`
- **Features**: Performs math and data transformation for rendering.

## Frontend Components
- **Location**: `components/`
- **Files**: Reusable components matching Stitch design markers.

## Mock Status
- **Status**: PARTIAL

## Production Status
- **Status**: PARTIAL (heartbeat checks need automation)

## Future Integration Notes
Ensure mock JSON responses match the schema returned by the corresponding FastAPI endpoints. Map endpoint fields exactly to avoid breaking client charts.
