# ADR-006: Scheduler Process Separation

## Status
Accepted

## Context
MoroQuant requires cron actions and background timers (e.g. data ingestion routines, daily portfolio reconciliations, signal updates). Running these background jobs inline with the primary web application request loop or UI service blocks incoming HTTP requests, degrades server responsiveness, and results in double-execution if the application scales to multiple web instances.

## Decision
All scheduled tasks and timers must run in a **separate scheduler process** independent of the API web handlers. This daemon process will execute scheduled routines, publish tasks to workers, or trigger events, leaving the web server instances stateless and dedicated solely to user requests.

## Consequences
- **High Availability**: Web instances can scale out dynamically without causing scheduled tasks to execute multiple times.
- **Reliability**: Scheduler crashes will not disrupt user UI navigation or active WebSockets.
- **Configuration**: Requires a process supervisor or container orchestrator setup to run, monitor, and scale the scheduler process separately.

## Alternatives Considered
- **In-Process Timers**: Running scheduler threads inside the Next.js runtime or Python web runtime. Rejected due to scaling conflicts, memory leaks, and process restart vulnerabilities.
- **External Cron Triggers**: Using host machine standard system crons to hit API endpoints. Rejected as it exposes security endpoints to public access and depends heavily on host-specific operating systems.

## Related Documents
- [01-engineering-workflow.md](file:///home/zafka/trade-dashboard/docs/book/01-engineering-workflow.md)
- [07-audit-standard.md](file:///home/zafka/trade-dashboard/docs/book/07-audit-standard.md)

## Future Impact
Positions the codebase to adopt distributed task queues (e.g., Celery, Redis) when scaling to high-frequency processing pipelines.
