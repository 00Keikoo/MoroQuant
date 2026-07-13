# Scheduler Contract
    
## Purpose
Displays Directed Acyclic Graph (DAG) for training, validation, and data synchronization cron schedules.

## Responsibilities
- **Frontend / Client**: Client renders DAG nodes, execution timers, and run buttons. Backend executes tasks and updates states.
- **Backend / Server**: Manages database reads/writes, calculates aggregations, and serves JSON payloads via FastAPI.

## Widgets
- DAG task dependency graph\n- Cron schedule table\n- Trigger task controls

## Dependencies
- **UI Components**: MQDS Components
- **Libraries**: lucide-react

## Required APIs
- GET `/api/scheduler/status` (Returns active scheduler state)\nPOST `/api/scheduler/trigger-task` (Triggers manual execution of a task)

## Repository Layer
- **Location**: `ml_service/repositories/`
- **Functions**: `experiment_repository.py` (logs scheduler run events)

## Service Layer
- **Location**: `ml_service/services/`
- **Classes**: `explorer_query_service.py` (reads scheduler state)

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
