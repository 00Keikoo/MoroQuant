# 14 - Database Conventions

Standardized naming guidelines, query patterns, and migration pathways.

## Naming Standards
- **Tables**: Plural snake_case (e.g. `order_book_steps`, `trade_logs`).
- **Columns**: Singular snake_case (e.g. `created_at`, `order_status`).
- **Foreign Keys**: Follow pattern `parent_table_id` (e.g. `user_id`).

## Connection Management

| Environment | Database Choice | Pool Strategy |
|---|---|---|
| Development | SQLite | Single connection / connection per thread |
| Production | PostgreSQL | Managed connection pool (e.g. pgpool, SQLAlchemy QueuePool) |

## Database Best Practices
- **No Wildcard Queries**: Write `SELECT col_a, col_b` explicitly rather than `SELECT *`.
- **Batch Processing**: Use batch inserts for tick collections or simulation runs to minimize transaction commit overhead.
- **Constraints**: Apply strict database-level constraints (`NOT NULL`, `FOREIGN KEY`, `UNIQUE`) instead of relying solely on validation in code.

## Database Verification Checklist
- [ ] Schema changes have corresponding rollback scripts.
- [ ] Indexes are created for all query columns used in filtering.
- [ ] Queries are parameterized to protect against SQL injections.
