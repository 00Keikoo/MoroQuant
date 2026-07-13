# Trading Dashboard Contract
    
## Purpose
Provides a high-level view of global PnL, equity curves, sector exposure, and active exposure telemetry for live system management.

## Responsibilities
- **Frontend / Client**: Client handles charting rendering, metric formatting, and real-time updates via WebSocket. Backend tracks live balances, performance history, and updates database via exchange sync.
- **Backend / Server**: Manages database reads/writes, calculates aggregations, and serves JSON payloads via FastAPI.

## Widgets
- Equity Curve Chart (Recharts)\n- Daily PnL / Cumulative PnL metric cards\n- System Exposure / Leverage indicator\n- Active Positions summary list

## Dependencies
- **UI Components**: MQDS Components
- **Libraries**: Recharts, lucide-react, JetBrains Mono font

## Required APIs
- GET `/api/ml/portfolio/summary` (Returns balances, PnL, current equity points)\nGET `/api/binance/account` (Returns live exchange balance validation)

## Repository Layer
- **Location**: `ml_service/repositories/`
- **Functions**: `equity_repository.py` (equity points, daily snapshots)

## Service Layer
- **Location**: `ml_service/services/`
- **Classes**: `paper_analytics_service.py` (calculates drawdowns, rolling returns)

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
