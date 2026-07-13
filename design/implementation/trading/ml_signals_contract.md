# ML Signals Contract
    
## Purpose
Displays real-time machine learning predictions, directional confidence scores, and TP/SL barriers for active trading symbols.

## Responsibilities
- **Frontend / Client**: Client renders active signal tables, model confidence charts, and symbol filters. Backend runs model inference on schedule, persists signal outputs, and serves active signals.
- **Backend / Server**: Manages database reads/writes, calculates aggregations, and serves JSON payloads via FastAPI.

## Widgets
- Active Predictions table (symbol, direction, confidence, entry, TP/SL)\n- Feature Attribution Bar Chart (Gini/SHAP values)\n- Timeframe / Regime filter pills

## Dependencies
- **UI Components**: MQDS Components
- **Libraries**: Recharts, lucide-react, JetBrains Mono font

## Required APIs
- GET `/api/signals` (Returns active signals list)\nGET `/api/symbols` (Returns supported symbols and timeframes)

## Repository Layer
- **Location**: `ml_service/repositories/`
- **Functions**: `signal_repository.py` (stores signal direction, confidence, targets)

## Service Layer
- **Location**: `ml_service/services/`
- **Classes**: `market_state_service.py` (determines current market regime)

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
