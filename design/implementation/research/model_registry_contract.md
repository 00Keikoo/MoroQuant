# Model Registry Contract
    
## Purpose
Model governance, active deployment flags, validation audit logs, and status tracker.

## Responsibilities
- **Frontend / Client**: Client lists model registry database, details active models, and triggers promotions. Backend stores active model configs.
- **Backend / Server**: Manages database reads/writes, calculates aggregations, and serves JSON payloads via FastAPI.

## Widgets
- Registered Models list with tags (Production, Shadow, Sandbox)\n- Active models status cards\n- Model compatibility validation report

## Dependencies
- **UI Components**: MQDS Components
- **Libraries**: lucide-react

## Required APIs
- GET `/api/models` (Returns registered models)\nPOST `/api/models/{id}/status` (Updates active/inactive flags)

## Repository Layer
- **Location**: `ml_service/repositories/`
- **Functions**: `experiment_repository.py` (saves model registration state)

## Service Layer
- **Location**: `ml_service/services/`
- **Classes**: `explorer_query_service.py` (validates model state)

## Analytics Layer
- **Location**: `ml_service/analytics/` or `ml_service/services/paper_analytics_service.py`
- **Features**: Performs math and data transformation for rendering.

## Frontend Components
- **Location**: `components/`
- **Files**: Reusable components matching Stitch design markers.

## Mock Status
- **Status**: READY

## Production Status
- **Status**: READY

## Future Integration Notes
Ensure mock JSON responses match the schema returned by the corresponding FastAPI endpoints. Map endpoint fields exactly to avoid breaking client charts.
