# Experiments Contract
    
## Purpose
Compares hyperparameters, validation metrics, and performance coefficients across experiment runs.

## Responsibilities
- **Frontend / Client**: Client shows multi-run comparison tables and correlation charts. Backend stores and retrieves hyperparameter parameters.
- **Backend / Server**: Manages database reads/writes, calculates aggregations, and serves JSON payloads via FastAPI.

## Widgets
- Runs comparison table with sorting/filtering\n- Hyperparameter parallel coordinates plot\n- Model metrics radar/scatter charts

## Dependencies
- **UI Components**: MQDS Components
- **Libraries**: Recharts, lucide-react

## Required APIs
- GET `/api/experiments` (Returns experiment runs and metrics)\nGET `/api/experiments/{id}` (Returns single experiment details)

## Repository Layer
- **Location**: `ml_service/repositories/`
- **Functions**: `experiment_repository.py` (saves runs, parameters, and validation metrics)

## Service Layer
- **Location**: `ml_service/services/`
- **Classes**: `experiment_service.py` (metrics comparisons)

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
