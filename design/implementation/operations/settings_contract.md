# Settings Contract
    
## Purpose
Global parameter management, database connection strings, and exchange API credentials configuration.

## Responsibilities
- **Frontend / Client**: Client renders settings forms and triggers test connections. Backend saves config.yaml settings.
- **Backend / Server**: Manages database reads/writes, calculates aggregations, and serves JSON payloads via FastAPI.

## Widgets
- Configuration options tabs (Exchange, Database, Model limits)\n- Form fields for API keys and connection URLs\n- Test Connection action button

## Dependencies
- **UI Components**: MQDS Components
- **Libraries**: lucide-react

## Required APIs
- GET `/api/settings` (Returns current non-sensitive settings configuration)\nPOST `/api/settings` (Saves configuration parameters)

## Repository Layer
- **Location**: `ml_service/repositories/`
- **Functions**: None

## Service Layer
- **Location**: `ml_service/services/`
- **Classes**: None

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
