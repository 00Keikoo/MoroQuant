# 13 - Runtime Guidelines

Guidelines for runtime safety, performance optimization, and reliability under load.

## Runtime Parameters

| Domain | Parameter Target | Value Constraint | Reason |
|---|---|---|---|
| Frontend | API Timeout | `< 5000ms` | Keep UI responsive, fail fast |
| ML Services | Memory Cap | `4GB` | Contain large model footprints |
| Database | Pool Size | `20 - 50` | Avoid port exhaustion |

## Concurrency and Performance Rules
- **Thread Constraints**: Do not initiate blocking network calls inside asynchronous loops.
- **Resource Cleanup**: Always close database connections, WebSocket channels, and file streams inside `finally` blocks.
- **Graceful Shutdowns**: Implement signal listeners (`SIGTERM`, `SIGINT`) to complete active transactions, release locks, and notify connected nodes before shutting down.

## Runtime Reliability Checklist
- [ ] Are retry mechanisms configured for external API calls?
- [ ] Do connection error states provide meaningful console outputs without crashing the app?
- [ ] Is server memory consumption monitored during active simulation loops?
