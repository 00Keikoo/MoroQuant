# Live Analytics Contract
    
## Purpose
Calculates and visualizes performance distribution, drawdown, Sharpe ratio, and regime-based metrics in real time.

## Responsibilities
- **Frontend / Client**: Client displays statistical plots, distribution histograms, and performance tables. Backend runs analytics calculations over historic and live trade data.
- **Backend / Server**: Manages database reads/writes, calculates aggregations, and serves JSON payloads via FastAPI.

## Widgets
- PnL Distribution Histogram\n- Rolling Sharpe/Sortino chart\n- Regime Performance Breakdown grid

## Dependencies
- **UI Components**: MQDS Components
- **Libraries**: Recharts, lucide-react

## Required APIs
- GET `/api/ml/portfolio/analytics` (Returns performance statistics and Sharpe ratio)

## Repository Layer
- **Location**: `ml_service/repositories/`
- **Functions**: `equity_repository.py` (equity curves), `trade_repository.py` (trade data)

## Service Layer
- **Location**: `ml_service/services/`
- **Classes**: `paper_analytics_service.py` (implements performance math)

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
