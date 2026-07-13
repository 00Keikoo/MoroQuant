# Execution Contract
    
## Purpose
Monitors sub-millisecond order flow, slippage analytics, execution latency, and order book depth.

## Responsibilities
- **Frontend / Client**: Client renders real-time latency line charts, order flow logs, and slippage tables. Backend tracks order lifecycle timings and computes latency stats.
- **Backend / Server**: Manages database reads/writes, calculates aggregations, and serves JSON payloads via FastAPI.

## Widgets
- Execution Latency timeline chart\n- Slippage per asset table\n- Order book depth visualization

## Dependencies
- **UI Components**: MQDS Components
- **Libraries**: Recharts, lucide-react, JetBrains Mono font

## Required APIs
- GET `/api/execution/latency` (Returns system latency and order flow telemetry)

## Repository Layer
- **Location**: `ml_service/repositories/`
- **Functions**: `trade_repository.py` (order fill logs with sub-ms execution timestamps)

## Service Layer
- **Location**: `ml_service/services/`
- **Classes**: `execution_intelligence.py` (calculates execution slippage, latency distribution)

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
