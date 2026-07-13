# Research Command Center Contract
    
## Purpose
Mission control for active model training, tuning, and validation jobs.

## Responsibilities
- **Frontend / Client**: Client shows status tables, CPU/GPU utilisation, and job actions (trigger/cancel). Backend runs pipelines and manages processes.
- **Backend / Server**: Manages database reads/writes, calculates aggregations, and serves JSON payloads via FastAPI.

## Widgets
- Pipeline Job Status grid\n- Training Loss curves (real-time progress)\n- System resources (GPU/CPU/RAM status)\n- Trigger Training form

## Dependencies
- **UI Components**: MQDS Components
- **Libraries**: Recharts, lucide-react

## Required APIs
- GET `/api/scheduler/jobs` (Returns active and historic jobs)\nPOST `/api/scheduler/jobs/trigger` (Starts a training pipeline)

## Repository Layer
- **Location**: `ml_service/repositories/`
- **Functions**: `experiment_repository.py` (records pipeline runs)

## Service Layer
- **Location**: `ml_service/services/`
- **Classes**: `explorer_query_service.py` (job management)

## Analytics Layer
- **Location**: `ml_service/analytics/` or `ml_service/services/paper_analytics_service.py`
- **Features**: Performs math and data transformation for rendering.

## Frontend Components
- **Location**: `components/`
- **Files**: Reusable components matching Stitch design markers.

## Mock Status
- **Status**: READY

## Production Status
- **Status**: PARTIAL (trigger API needs wiring to Python subprocesses)

## Future Integration Notes
Ensure mock JSON responses match the schema returned by the corresponding FastAPI endpoints. Map endpoint fields exactly to avoid breaking client charts.
