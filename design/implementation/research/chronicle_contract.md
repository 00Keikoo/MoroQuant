# Research Chronicle Contract
    
## Purpose
GitHub Actions-style lifecycle timeline of experiments, validations, and promotions.

## Responsibilities
- **Frontend / Client**: Client renders timeline steps with logs inspector. Backend retrieves pipeline event history and steps logs.
- **Backend / Server**: Manages database reads/writes, calculates aggregations, and serves JSON payloads via FastAPI.

## Widgets
- Vertical timeline of model lifecycle events\n- Step detailed logs inspector side panel\n- Status icons (success, fail, running)

## Dependencies
- **UI Components**: MQDS Components
- **Libraries**: lucide-react, JetBrains Mono font

## Required APIs
- GET `/api/scheduler/chronicle` (Returns chronological pipeline run steps)

## Repository Layer
- **Location**: `ml_service/repositories/`
- **Functions**: `experiment_repository.py` (runs audit log)

## Service Layer
- **Location**: `ml_service/services/`
- **Classes**: `explorer_query_service.py` (aggregates runs)

## Analytics Layer
- **Location**: `ml_service/analytics/` or `ml_service/services/paper_analytics_service.py`
- **Features**: Performs math and data transformation for rendering.

## Frontend Components
- **Location**: `components/`
- **Files**: Reusable components matching Stitch design markers.

## Mock Status
- **Status**: PARTIAL

## Production Status
- **Status**: PARTIAL (historical log ingestion pipeline is basic)

## Future Integration Notes
Ensure mock JSON responses match the schema returned by the corresponding FastAPI endpoints. Map endpoint fields exactly to avoid breaking client charts.
