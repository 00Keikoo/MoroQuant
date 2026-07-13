# Workers Contract
    
## Purpose
GPU/CPU node utilization, node heartbeat monitor, and worker task distribution.

## Responsibilities
- **Frontend / Client**: Client shows node health tables and memory usage meters. Backend tracks active process threads and runs systems checks.
- **Backend / Server**: Manages database reads/writes, calculates aggregations, and serves JSON payloads via FastAPI.

## Widgets
- GPU/CPU utilization timelines\n- Worker status table (ID, task, status, load)\n- Cluster memory gauge

## Dependencies
- **UI Components**: MQDS Components
- **Libraries**: Recharts, lucide-react

## Required APIs
- GET `/api/workers/metrics` (Returns cluster CPU, GPU, memory, and status of running tasks)

## Repository Layer
- **Location**: `ml_service/repositories/`
- **Functions**: None

## Service Layer
- **Location**: `ml_service/services/`
- **Classes**: `explorer_query_service.py` (retrieves subprocess thread health)

## Analytics Layer
- **Location**: `ml_service/analytics/` or `ml_service/services/paper_analytics_service.py`
- **Features**: Performs math and data transformation for rendering.

## Frontend Components
- **Location**: `components/`
- **Files**: Reusable components matching Stitch design markers.

## Mock Status
- **Status**: MISSING

## Production Status
- **Status**: MISSING (requires writing host metrics collection script)

## Future Integration Notes
Ensure mock JSON responses match the schema returned by the corresponding FastAPI endpoints. Map endpoint fields exactly to avoid breaking client charts.
