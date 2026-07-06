# Trade Explorer - System Architecture

**Sprint 3, Task 3.1**  
**Date:** 2026-07-06  
**Status:** Design Phase

## Executive Summary

Trade Explorer is a research-focused UI for exploring paper trading execution data. It provides deep visibility into trade performance, execution quality, and attribution analysis without modifying the paper trading engine.

**Architecture Pattern:** Read-only analytical layer over existing paper trading infrastructure  
**Integration Approach:** REST API + React frontend components  
**Data Strategy:** Query-time aggregation with optional caching for complex analytics

---

## System Context

```
┌─────────────────────────────────────────────────────────────┐
│                    Trade Dashboard (Next.js)                │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Trading    │  │  Dashboard   │  │    Trade     │     │
│  │     Page     │  │     Page     │  │  Explorer    │◄────┼─── NEW
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│         │                 │                  │              │
└─────────┼─────────────────┼──────────────────┼──────────────┘
          │                 │                  │
          ▼                 ▼                  ▼
┌─────────────────────────────────────────────────────────────┐
│              ML Service REST API (FastAPI)                   │
│                                                              │
│  Existing Endpoints       │      Trade Explorer Endpoints   │
│  ───────────────────      │      ───────────────────────    │
│  /paper/summary           │      /explorer/trades           │◄─── NEW
│  /paper/analytics         │      /explorer/trades/:id       │◄─── NEW
│  /paper/positions/closed  │      /explorer/analytics        │◄─── NEW
│                           │      /explorer/filters          │◄─── NEW
└───────────────────────────┼──────────────────────────────────┘
                            │
                            ▼
                  ┌─────────────────────┐
                  │   SQLite Database   │
                  │                     │
                  │  paper_positions    │
                  │  paper_account      │
                  │  paper_equity_hist  │
                  │  signals            │
                  └─────────────────────┘
```

---

## Architecture Principles

### 1. Separation of Concerns
- **Paper Broker:** Executes trades, manages lifecycle, tracks metrics
- **Trade Explorer:** Reads and analyzes completed trades, zero write operations
- **No coupling:** Trade Explorer does not modify paper trading logic

### 2. Query-Time Aggregation
- Compute analytics on-demand from raw position data
- No separate aggregation tables or materialized views
- Leverage SQLite's query performance (sufficient for research workload)

### 3. Progressive Enhancement
- MVP delivers core exploration with existing data
- Future phases add caching, advanced analytics, price history
- Each phase is independently deployable

### 4. Read-Only Operations
- All Trade Explorer endpoints are GET requests
- No mutations to paper trading state
- Safe for concurrent access during live trading

---

## Component Architecture

### Backend Layer

```
┌────────────────────────────────────────────────────────────┐
│                   FastAPI Application                       │
│                                                             │
│  routes.py (existing)                                       │
│  ├── /paper/*              (existing endpoints)            │
│  └── /explorer/*           (new endpoints) ◄────────────┐  │
│                                                          │  │
│  services/                                               │  │
│  ├── paper_analytics_service.py (existing)              │  │
│  └── trade_explorer_service.py (new) ◄──────────────────┘  │
│       │                                                     │
│       ├── get_trades(filters, pagination)                  │
│       ├── get_trade_detail(trade_id)                       │
│       ├── compute_analytics(filters)                       │
│       └── get_filter_options()                             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### New Service: `trade_explorer_service.py`

**Responsibilities:**
- Query `paper_positions` with flexible filtering
- Compute derived metrics (EQS, classifications)
- JOIN with `signals` table for attribution
- Aggregate analytics by dimensions (confidence, regime, policy)
- Return paginated, filtered, sorted trade lists

**Key Functions:**
```python
def get_trades(
    filters: TradeFilters,
    sort_by: str,
    sort_order: str,
    page: int,
    page_size: int
) -> TradeListResponse

def get_trade_detail(trade_id: int) -> TradeDetail

def compute_filtered_analytics(
    filters: TradeFilters
) -> AnalyticsSummary

def get_filter_dimensions() -> FilterOptions
```

---

### Frontend Layer

```
┌────────────────────────────────────────────────────────────┐
│              app/explorer/page.tsx (new)                    │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐  │
│  │              Trade Explorer Layout                   │  │
│  │                                                       │  │
│  │  ┌──────────────────────────────────────────────┐   │  │
│  │  │         TradeFilterPanel.tsx (new)           │   │  │
│  │  │  Symbol │ Status │ Regime │ Confidence │... │   │  │
│  │  └──────────────────────────────────────────────┘   │  │
│  │                                                       │  │
│  │  ┌──────────────────────────────────────────────┐   │  │
│  │  │       TradeAnalyticsSummary.tsx (new)        │   │  │
│  │  │  Win Rate │ Profit Factor │ EQS │ Expectancy │   │  │
│  │  └──────────────────────────────────────────────┘   │  │
│  │                                                       │  │
│  │  ┌──────────────────────────────────────────────┐   │  │
│  │  │          TradeListTable.tsx (new)            │   │  │
│  │  │  [Paginated, sortable trade list]            │   │  │
│  │  └──────────────────────────────────────────────┘   │  │
│  │                                                       │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                             │
│  app/explorer/[id]/page.tsx (new)                          │
│  ┌─────────────────────────────────────────────────────┐  │
│  │           Trade Detail View                          │  │
│  │  ┌────────────────┐  ┌─────────────────────────┐   │  │
│  │  │  Trade Summary │  │  Execution Intelligence │   │  │
│  │  │  Entry/Exit    │  │  MAE/MFE/PCR/EQS       │   │  │
│  │  └────────────────┘  └─────────────────────────┘   │  │
│  │  ┌────────────────────────────────────────────────┐ │  │
│  │  │         Signal Attribution Card              │ │  │
│  │  │  Confidence │ Regime │ Probabilities         │ │  │
│  │  └────────────────────────────────────────────────┘ │  │
│  └─────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────┘
```

---

## Data Flow

### Trade List Query Flow

```
User interacts with filters
         │
         ▼
TradeFilterPanel emits filter state
         │
         ▼
React Query fetches /explorer/trades?filters=...
         │
         ▼
trade_explorer_service.get_trades()
         │
         ├─► Build SQL WHERE clause from filters
         ├─► JOIN with signals table for attribution
         ├─► Compute derived metrics (EQS, classification)
         ├─► Apply sorting and pagination
         └─► Return TradeListResponse
         │
         ▼
TradeListTable renders paginated results
         │
         ▼
User clicks trade row
         │
         ▼
Navigate to /explorer/:id
```

### Analytics Aggregation Flow

```
Filters change
         │
         ▼
React Query fetches /explorer/analytics?filters=...
         │
         ▼
trade_explorer_service.compute_filtered_analytics()
         │
         ├─► Query filtered positions
         ├─► Compute win rate, profit factor, EQS
         ├─► Group by dimensions (confidence, regime, policy)
         └─► Return AnalyticsSummary
         │
         ▼
TradeAnalyticsSummary displays KPIs
```

---

## Database Query Patterns

### Core Query Structure

```sql
-- Base query with JOINs and derived metrics
SELECT 
    pp.*,
    s.direction as signal_direction,
    s.timestamp as signal_timestamp,
    
    -- Derived: Execution Quality Score
    CASE 
        WHEN pp.size_usdt > 0 THEN
            50 + 
            CASE WHEN pp.mfe > 0.01 
                THEN (pp.profit_capture_ratio * 30) 
                ELSE 0 END +
            CASE WHEN pp.mae < -0.02 
                THEN (ABS(pp.mae) * -100) 
                ELSE 10 END +
            CASE pp.status
                WHEN 'TP_HIT' THEN 20
                WHEN 'SL_HIT' THEN 5
                ELSE 10 END
        ELSE 0
    END as eqs,
    
    -- Derived: Execution Classification
    CASE
        WHEN pp.mfe > 0.02 AND pp.profit_capture_ratio > 0.5 
            THEN 'MODEL_CORRECT_EXECUTION_CORRECT'
        WHEN pp.mfe > 0.02 AND pp.profit_capture_ratio <= 0.5 
            THEN 'MODEL_CORRECT_EXECUTION_WEAK'
        WHEN pp.mfe <= 0.02 AND pp.realized_pnl >= 0 
            THEN 'MODEL_WEAK_EXECUTION_CORRECT'
        WHEN pp.mfe <= 0.02 AND pp.realized_pnl < 0 
            THEN 'MODEL_WEAK_EXECUTION_WEAK'
        ELSE 'UNKNOWN'
    END as execution_classification,
    
    -- Derived: Duration
    CAST((julianday(pp.closed_at) - julianday(pp.opened_at)) * 24 AS REAL) as duration_hours,
    
    -- Derived: PnL %
    CASE WHEN pp.size_usdt > 0 
        THEN (pp.realized_pnl / pp.size_usdt * 100) 
        ELSE 0 END as pnl_pct

FROM paper_positions pp
LEFT JOIN signals s ON pp.signal_id = s.id
WHERE pp.status != 'OPEN'
    AND (? IS NULL OR pp.symbol = ?)
    AND (? IS NULL OR pp.status = ?)
    AND (? IS NULL OR pp.regime = ?)
    AND (? IS NULL OR pp.confidence >= ?)
    -- ... additional filters
ORDER BY pp.closed_at DESC
LIMIT ? OFFSET ?
```

### Indexes (Existing)

```sql
CREATE INDEX idx_paper_positions_status ON paper_positions(status);
CREATE INDEX idx_paper_positions_symbol ON paper_positions(symbol);
```

### Recommended Indexes (Future Optimization)

```sql
-- Composite index for common filter combinations
CREATE INDEX idx_paper_positions_filters 
ON paper_positions(status, symbol, regime, confidence, closed_at);

-- Index for signal JOINs
CREATE INDEX idx_paper_positions_signal_id ON paper_positions(signal_id);
CREATE INDEX idx_signals_id ON signals(id);
```

---

## API Design (Preview)

See `TradeExplorer_API.md` for full specification.

### Core Endpoints

```
GET  /api/explorer/trades
GET  /api/explorer/trades/:id
GET  /api/explorer/analytics
GET  /api/explorer/filters
```

### Response Pagination

```json
{
  "status": "success",
  "data": [...],
  "pagination": {
    "page": 1,
    "page_size": 50,
    "total_count": 156,
    "total_pages": 4,
    "has_next": true,
    "has_prev": false
  }
}
```

---

## Performance Considerations

### Query Performance

**Expected Load:**
- Research workload (not production latency-sensitive)
- 1-10 concurrent users
- 100-1000 closed positions
- Query latency target: < 500ms for list, < 200ms for detail

**Optimization Strategy:**
- SQLite performs well for this scale
- Add composite indexes if query time > 500ms
- Consider query result caching for analytics (5-minute TTL)

### Scalability

**Current Scale:**
- ~10 trades/day × 365 days = ~3,650 trades/year
- Well within SQLite's capacity (tested to millions of rows)

**Future Scale (if needed):**
- Add Redis cache for analytics endpoints
- Move to PostgreSQL for advanced analytics (window functions, CTEs)
- Implement materialized views for common aggregations

---

## Error Handling

### Backend

```python
# trade_explorer_service.py
def get_trade_detail(trade_id: int) -> TradeDetail:
    try:
        conn = _get_connection()
        row = conn.execute(
            "SELECT ... FROM paper_positions WHERE id = ?", 
            (trade_id,)
        ).fetchone()
        
        if not row:
            raise TradeNotFoundError(f"Trade {trade_id} not found")
        
        return _row_to_trade_detail(row)
    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        raise DatabaseError("Failed to fetch trade") from e
    finally:
        conn.close()
```

### Frontend

```typescript
// Use React Query for error handling
const { data, error, isLoading } = useQuery({
  queryKey: ['trade', id],
  queryFn: () => fetchTradeDetail(id)
});

if (error) return <ErrorCard message="Failed to load trade" />;
if (isLoading) return <Skeleton />;
```

---

## Security Considerations

### Authentication
- Trade Explorer uses existing Next.js auth (if implemented)
- If no auth: data is already accessible via existing paper endpoints
- Read-only operations: no CSRF risk

### SQL Injection
- Use parameterized queries for all user inputs
- Validate enum values (status, direction) against allowed sets
- Sanitize string filters (symbol, regime)

### Data Privacy
- Paper trading data is research-only (no real funds)
- No PII or sensitive data in positions table
- Safe to expose in development/research environments

---

## Testing Strategy

### Unit Tests

```python
# tests/test_trade_explorer_service.py
def test_get_trades_with_filters():
    """Test trade list filtering logic."""
    filters = TradeFilters(symbol="BTCUSDT", status="TP_HIT")
    result = get_trades(filters, page=1, page_size=10)
    assert all(t.symbol == "BTCUSDT" for t in result.trades)
    assert all(t.status == "TP_HIT" for t in result.trades)

def test_compute_eqs():
    """Test EQS derivation logic."""
    eqs = _calculate_eqs(mae=-0.05, mfe=0.10, realized_pnl=50, 
                         size_usdt=1000, status="TP_HIT")
    assert 0 <= eqs <= 100
```

### Integration Tests

```python
# tests/test_explorer_api.py
def test_get_trades_endpoint(client):
    """Test trades endpoint returns valid response."""
    response = client.get("/api/explorer/trades?symbol=BTCUSDT")
    assert response.status_code == 200
    data = response.json()
    assert "trades" in data
    assert "pagination" in data

def test_trade_detail_404(client):
    """Test trade detail returns 404 for invalid ID."""
    response = client.get("/api/explorer/trades/99999")
    assert response.status_code == 404
```

### Frontend Tests

```typescript
// components/__tests__/TradeListTable.test.tsx
test('renders trade list with data', () => {
  const trades = mockTradeData();
  render(<TradeListTable trades={trades} />);
  expect(screen.getByText('BTCUSDT')).toBeInTheDocument();
});

test('handles empty state', () => {
  render(<TradeListTable trades={[]} />);
  expect(screen.getByText('No trades found')).toBeInTheDocument();
});
```

---

## Deployment Strategy

### Phase 1: Backend Only (Day 1-2)
1. Implement `trade_explorer_service.py`
2. Add `/explorer/*` endpoints to `routes.py`
3. Write unit tests
4. Deploy to dev environment
5. Test via Postman/curl

### Phase 2: Frontend MVP (Day 3-4)
1. Create `/app/explorer/page.tsx`
2. Implement `TradeListTable` and `TradeFilterPanel`
3. Add navigation link from main dashboard
4. Deploy to dev environment
5. Internal testing

### Phase 3: Detail View (Day 5)
1. Create `/app/explorer/[id]/page.tsx`
2. Implement `TradeDetailView` components
3. Add drill-down navigation from list
4. Deploy to dev environment

### Phase 4: Analytics Enhancement (Day 6+)
1. Add `TradeAnalyticsSummary` component
2. Implement chart visualizations (MAE/MFE distributions)
3. Performance optimization (caching, indexes)
4. User feedback iteration

---

## Monitoring & Observability

### Metrics to Track

```python
# Add to trade_explorer_service.py
logger.info(
    "Trade query executed",
    extra={
        "filters": filters.dict(),
        "result_count": len(trades),
        "query_time_ms": query_time,
        "page": page
    }
)
```

### Dashboard Alerts
- Trade query latency > 1s (investigate slow queries)
- Error rate > 5% (database issues)
- Zero trades returned unexpectedly (data pipeline issue)

---

## Future Enhancements

### Phase 2: Advanced Analytics
- Trade equity curve (individual position impact)
- MAE/MFE distribution histograms
- Win/loss streak analysis
- Comparison mode (compare policies, regimes)

### Phase 3: Export & Reporting
- Export filtered trades to CSV
- Generate PDF trade reports
- Scheduled email reports

### Phase 4: Real-Time Updates
- WebSocket updates for live positions becoming closed
- Auto-refresh analytics as new trades close
- Real-time equity impact calculation

---

## References

- Gap Analysis: `GapAnalysis.md`
- Data Availability: `DataAvailabilityMatrix.md`
- API Specification: `TradeExplorer_API.md`
- Database Schema: `TradeExplorer_Database.md`
- UI Design: `TradeExplorer_UI.md`

---

## Appendix: Technology Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Backend | FastAPI | Existing, proven in production |
| Database | SQLite | Sufficient for research workload, existing |
| Frontend | Next.js 14 + React | Existing stack |
| UI Library | Tailwind CSS + shadcn/ui | Existing, consistent with dashboard |
| State Management | React Query | Best for async data fetching |
| Charts | Recharts | Existing, simple integration |
| Testing | pytest (backend), Jest (frontend) | Standard tools |

---

## Success Criteria

Trade Explorer MVP is successful if:

1. ✅ Users can list all closed paper trades with filtering
2. ✅ Users can view detailed execution intelligence per trade
3. ✅ Users can analyze performance by confidence/regime/policy
4. ✅ Query latency < 500ms for list, < 200ms for detail
5. ✅ Zero bugs in core filtering/sorting logic
6. ✅ UI is intuitive without documentation

**Timeline:** 5-6 days for MVP delivery.
