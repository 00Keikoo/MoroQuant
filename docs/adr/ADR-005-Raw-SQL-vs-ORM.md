# ADR-005: Raw SQL vs. ORM Selection

## Status
Accepted

## Context
We need to access and query relational tables for trade tracking and performance analysis. Using an Object-Relational Mapper (ORM) speeds up initial model creation and handles routine CRUD workflows, but it can introduce query performance overhead and conceal complex joins. Conversely, writing raw SQL queries gives maximum performance and visibility but increases maintenance and database-dependent syntax exposure.

## Decision
We will employ a **hybrid data access strategy**:
1. For standard CRUD operations (e.g. user settings, configuration profiles, execution locks), we will utilize light ORMs to speed up development.
2. For heavy time-series read operations, complex analytical reports, and bulk inserts of historical trade steps, we will write **parameterized Raw SQL** or execution helpers to bypass ORM mapping performance bottlenecks.

## Consequences
- **Optimization**: Retains database query optimization options for quantitative reporting paths.
- **Speed of Development**: Minimizes boilerplate for simple data operations.
- **Safety**: Raw SQL queries must still be parameterized to prevent injection risks.
- **Consistency Requirements**: Developers must clearly document in repository classes why raw SQL is preferred over ORM helpers for a given function.

## Alternatives Considered
- **Strict ORM-Only**: Forbid all raw SQL. Rejected due to performance limitations and query mapping issues on complex trade aggregates.
- **Strict SQL-Only**: Implement all storage layers via manual SQL scripts. Rejected due to high development overhead for trivial configuration models.

## Related Documents
- [ADR-002-Repository-Pattern.md](file:///home/zafka/trade-dashboard/docs/adr/ADR-002-Repository-Pattern.md)
- [05-code-review-standard.md](file:///home/zafka/trade-dashboard/docs/book/05-code-review-standard.md)

## Future Impact
Keeps database schemas clean and readable while facilitating manual database indexing and performance tuning as data volume grows.
