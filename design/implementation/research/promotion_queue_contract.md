# Promotion Queue Contract
    
## Purpose
Tracks models transitioning from Sandbox -> Shadow -> Production with automated validation checkmarks.

## Responsibilities
- **Frontend / Client**: Client shows promotion workflow steps and approval actions. Backend runs compatibility checks and handles updates.
- **Backend / Server**: Manages database reads/writes, calculates aggregations, and serves JSON payloads via FastAPI.

## Widgets
- Model Promotion pipeline checklist\n- Governance test status table (tests passed, failed, warning)\n- Promote / Demote action controls

## Dependencies
- **UI Components**: MQDS Components
- **Libraries**: lucide-react

## Required APIs
- GET `/api/models/promotion-queue` (Returns queue list)\nPOST `/api/models/{id}/promote` (Triggers tier-promotion and checks)

## Repository Layer
- **Location**: `ml_service/repositories/`
- **Functions**: `experiment_repository.py` (audits promotion events)

## Service Layer
- **Location**: `ml_service/services/`
- **Classes**: `explorer_query_service.py` (runs compatibility audits before promotion)

## Analytics Layer
- **Location**: `ml_service/analytics/` or `ml_service/services/paper_analytics_service.py`
- **Features**: Performs math and data transformation for rendering.

## Frontend Components
- **Location**: `components/`
- **Files**: Reusable components matching Stitch design markers.

## Mock Status
- **Status**: PARTIAL

## Production Status
- **Status**: PARTIAL (automatic checklist verification exists in CLI but needs API mapping)

## Future Integration Notes
Ensure mock JSON responses match the schema returned by the corresponding FastAPI endpoints. Map endpoint fields exactly to avoid breaking client charts.
