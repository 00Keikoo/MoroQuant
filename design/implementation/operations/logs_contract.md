# Logs Contract
    
## Purpose
High-performance real-time streaming application logs for backend services and pipelines.

## Responsibilities
- **Frontend / Client**: Client displays streaming terminal window with text filters. Backend tails logs from log files.
- **Backend / Server**: Manages database reads/writes, calculates aggregations, and serves JSON payloads via FastAPI.

## Widgets
- Terminal logger component with auto-scroll\n- Log source selectors (FastAPI, Scheduler, Backtester)\n- Level filter (INFO, WARN, ERROR)

## Dependencies
- **UI Components**: MQDS Components
- **Libraries**: lucide-react, JetBrains Mono font

## Required APIs
- GET `/api/logs` (Returns last N log lines)\nGET `/api/logs/stream` (Event source or WebSocket for log streaming)

## Repository Layer
- **Location**: `ml_service/repositories/`
- **Functions**: None

## Service Layer
- **Location**: `ml_service/services/`
- **Classes**: `explorer_query_service.py` (reads log files)

## Analytics Layer
- **Location**: `ml_service/analytics/` or `ml_service/services/paper_analytics_service.py`
- **Features**: Performs math and data transformation for rendering.

## Frontend Components
- **Location**: `components/`
- **Files**: Reusable components matching Stitch design markers.

## Mock Status
- **Status**: PARTIAL

## Production Status
- **Status**: PARTIAL (real-time stream needs SSE/WebSocket integration)

## Future Integration Notes
Ensure mock JSON responses match the schema returned by the corresponding FastAPI endpoints. Map endpoint fields exactly to avoid breaking client charts.
