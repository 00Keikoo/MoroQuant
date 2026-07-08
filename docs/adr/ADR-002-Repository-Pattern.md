# ADR-002: Repository Pattern for Data Access

## Status
Accepted

## Context
The application needs to interact with trading databases, user preferences, and backtesting metrics. Directly embedding query logic, file I/O operations, or database connections within React component handlers, Next.js page routes, or core Python machine learning modules creates tight coupling. This coupling complicates testing, database migrations, and structural refactoring.

## Decision
We will enforce the **Repository Pattern** as the sole interface for data access. All business logic, services, and APIs must interact with data layers through repository interfaces, abstracting details such as raw files, SQLite databases, or external APIs.

## Consequences
- **Testing**: Allows easy mocking of repositories during unit testing.
- **Decoupling**: Business logic is independent of the persistence technology.
- **Portability**: Transitioning storage engines will only require updating the repository implementations, not the services calling them.
- **Maintenance**: Adds an extra abstraction layer and repository interfaces, slightly increasing file count.

## Alternatives Considered
- **Direct ORM/Query Invocation**: Calling ORM models directly in routing handlers. Rejected due to high coupling and difficulty mocking database layers in tests.
- **Active Record Pattern**: Allowing domain models to handle their own saving and retrieval. Rejected as it mixes business validation with storage mechanisms.

## Related Documents
- [04-documentation-standard.md](file:///home/zafka/trade-dashboard/docs/book/04-documentation-standard.md)
- [06-testing-standard.md](file:///home/zafka/trade-dashboard/docs/book/06-testing-standard.md)

## Future Impact
Facilitates swapping file-based storage or SQLite with PostgreSQL in production instances without changing front-end UI data bindings or machine learning backtest services.
