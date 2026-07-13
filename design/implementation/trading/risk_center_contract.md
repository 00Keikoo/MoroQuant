# Risk Center Contract
    
## Purpose
Provides stress testing (Monte Carlo simulations), Greek exposure ladders, Value at Risk (VaR), and margin limits.

## Responsibilities
- **Frontend / Client**: Client renders risk gauges, VaR boundaries, and stress test controls. Backend calculates Monte Carlo paths and runs Greek risk math.
- **Backend / Server**: Manages database reads/writes, calculates aggregations, and serves JSON payloads via FastAPI.

## Widgets
- Monte Carlo Path projection chart\n- VaR (Value at Risk) gauge\n- Scenario stress test controls

## Dependencies
- **UI Components**: MQDS Components
- **Libraries**: Recharts, lucide-react

## Required APIs
- GET `/api/ml/portfolio/analytics` (Returns standard risk metrics)\nGET `/api/ml/portfolio/risk/simulate` (Triggers and returns stress test simulations)

## Repository Layer
- **Location**: `ml_service/repositories/`
- **Functions**: `equity_repository.py` (historical returns data)

## Service Layer
- **Location**: `ml_service/services/`
- **Classes**: `paper_analytics_service.py` (implements VaR and basic stats)

## Analytics Layer
- **Location**: `ml_service/analytics/` or `ml_service/services/paper_analytics_service.py`
- **Features**: Performs math and data transformation for rendering.

## Frontend Components
- **Location**: `components/`
- **Files**: Reusable components matching Stitch design markers.

## Mock Status
- **Status**: PARTIAL

## Production Status
- **Status**: PARTIAL (stress test simulation endpoints require extension)

## Future Integration Notes
Ensure mock JSON responses match the schema returned by the corresponding FastAPI endpoints. Map endpoint fields exactly to avoid breaking client charts.
