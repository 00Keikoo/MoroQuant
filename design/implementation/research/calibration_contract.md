# Calibration Contract
    
## Purpose
Model calibration analysis, including Brier scores, reliability diagrams, and confidence histograms.

## Responsibilities
- **Frontend / Client**: Client displays reliability curves and confidence histograms. Backend calculates probability calibration metrics.
- **Backend / Server**: Manages database reads/writes, calculates aggregations, and serves JSON payloads via FastAPI.

## Widgets
- Reliability curve chart (expected vs actual outcomes)\n- Confidence score distribution histogram\n- Brier score metrics panel

## Dependencies
- **UI Components**: MQDS Components
- **Libraries**: Recharts, lucide-react

## Required APIs
- GET `/api/calibration/metrics` (Returns Brier scores and reliability coordinates)

## Repository Layer
- **Location**: `ml_service/repositories/`
- **Functions**: `signal_repository.py` (tracks predicted confidence vs actual market directions)

## Service Layer
- **Location**: `ml_service/services/`
- **Classes**: `paper_analytics_service.py` (runs probability statistics and bins confidence levels)

## Analytics Layer
- **Location**: `ml_service/analytics/` or `ml_service/services/paper_analytics_service.py`
- **Features**: Performs math and data transformation for rendering.

## Frontend Components
- **Location**: `components/`
- **Files**: Reusable components matching Stitch design markers.

## Mock Status
- **Status**: PARTIAL

## Production Status
- **Status**: PARTIAL (needs API route exposing bin stats)

## Future Integration Notes
Ensure mock JSON responses match the schema returned by the corresponding FastAPI endpoints. Map endpoint fields exactly to avoid breaking client charts.
