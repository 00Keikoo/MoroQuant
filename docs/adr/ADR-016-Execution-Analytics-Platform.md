# ADR-016: Execution Analytics Platform Architecture

## Status
Accepted

## Context
Sprint 4.6 introduces the Execution Analytics Platform to query and audit order execution efficiency, slippage, latency, funnel conversions, and trade performance. An audit of our current system reveals several critical architectural issues:
1. **Repository Lag & Schema Drift**: The database schemas for `paper_positions` and `execution_decisions` have evolved to support latency, slippage, and execution policy details. However, the `TradeRepository` and its mapping classes have not been updated to load/write these attributes, leaving them unreachable through standard repository APIs.
2. **Repository Boundary Bypasses**: The Paper Broker, `execution_audit.py`, and existing analytics modules bypass the repository layer and instantiate raw SQLite connections directly, making it difficult to transition to other database backends (e.g. PostgreSQL) or mock data in testing.
3. **No Execution Decisions Repository**: There is no repository implementation for the `execution_decisions` table, forcing downstream components to run arbitrary raw SQL queries to compile rejections or funnel metrics.
4. **Data Lineage Contamination**: Syncing live exchange executions (`user_trade_history`) and paper simulations (`paper_positions`) requires strict logical separation to maintain performance boundaries and analytics integrity.

## Decision
We will enforce the standard MoroQuant architectural pattern:
$$\text{Repository} \longrightarrow \text{Service} \longrightarrow \text{Analytics} \longrightarrow \text{API}$$

Specifically, we establish the following decisions:
1. **Repository Restructuring**:
   - Update `TradeRepository` to support all execution quality attributes (`signal_price`, `execution_price`, `execution_timestamp`, `slippage_pct`, `execution_latency_ms`).
   - Create `ExecutionDecisionRepository` to manage inserts, updates, and filtering of execution decisions.
   - Restrict database operations to use a single connection management boundary defined in `ml_service/repositories/database.py`. No component may execute raw SQLite connections directly.
2. **Analytics Isolation**:
   - The analytics layer (`ml_service/analytics/execution/analytics.py`) must consist solely of pure functions that accept immutable dataclasses or numeric structures.
   - It is strictly prohibited from running database queries, loading environment variables, or accessing disk I/O.
3. **Service Orchestration**:
   - Create a service layer (`ml_service/analytics/execution/service.py`) that acts as the entrypoint for compiling metrics from repositories, passing raw records to the pure analytics engine, and returning unified data contracts to the API.
4. **API Integration**:
   - Expose endpoints via FastAPI under the `/api/v1/analytics/execution` routing prefix.
   - Use distinct API endpoints for `paper` vs `live` to prevent lineage contamination.

## Consequences
- **Testing**: We can easily unit test the analytics logic by passing dummy dataclasses without mocking database state.
- **Portability**: Transitioning from SQLite to PostgreSQL is simplified, as all SQL operations are confined to repository files.
- **Consistency**: Eliminates duplicate SQLite handles across background threads and resolves schema drift.
- **Complexity**: Slightly increases file counts by adding explicit service and contract interfaces.

## Related Documents
- [ADR-002: Repository Pattern for Data Access](file:///home/zafka/trade-dashboard/docs/adr/ADR-002-Repository-Pattern.md)
- [ADR-004: Analytics Layer Separation](file:///home/zafka/trade-dashboard/docs/adr/ADR-004-Analytics-Layer-Separation.md)
- [EXECUTION_ANALYTICS_DATA_AUDIT.md](file:///home/zafka/trade-dashboard/docs/audits/lab/execution_analytics_data_audit.md)
