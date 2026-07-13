# Trades Contract
    
## Purpose
Active position monitor and trade history blotter with performance details.

## Responsibilities
- **Frontend / Client**: Client displays tables of open and closed trades with search, sorting, and pagination. Backend logs execution, updates trade statuses, and fetches records.
- **Backend / Server**: Manages database reads/writes, calculates aggregations, and serves JSON payloads via FastAPI.

## Widgets
- Open Positions Table (entry price, current price, unrealized PnL, leverage)\n- Trade History Blotter (closed trades, realized PnL, exit reasons)\n- Filter controls (direction, date range, asset)

## Dependencies
- **UI Components**: MQDS Components
- **Libraries**: lucide-react, JetBrains Mono font

## Required APIs
- GET `/api/ml/trades` (Returns active positions and trade history)

## Repository Layer
- **Location**: `ml_service/repositories/`
- **Functions**: `trade_repository.py` (persists trade records, entry/exit timestamp, PnL)

## Service Layer
- **Location**: `ml_service/services/`
- **Classes**: `paper_analytics_service.py` (analyzes trade metrics: win rate, profit factor)

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
