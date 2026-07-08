# Backend Architecture - Trade Explorer

**Version:** 1.0  
**Date:** 2026-07-06  
**Status:** Production Ready

---

## Overview

The Trade Explorer backend follows a **layered architecture** with strict separation of concerns. Each layer has a single responsibility and communicates only with adjacent layers.

```
HTTP Request
    ↓
FastAPI Routes (API Layer)
    ↓
ExplorerQueryService (Service Layer)
    ↓
TradeAnalytics (Analytics Layer)
    ↓
Repositories (Data Access Layer)
    ↓
SQLite Database
```

---

## Architecture Principles

### 1. Dependency Flow

Dependencies flow **downward only**:

- Routes depend on Service
- Service depends on Analytics + Repositories
- Analytics depends on Domain Objects (TradePosition)
- Repositories depend on Database

**No upward dependencies.** Lower layers never import from upper layers.

### 2. Layer Responsibilities

Each layer has a **single responsibility**:

| Layer | Responsibility | NOT Allowed |
|-------|---------------|-------------|
| Routes | HTTP handling, validation | Business logic, SQL, analytics |
| Service | Orchestration only | Business logic, SQL, analytics |
| Analytics | Pure calculations | Database access, side effects |
| Repository | SQL queries only | Business logic, calculations |

### 3. No Business Logic in Routes

Routes are **thin adapters** that:
- Parse HTTP requests
- Validate input (via Pydantic)
- Call service methods
- Return HTTP responses

Routes **never**:
- Perform calculations
- Write SQL
- Implement business logic

### 4. Pure Functions for Analytics

Analytics layer uses **pure functions**:
- No side effects
- No database access
- No global state
- Deterministic output

Benefits:
- Easy to test
- Easy to understand
- Easy to optimize
- Composable

---

## Layer Details

### API Layer (Routes)

**Location:** `ml_service/api/explorer_routes.py`

**Responsibility:** HTTP request/response handling

**Pattern:**
```python
@router.get("/endpoint", response_model=ResponseSchema)
async def endpoint_handler(
    params: QueryParams,
    service: Service = Depends(get_service)
) -> ResponseSchema:
    result = service.method(params)
    return ResponseSchema.from_domain(result)
```

**Key Points:**
- Uses FastAPI dependency injection
- Pydantic models for validation
- No business logic
- Delegates to service layer

**Files:**
- `explorer_routes.py` - Route definitions
- `schemas.py` - Pydantic response models

---

### Service Layer (Orchestration)

**Location:** `ml_service/services/explorer_query_service.py`

**Responsibility:** Coordinate repositories and analytics

**Pattern:**
```python
class ExplorerQueryService:
    def __init__(self, trade_repo, signal_repo, equity_repo):
        self.trade_repo = trade_repo
        self.signal_repo = signal_repo
        self.equity_repo = equity_repo

    def get_summary(self) -> TradeAnalyticsResult:
        trades = self.trade_repo.find_all(limit=10000)
        return calculate_trade_analytics(trades)
```

**Key Points:**
- NO business logic
- NO SQL queries
- NO calculations
- Only orchestration

**What Service Does:**
1. Call repositories to fetch data
2. Pass data to analytics layer
3. Return results to routes

**What Service Does NOT Do:**
- Perform calculations
- Write SQL
- Transform data

---

### Analytics Layer (Calculations)

**Location:** `ml_service/analytics/trade_analytics.py`

**Responsibility:** Calculate trading metrics from domain objects

**Pattern:**
```python
def calculate_trade_analytics(trades: List[TradePosition]) -> TradeAnalyticsResult:
    """Pure function - no side effects."""
    if not trades:
        return _empty_result()

    winning_trades = sum(1 for t in closed_trades if t.realized_pnl > 0)
    gross_profit = sum(t.realized_pnl for t in closed_trades if t.realized_pnl > 0)
    
    return TradeAnalyticsResult(
        winning_trades=winning_trades,
        gross_profit=gross_profit,
        # ... more metrics
    )
```

**Key Points:**
- Pure functions only
- Takes domain objects as input
- Returns domain objects as output
- No database access
- No side effects

**Testing:**
```python
def test_analytics():
    trades = [mock_trade_1, mock_trade_2]
    result = calculate_trade_analytics(trades)
    assert result.win_rate == 0.5
```

---

### Repository Layer (Data Access)

**Location:** `ml_service/repositories/`

**Responsibility:** Execute SQL queries, return domain objects

**Pattern:**
```python
class TradeRepository:
    def find_all(
        self,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[TradePosition]:
        query = "SELECT * FROM paper_positions WHERE 1=1"
        params = []

        if status:
            query += " AND status = ?"
            params.append(status)

        query += " LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        conn = get_connection(self.db_path)
        try:
            cursor = conn.execute(query, params)
            return [self._row_to_position(row) for row in cursor.fetchall()]
        finally:
            conn.close()
```

**Key Points:**
- Only layer that writes SQL
- Returns domain objects (TradePosition, Signal)
- No business logic
- Parameterized queries (SQL injection prevention)

**Domain Objects:**
```python
@dataclass
class TradePosition:
    id: int
    symbol: str
    direction: str
    entry_price: float
    realized_pnl: float
    # ... more fields
```

---

## Data Flow Examples

### Example 1: GET /trades

```
1. HTTP Request → FastAPI Route
   GET /api/v1/explorer/trades?status=OPEN&limit=10

2. Route → Service
   service.get_trade_list(status="OPEN", limit=10)

3. Service → Repository
   trade_repo.find_all(status="OPEN", limit=10)
   trade_repo.count(status="OPEN")

4. Repository → Database
   SELECT * FROM paper_positions WHERE status = 'OPEN' LIMIT 10
   SELECT COUNT(*) FROM paper_positions WHERE status = 'OPEN'

5. Repository → Service (domain objects)
   [TradePosition(...), TradePosition(...)]

6. Service → Route (domain objects)
   TradeListResult(trades=[...], total=42)

7. Route → HTTP Response (JSON)
   {"trades": [...], "total": 42, "limit": 10, "offset": 0}
```

**Key Points:**
- No business logic in route
- Service only orchestrates
- Repository handles SQL
- Domain objects flow through layers

---

### Example 2: GET /summary

```
1. HTTP Request → Route
   GET /api/v1/explorer/summary

2. Route → Service
   service.get_summary()

3. Service → Repository
   trade_repo.find_all(limit=10000)

4. Repository → Service (domain objects)
   [TradePosition(...), ...]

5. Service → Analytics
   calculate_trade_analytics(trades)

6. Analytics → Service (calculated result)
   TradeAnalyticsResult(win_rate=0.65, net_profit=17000, ...)

7. Service → Route (domain object)
   TradeAnalyticsResult(...)

8. Route → HTTP Response (JSON)
   {"win_rate": 0.65, "net_profit": 17000.0, ...}
```

**Key Points:**
- Analytics layer performs calculations
- Service orchestrates repository + analytics
- Pure function (analytics) receives domain objects

---

## Sequence Diagrams

### Trade List Query

```
┌──────┐     ┌───────┐     ┌─────────┐     ┌────────────┐     ┌──────────┐
│Client│     │Routes │     │ Service │     │ Repository │     │ Database │
└──┬───┘     └───┬───┘     └────┬────┘     └─────┬──────┘     └────┬─────┘
   │             │              │                │                  │
   │ GET /trades │              │                │                  │
   │────────────>│              │                │                  │
   │             │              │                │                  │
   │             │ get_trade_list()             │                  │
   │             │─────────────>│                │                  │
   │             │              │                │                  │
   │             │              │ find_all()     │                  │
   │             │              │───────────────>│                  │
   │             │              │                │                  │
   │             │              │                │ SELECT * FROM... │
   │             │              │                │─────────────────>│
   │             │              │                │                  │
   │             │              │                │ [rows]           │
   │             │              │                │<─────────────────│
   │             │              │                │                  │
   │             │              │ [TradePosition]│                  │
   │             │              │<───────────────│                  │
   │             │              │                │                  │
   │             │              │ count()        │                  │
   │             │              │───────────────>│                  │
   │             │              │                │                  │
   │             │              │                │ SELECT COUNT(*)  │
   │             │              │                │─────────────────>│
   │             │              │                │                  │
   │             │              │                │ 42               │
   │             │              │                │<─────────────────│
   │             │              │                │                  │
   │             │              │ 42             │                  │
   │             │              │<───────────────│                  │
   │             │              │                │                  │
   │             │ TradeListResult               │                  │
   │             │<─────────────│                │                  │
   │             │              │                │                  │
   │ JSON Response              │                │                  │
   │<────────────│              │                │                  │
   │             │              │                │                  │
```

### Summary Calculation

```
┌──────┐     ┌───────┐     ┌─────────┐     ┌────────────┐     ┌───────────┐
│Client│     │Routes │     │ Service │     │ Repository │     │ Analytics │
└──┬───┘     └───┬───┘     └────┬────┘     └─────┬──────┘     └─────┬─────┘
   │             │              │                │                    │
   │GET /summary │              │                │                    │
   │────────────>│              │                │                    │
   │             │              │                │                    │
   │             │ get_summary()│                │                    │
   │             │─────────────>│                │                    │
   │             │              │                │                    │
   │             │              │ find_all()     │                    │
   │             │              │───────────────>│                    │
   │             │              │                │                    │
   │             │              │ [TradePosition]│                    │
   │             │              │<───────────────│                    │
   │             │              │                │                    │
   │             │              │ calculate_trade_analytics(trades)  │
   │             │              │───────────────────────────────────>│
   │             │              │                │                    │
   │             │              │                │       [pure        │
   │             │              │                │      calculation]  │
   │             │              │                │                    │
   │             │              │ TradeAnalyticsResult               │
   │             │              │<───────────────────────────────────│
   │             │              │                │                    │
   │             │ TradeAnalyticsResult          │                    │
   │             │<─────────────│                │                    │
   │             │              │                │                    │
   │JSON Response│              │                │                    │
   │<────────────│              │                │                    │
   │             │              │                │                    │
```

---

## Database Schema

### paper_positions

Primary table for trade data.

```sql
CREATE TABLE paper_positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    direction TEXT NOT NULL CHECK(direction IN ('LONG', 'SHORT')),
    entry_price REAL NOT NULL,
    current_price REAL,
    size_usdt REAL NOT NULL,
    qty REAL NOT NULL,
    stop_loss REAL,
    take_profit REAL,
    signal_id INTEGER,
    status TEXT NOT NULL DEFAULT 'OPEN',
    realized_pnl REAL NOT NULL DEFAULT 0.0,
    opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    closed_at TIMESTAMP,
    confidence INTEGER,
    regime TEXT,
    timeframe TEXT,
    -- execution tracking fields
    mae REAL,
    mfe REAL,
    profit_capture_ratio REAL,
    final_exit_reason TEXT,
    execution_policy TEXT DEFAULT 'FIXED_SL'
);

CREATE INDEX idx_paper_positions_status ON paper_positions(status);
CREATE INDEX idx_paper_positions_symbol ON paper_positions(symbol);
```

### signals

Supporting table for signal data.

```sql
CREATE TABLE signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    timestamp INTEGER NOT NULL,
    direction TEXT NOT NULL,
    confidence INTEGER NOT NULL,
    features_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_signals_symbol_timeframe 
    ON signals(symbol, timeframe, timestamp DESC);
```

---

## Future PostgreSQL Migration

The architecture is designed for easy PostgreSQL migration:

### What Stays the Same

✅ **All business logic** - Service and Analytics layers unchanged  
✅ **API contracts** - No breaking changes to endpoints  
✅ **Domain objects** - TradePosition, Signal remain identical  
✅ **Repository interfaces** - Method signatures stay the same

### What Changes

🔄 **Repository implementation** - Replace SQLite queries with PostgreSQL  
🔄 **Database module** - Connection pooling, PostgreSQL driver  
🔄 **Migration scripts** - Schema definition in PostgreSQL

### Migration Steps

1. **Create PostgreSQL schema** - Same structure, PostgreSQL types
2. **Update database.py** - Use psycopg2/asyncpg instead of sqlite3
3. **Update repositories** - PostgreSQL-specific queries (minimal changes)
4. **Test with integration tests** - Same tests, different database
5. **Deploy** - Zero downtime with read replicas

### Example: Repository Changes

**Before (SQLite):**
```python
def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    path = get_db_path(db_path)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn
```

**After (PostgreSQL):**
```python
def get_connection(db_url: Optional[str] = None) -> psycopg2.Connection:
    url = get_db_url(db_url)
    conn = psycopg2.connect(url)
    conn.row_factory = RealDictRow
    return conn
```

**Repository queries stay nearly identical** - Only SQL dialect differences (e.g., `RETURNING *` in INSERT).

---

## Testing Strategy

### Unit Tests

Test each layer independently:

**Analytics (Pure Functions):**
```python
def test_calculate_analytics():
    trades = [
        TradePosition(realized_pnl=100, status="CLOSED", ...),
        TradePosition(realized_pnl=-50, status="CLOSED", ...)
    ]
    result = calculate_trade_analytics(trades)
    assert result.net_profit == 50
```

**Repositories (with Test Database):**
```python
def test_find_by_status(temp_db):
    repo = TradeRepository(db_path=temp_db)
    trades = repo.find_all(status="OPEN")
    assert all(t.status == "OPEN" for t in trades)
```

### Integration Tests

Test full stack with real components:

```python
def test_get_trades_endpoint(seeded_db):
    service = ExplorerQueryService(
        TradeRepository(seeded_db),
        SignalRepository(seeded_db),
        EquityRepository(seeded_db)
    )
    client = TestClient(app)
    response = client.get("/api/v1/explorer/trades")
    assert response.status_code == 200
```

---

## Performance Characteristics

### Time Complexity

| Operation | Complexity | Notes |
|-----------|-----------|-------|
| GET /trades | O(log n) | Indexed filter + sort |
| GET /trades/{id} | O(1) | Primary key lookup |
| GET /summary | O(n) | In-memory calculation |
| GET /metadata | O(n) | In-memory aggregation |

### Space Complexity

| Operation | Memory | Notes |
|-----------|--------|-------|
| GET /trades | O(limit) | Paginated results |
| GET /trades/{id} | O(1) | Single record |
| GET /summary | O(n) | Loads all trades (up to 10,000) |
| GET /metadata | O(n) | Loads all trades (up to 10,000) |

### Scalability

- ✅ 0-10,000 trades: Excellent performance
- ✅ 10,000-50,000 trades: Good performance
- ⚠️ 50,000+ trades: May need database-level aggregation

---

## Error Handling

### Repository Layer

```python
try:
    cursor = conn.execute(query, params)
    return [self._row_to_position(row) for row in cursor.fetchall()]
finally:
    conn.close()  # Always close connection
```

### Service Layer

Service returns `None` for not found, routes convert to 404:

```python
result = service.get_trade_detail(trade_id)
if result is None:
    raise HTTPException(status_code=404, detail=f"Trade {trade_id} not found")
```

### API Layer

FastAPI handles validation errors automatically (422).

---

## Security

### SQL Injection Prevention

✅ **Parameterized queries** - All user input uses `?` placeholders  
✅ **Query validation** - Sort columns validated against allowlist  
✅ **No string interpolation** - Never `f"SELECT * FROM {table}"`

### Input Validation

✅ **Pydantic models** - Automatic type validation  
✅ **Range constraints** - `limit` (1-1000), `offset` (≥0)  
✅ **Repository validation** - ID must be positive

---

## Dependency Injection

### Route Level

```python
@router.get("/trades")
async def get_trades(
    service: ExplorerQueryService = Depends(get_explorer_service)
):
    return service.get_trade_list()
```

### Service Factory

```python
def get_explorer_service() -> ExplorerQueryService:
    trade_repo = TradeRepository()
    signal_repo = SignalRepository()
    equity_repo = EquityRepository()
    return ExplorerQueryService(trade_repo, signal_repo, equity_repo)
```

### Testing Override

```python
app.dependency_overrides[get_explorer_service] = lambda: mock_service
```

---

## Code Organization

```
ml_service/
├── api/
│   ├── explorer_routes.py    # API layer
│   └── schemas.py             # Pydantic models
├── services/
│   └── explorer_query_service.py  # Service layer
├── analytics/
│   └── trade_analytics.py     # Analytics layer
└── repositories/
    ├── database.py            # Connection management
    ├── trade_repository.py    # Trade data access
    └── signal_repository.py   # Signal data access
```

---

## Related Documentation

- **[ADR-002: Repository Pattern](../adr/ADR-002-Repository-Pattern.md)** - Data access architecture
- **[ADR-003: Read-Only Trade Explorer](../adr/ADR-003-Read-Only-Trade-Explorer.md)** - API design rationale
- **[ADR-004: Analytics Layer Separation](../adr/ADR-004-Analytics-Layer-Separation.md)** - Pure functions approach
- **[ADR-005: Raw SQL vs ORM](../adr/ADR-005-Raw-SQL-vs-ORM.md)** - Repository implementation
- **[ADR-007: PostgreSQL Migration Strategy](../adr/ADR-007-PostgreSQL-Migration-Strategy.md)** - Future database migration

---

**Last Updated:** 2026-07-06  
**Review Cycle:** Quarterly or when major changes occur
