# Feature Registry Contract
    
## Purpose
Registry of calculated features, dependency trees, and feature importances (Gini/SHAP values).

## Responsibilities
- **Frontend / Client**: Client lists registered features and renders dependency trees. Backend runs feature analysis and dependency mapping.
- **Backend / Server**: Manages database reads/writes, calculates aggregations, and serves JSON payloads via FastAPI.

## Widgets
- Feature catalog table (name, category, source, status)\n- Feature importance bar chart\n- Feature dependency graph

## Dependencies
- **UI Components**: MQDS Components
- **Libraries**: Recharts, lucide-react

## Required APIs
- GET `/api/features` (Returns list of registered features and importances)\nGET `/api/features/{id}/dependencies` (Returns feature dependency graph)

## Repository Layer
- **Location**: `ml_service/repositories/`
- **Functions**: `signal_repository.py` (associates features with signals)

## Service Layer
- **Location**: `ml_service/services/`
- **Classes**: `explorer_query_service.py` (retrieves feature attributes)

## Analytics Layer
- **Location**: `ml_service/analytics/` or `ml_service/services/paper_analytics_service.py`
- **Features**: Performs math and data transformation for rendering.

## Frontend Components
- **Location**: `components/`
- **Files**: Reusable components matching Stitch design markers.

## Mock Status
- **Status**: PARTIAL

## Production Status
- **Status**: PARTIAL (dependency mapping logic needs UI integration)

## Future Integration Notes
Ensure mock JSON responses match the schema returned by the corresponding FastAPI endpoints. Map endpoint fields exactly to avoid breaking client charts.
