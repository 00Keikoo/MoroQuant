# ADR-007: PostgreSQL Migration Strategy

## Status
Accepted

## Context
During development, SQLite or file-based datastores are utilized for simplicity and zero-configuration setups. However, production instances demand concurrent writes, robust data constraints, transaction isolation, and scalability under large time-series workloads.

## Decision
We will design all database schemas and repositories to support a future migration to **PostgreSQL**. The migration strategy relies on:
1. Enforcing ANSI-compliant SQL queries and avoiding database-specific SQLite extensions in repository code.
2. Abstracting data schemas so database tables can be initialized in either SQLite or PostgreSQL.
3. Structuring migrations using versioned migration files rather than ad-hoc schema initialization scripts.

## Consequences
- **Portability**: Development workflows continue using fast, lightweight SQLite engines.
- **Enterprise-Ready**: Production environments can seamlessly leverage PostgreSQL concurrency and backup features.
- **Additional Overhead**: Requires double-testing schema changes and migrations on SQLite and PostgreSQL engines in CI environments.

## Alternatives Considered
- **Production SQLite**: Attempting to use SQLite in production with WAL (Write-Ahead Logging) mode. Rejected due to limited clustering options and lock contentions during heavy analytical workloads.
- **Early-Stage PostgreSQL Only**: Mandating PostgreSQL for local development. Rejected as it increases onboarding complexity and local development environment setup times.

## Related Documents
- [ADR-002-Repository-Pattern.md](file:///home/zafka/trade-dashboard/docs/adr/ADR-002-Repository-Pattern.md)
- [ADR-005-Raw-SQL-vs-ORM.md](file:///home/zafka/trade-dashboard/docs/adr/ADR-005-Raw-SQL-vs-ORM.md)

## Future Impact
Allows MoroQuant to handle thousands of concurrent transactions and feed production-grade analytical interfaces without database bottlenecks.
