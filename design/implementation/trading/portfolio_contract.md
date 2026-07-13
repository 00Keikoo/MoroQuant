# Portfolio Contract
    
## Purpose
Manages capital allocation, asset weights, sector exposures, and rebalancing parameters.

## Responsibilities
- **Frontend / Client**: Client shows current weights vs target weights and provides input forms for rebalancing. Backend calculates allocation optimization and processes target modifications.
- **Backend / Server**: Manages database reads/writes, calculates aggregations, and serves JSON payloads via FastAPI.

## Widgets
- Asset allocation pie/donut chart\n- Target vs Actual weight alignment tables\n- Leverage and margin utilization gauges

## Dependencies
- **UI Components**: MQDS Components
- **Libraries**: Recharts, lucide-react

## Required APIs
- GET `/api/ml/portfolio/summary` (Returns portfolio balances and positions)\nPOST `/api/ml/portfolio/rebalance` (Saves target weights and triggers rebalancing)

## Repository Layer
- **Location**: `ml_service/repositories/`
- **Functions**: `equity_repository.py` (tracks asset allocation ledger)

## Service Layer
- **Location**: `ml_service/services/`
- **Classes**: `paper_analytics_service.py` (computes portfolio beta, allocation metrics)

## Analytics Layer
- **Location**: `ml_service/analytics/` or `ml_service/services/paper_analytics_service.py`
- **Features**: Performs math and data transformation for rendering.

## Frontend Components
- **Location**: `components/`
- **Files**: Reusable components matching Stitch design markers.

## Mock Status
- **Status**: READY

## Production Status
- **Status**: PARTIAL (rebalance execution needs API integration)

## Future Integration Notes
Ensure mock JSON responses match the schema returned by the corresponding FastAPI endpoints. Map endpoint fields exactly to avoid breaking client charts.
