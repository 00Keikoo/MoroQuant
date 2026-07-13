# Trade Forensics Contract
    
## Purpose
Post-trade audit tool mapping closed trades back to specific feature states, dataset versions, and signals.

## Responsibilities
- **Frontend / Client**: Client shows single-trade drilldown, dataset version links, and signal graphs. Backend maps trade timestamps back to signal and dataset history.
- **Backend / Server**: Manages database reads/writes, calculates aggregations, and serves JSON payloads via FastAPI.

## Widgets
- Forensics search filter\n- Trade lineage map (Trade -> Signal -> Model -> Dataset)\n- Feature values at entry table

## Dependencies
- **UI Components**: MQDS Components
- **Libraries**: Recharts, lucide-react

## Required APIs
- GET `/api/forensics/trade/{id}` (Returns single trade forensic lineage details)

## Repository Layer
- **Location**: `ml_service/repositories/`
- **Functions**: `trade_repository.py` & `signal_repository.py` (traces trade entries back to generated signal records)

## Service Layer
- **Location**: `ml_service/services/`
- **Classes**: `explorer_query_service.py` (queries point-in-time feature records)

## Analytics Layer
- **Location**: `ml_service/analytics/` or `ml_service/services/paper_analytics_service.py`
- **Features**: Performs math and data transformation for rendering.

## Frontend Components
- **Location**: `components/`
- **Files**: Reusable components matching Stitch design markers.

## Mock Status
- **Status**: PARTIAL

## Production Status
- **Status**: PARTIAL (point-in-time feature extraction requires backend refinement)

## Future Integration Notes
Ensure mock JSON responses match the schema returned by the corresponding FastAPI endpoints. Map endpoint fields exactly to avoid breaking client charts.
