# Validation Contract
    
## Purpose
Purged walk-forward validation visualization, fold results, and training vs validation error analysis.

## Responsibilities
- **Frontend / Client**: Client displays walk-forward fold grids and validation loss curves. Backend computes purged fold metrics.
- **Backend / Server**: Manages database reads/writes, calculates aggregations, and serves JSON payloads via FastAPI.

## Widgets
- Purged Walk-Forward Fold grid (visualizing train/validation/purge zones)\n- Out-of-sample metrics per fold table\n- Loss decay chart

## Dependencies
- **UI Components**: MQDS Components
- **Libraries**: Recharts, lucide-react

## Required APIs
- GET `/api/validation/folds` (Returns fold structures and performance)\nGET `/api/validation/metrics` (Returns validation metrics)

## Repository Layer
- **Location**: `ml_service/repositories/`
- **Functions**: `experiment_repository.py` (saves model validation results)

## Service Layer
- **Location**: `ml_service/services/`
- **Classes**: `explorer_query_service.py` (retrieves cross-validation statistics)

## Analytics Layer
- **Location**: `ml_service/analytics/` or `ml_service/services/paper_analytics_service.py`
- **Features**: Performs math and data transformation for rendering.

## Frontend Components
- **Location**: `components/`
- **Files**: Reusable components matching Stitch design markers.

## Mock Status
- **Status**: PARTIAL

## Production Status
- **Status**: PARTIAL (walk-forward visual metadata needs structured endpoints)

## Future Integration Notes
Ensure mock JSON responses match the schema returned by the corresponding FastAPI endpoints. Map endpoint fields exactly to avoid breaking client charts.
