# Trade Explorer - REST API Specification

**Sprint 3, Task 3.1**  
**Date:** 2026-07-06  
**Status:** Design Phase

## Overview

REST API endpoints for Trade Explorer. All endpoints are read-only (GET requests) and query the paper trading execution database.

**Base URL:** `/api/explorer`  
**Response Format:** JSON  
**Authentication:** Uses existing Next.js/FastAPI auth (if configured)

---

## Endpoints Summary

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/explorer/trades` | GET | List trades with filtering, sorting, pagination |
| `/explorer/trades/:id` | GET | Get detailed trade data |
| `/explorer/analytics` | GET | Compute analytics for filtered trades |
| `/explorer/filters` | GET | Get available filter options |

---

## 1. List Trades

**Endpoint:** `GET /api/explorer/trades`

**Purpose:** Retrieve paginated, filtered, sorted list of closed paper trades.

### Query Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `page` | integer | No | 1 | Page number (1-indexed) |
| `page_size` | integer | No | 50 | Items per page (max 200) |
| `sort_by` | string | No | `closed_at` | Sort field |
| `sort_order` | string | No | `desc` | Sort direction: `asc` or `desc` |
| `symbol` | string | No | - | Filter by symbol (e.g., `BTCUSDT`) |
| `status` | string | No | - | Filter by status |
| `direction` | string | No | - | Filter by direction: `LONG` or `SHORT` |
| `regime` | string | No | - | Filter by market regime |
| `timeframe` | string | No | - | Filter by timeframe |
| `execution_policy` | string | No | - | Filter by execution policy |
| `confidence_min` | integer | No | - | Minimum confidence (0-100) |
| `confidence_max` | integer | No | - | Maximum confidence (0-100) |
| `pnl_min` | float | No | - | Minimum realized PnL |
| `pnl_max` | float | No | - | Maximum realized PnL |
| `date_from` | string | No | - | Start date (ISO 8601) |
| `date_to` | string | No | - | End date (ISO 8601) |
| `eqs_min` | integer | No | - | Minimum EQS (0-100) |
| `eqs_max` | integer | No | - | Maximum EQS (0-100) |

### Sort Fields

Allowed values for `sort_by`:
- `closed_at` (default)
- `opened_at`
- `realized_pnl`
- `pnl_pct`
- `duration_hours`
- `confidence`
- `eqs`
- `mae`
- `mfe`
- `profit_capture_ratio`

### Response Schema

```json
{
  "status": "success",
  "trades": [
    {
      "id": 42,
      "symbol": "BTCUSDT",
      "direction": "LONG",
      "status": "TP_HIT",
      "entry_price": 65000.0,
      "exit_price": 67000.0,
      "size_usdt": 100.0,
      "qty": 0.001538,
      "realized_pnl": 3.08,
      "pnl_pct": 3.08,
      "opened_at": "2026-07-01T08:30:00Z",
      "closed_at": "2026-07-02T14:15:00Z",
      "duration_hours": 29.75,
      
      "mae": -0.012,
      "mfe": 0.045,
      "profit_capture_ratio": 0.68,
      "eqs": 78,
      "execution_classification": "MODEL_CORRECT_EXECUTION_CORRECT",
      "final_exit_reason": "TP_HIT",
      
      "confidence": 72,
      "regime": "bullish_trending",
      "timeframe": "1h",
      "execution_edge": 0.35,
      "execution_policy": "TRAILING",
      "trailing_stop_activated": true,
      "sl_move_count": 3,
      "break_even_triggered": true,
      
      "signal_id": 1234,
      "signal_direction": "LONG",
      "signal_timestamp": "2026-07-01T08:00:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 50,
    "total_count": 156,
    "total_pages": 4,
    "has_next": true,
    "has_prev": false
  },
  "filters_applied": {
    "symbol": "BTCUSDT",
    "status": null,
    "confidence_min": 60
  },
  "timestamp": "2026-07-06T12:25:00Z"
}
```

### Error Responses

**400 Bad Request**
```json
{
  "status": "error",
  "error": "invalid_parameter",
  "message": "Invalid sort_by field: 'invalid_field'",
  "valid_options": ["closed_at", "opened_at", "realized_pnl", ...]
}
```

**422 Unprocessable Entity**
```json
{
  "status": "error",
  "error": "validation_error",
  "message": "confidence_min must be between 0 and 100",
  "field": "confidence_min",
  "value": 150
}
```

### Example Requests

```bash
# Get all trades
GET /api/explorer/trades

# Filter by symbol and confidence
GET /api/explorer/trades?symbol=BTCUSDT&confidence_min=70

# Sort by PnL descending
GET /api/explorer/trades?sort_by=realized_pnl&sort_order=desc

# Filter by date range
GET /api/explorer/trades?date_from=2026-07-01&date_to=2026-07-06

# Complex filter: bullish regime, high confidence, winning trades
GET /api/explorer/trades?regime=bullish_trending&confidence_min=70&pnl_min=0

# Page 2 with larger page size
GET /api/explorer/trades?page=2&page_size=100
```

---

## 2. Trade Detail

**Endpoint:** `GET /api/explorer/trades/:id`

**Purpose:** Get comprehensive details for a single trade.

### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | integer | Yes | Trade ID (paper_positions.id) |

### Response Schema

```json
{
  "status": "success",
  "trade": {
    "id": 42,
    "symbol": "BTCUSDT",
    "direction": "LONG",
    "status": "TP_HIT",
    
    "prices": {
      "entry": 65000.0,
      "exit": 67000.0,
      "stop_loss": 64350.0,
      "take_profit": 67500.0,
      "current": 67000.0
    },
    
    "position": {
      "size_usdt": 100.0,
      "qty": 0.001538,
      "realized_pnl": 3.08,
      "pnl_pct": 3.08
    },
    
    "timing": {
      "opened_at": "2026-07-01T08:30:00Z",
      "closed_at": "2026-07-02T14:15:00Z",
      "duration_hours": 29.75,
      "duration_human": "1d 5h 45m"
    },
    
    "execution_intelligence": {
      "mae": -0.012,
      "mae_pct": -1.2,
      "mae_timestamp": "2026-07-01T10:15:00Z",
      "mfe": 0.045,
      "mfe_pct": 4.5,
      "mfe_timestamp": "2026-07-02T12:00:00Z",
      "profit_capture_ratio": 0.68,
      "eqs": 78,
      "execution_classification": "MODEL_CORRECT_EXECUTION_CORRECT",
      "final_exit_reason": "TP_HIT",
      "lost_opportunity_pct": 1.42
    },
    
    "execution_policy": {
      "policy": "TRAILING",
      "trailing_stop_activated": true,
      "break_even_triggered": true,
      "sl_move_count": 3,
      "additional_profit_saved": 0.8
    },
    
    "signal_attribution": {
      "signal_id": 1234,
      "confidence": 72,
      "regime": "bullish_trending",
      "timeframe": "1h",
      "signal_direction": "LONG",
      "signal_timestamp": "2026-07-01T08:00:00Z",
      "probabilities": {
        "short": 0.15,
        "neutral": 0.13,
        "long": 0.72
      },
      "execution_edge": 0.35
    },
    
    "risk_metrics": {
      "initial_risk": 650.0,
      "risk_multiple": 4.74,
      "risk_reward_ratio": 1.77
    }
  },
  "timestamp": "2026-07-06T12:25:00Z"
}
```

### Error Responses

**404 Not Found**
```json
{
  "status": "error",
  "error": "trade_not_found",
  "message": "Trade with id 99999 not found",
  "trade_id": 99999
}
```

### Example Requests

```bash
# Get trade detail
GET /api/explorer/trades/42
```

---

## 3. Analytics

**Endpoint:** `GET /api/explorer/analytics`

**Purpose:** Compute aggregated analytics for filtered trades.

### Query Parameters

Accepts same filter parameters as `/explorer/trades` endpoint (symbol, status, confidence_min, etc.)

### Response Schema

```json
{
  "status": "success",
  "filters_applied": {
    "symbol": "BTCUSDT",
    "confidence_min": 70
  },
  "summary": {
    "total_trades": 45,
    "win_rate": 62.2,
    "total_pnl": 245.67,
    "avg_pnl": 5.46,
    "profit_factor": 2.34,
    "expectancy": 5.46,
    "sharpe_ratio": 1.82,
    "avg_hold_hours": 32.5,
    "avg_eqs": 72.3
  },
  "by_confidence": {
    "60-69%": {
      "total_trades": 12,
      "win_rate": 58.3,
      "total_pnl": 45.20,
      "avg_pnl": 3.77,
      "profit_factor": 1.95
    },
    "70-79%": {
      "total_trades": 22,
      "win_rate": 63.6,
      "total_pnl": 134.50,
      "avg_pnl": 6.11,
      "profit_factor": 2.45
    },
    "80-89%": {
      "total_trades": 11,
      "win_rate": 63.6,
      "total_pnl": 65.97,
      "avg_pnl": 6.00,
      "profit_factor": 2.68
    }
  },
  "by_regime": {
    "bullish_trending": {
      "total_trades": 18,
      "win_rate": 72.2,
      "total_pnl": 156.30,
      "avg_pnl": 8.68
    },
    "neutral": {
      "total_trades": 15,
      "win_rate": 53.3,
      "total_pnl": 42.15,
      "avg_pnl": 2.81
    },
    "bearish_trending": {
      "total_trades": 12,
      "win_rate": 58.3,
      "total_pnl": 47.22,
      "avg_pnl": 3.94
    }
  },
  "by_execution_policy": {
    "FIXED_SL": {
      "total_trades": 15,
      "win_rate": 53.3,
      "avg_pnl": 3.20,
      "avg_eqs": 65.2
    },
    "BREAK_EVEN": {
      "total_trades": 12,
      "win_rate": 66.7,
      "avg_pnl": 5.80,
      "avg_eqs": 74.5
    },
    "TRAILING": {
      "total_trades": 18,
      "win_rate": 66.7,
      "avg_pnl": 7.50,
      "avg_eqs": 78.9
    }
  },
  "execution_classifications": {
    "MODEL_CORRECT_EXECUTION_CORRECT": 25,
    "MODEL_CORRECT_EXECUTION_WEAK": 8,
    "MODEL_WEAK_EXECUTION_CORRECT": 7,
    "MODEL_WEAK_EXECUTION_WEAK": 5
  },
  "exit_reasons": {
    "TP_HIT": 28,
    "SL_HIT": 12,
    "EXPIRED": 3,
    "MANUAL_CLOSE": 2
  },
  "timestamp": "2026-07-06T12:25:00Z"
}
```

### Example Requests

```bash
# Overall analytics
GET /api/explorer/analytics

# Analytics for high-confidence trades
GET /api/explorer/analytics?confidence_min=70

# Analytics for specific regime
GET /api/explorer/analytics?regime=bullish_trending

# Analytics for date range
GET /api/explorer/analytics?date_from=2026-07-01&date_to=2026-07-06
```

---

## 4. Filter Options

**Endpoint:** `GET /api/explorer/filters`

**Purpose:** Get available values for filter dropdowns (symbols, regimes, etc.)

### Response Schema

```json
{
  "status": "success",
  "filters": {
    "symbols": [
      "BTCUSDT",
      "ETHUSDT",
      "SOLUSDT",
      "BNBUSDT"
    ],
    "statuses": [
      "TP_HIT",
      "SL_HIT",
      "EXPIRED",
      "MANUAL_CLOSE"
    ],
    "directions": [
      "LONG",
      "SHORT"
    ],
    "regimes": [
      "bullish_trending",
      "bearish_trending",
      "neutral",
      "high_volatility"
    ],
    "timeframes": [
      "1h",
      "4h",
      "1d"
    ],
    "execution_policies": [
      "FIXED_SL",
      "BREAK_EVEN",
      "TRAILING"
    ],
    "confidence_range": {
      "min": 55,
      "max": 88
    },
    "pnl_range": {
      "min": -45.20,
      "max": 123.50
    },
    "date_range": {
      "earliest": "2026-06-01T00:00:00Z",
      "latest": "2026-07-06T12:25:00Z"
    }
  },
  "trade_count": 156,
  "timestamp": "2026-07-06T12:25:00Z"
}
```

### Example Request

```bash
GET /api/explorer/filters
```

---

## Data Models

### TradeListItem

Lightweight trade representation for list view.

```typescript
interface TradeListItem {
  id: number;
  symbol: string;
  direction: "LONG" | "SHORT";
  status: "TP_HIT" | "SL_HIT" | "EXPIRED" | "MANUAL_CLOSE";
  entry_price: number;
  exit_price: number;
  size_usdt: number;
  qty: number;
  realized_pnl: number;
  pnl_pct: number;
  opened_at: string;
  closed_at: string;
  duration_hours: number;
  
  mae: number;
  mfe: number;
  profit_capture_ratio: number;
  eqs: number;
  execution_classification: ExecutionClassification;
  final_exit_reason: string;
  
  confidence: number;
  regime: string;
  timeframe: string;
  execution_edge: number;
  execution_policy: ExecutionPolicy;
  trailing_stop_activated: boolean;
  sl_move_count: number;
  break_even_triggered: boolean;
  
  signal_id: number | null;
  signal_direction: string | null;
  signal_timestamp: string | null;
}
```

### TradeDetail

Full trade representation with nested objects.

```typescript
interface TradeDetail {
  id: number;
  symbol: string;
  direction: "LONG" | "SHORT";
  status: TradeStatus;
  
  prices: {
    entry: number;
    exit: number;
    stop_loss: number | null;
    take_profit: number | null;
    current: number;
  };
  
  position: {
    size_usdt: number;
    qty: number;
    realized_pnl: number;
    pnl_pct: number;
  };
  
  timing: {
    opened_at: string;
    closed_at: string;
    duration_hours: number;
    duration_human: string;
  };
  
  execution_intelligence: {
    mae: number;
    mae_pct: number;
    mae_timestamp: string | null;
    mfe: number;
    mfe_pct: number;
    mfe_timestamp: string | null;
    profit_capture_ratio: number;
    eqs: number;
    execution_classification: ExecutionClassification;
    final_exit_reason: string;
    lost_opportunity_pct: number;
  };
  
  execution_policy: {
    policy: ExecutionPolicy;
    trailing_stop_activated: boolean;
    break_even_triggered: boolean;
    sl_move_count: number;
    additional_profit_saved: number | null;
  };
  
  signal_attribution: {
    signal_id: number | null;
    confidence: number;
    regime: string;
    timeframe: string;
    signal_direction: string | null;
    signal_timestamp: string | null;
    probabilities: {
      short: number;
      neutral: number;
      long: number;
    };
    execution_edge: number;
  };
  
  risk_metrics: {
    initial_risk: number;
    risk_multiple: number;
    risk_reward_ratio: number;
  };
}
```

### Enums

```typescript
type TradeStatus = "TP_HIT" | "SL_HIT" | "EXPIRED" | "MANUAL_CLOSE";

type ExecutionPolicy = "OFF" | "FIXED_SL" | "BREAK_EVEN" | "TRAILING";

type ExecutionClassification = 
  | "MODEL_CORRECT_EXECUTION_CORRECT"
  | "MODEL_CORRECT_EXECUTION_WEAK"
  | "MODEL_WEAK_EXECUTION_CORRECT"
  | "MODEL_WEAK_EXECUTION_WEAK"
  | "UNKNOWN";
```

---

## Error Handling

### Standard Error Response

```json
{
  "status": "error",
  "error": "error_code",
  "message": "Human-readable error description",
  "details": {}
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `invalid_parameter` | 400 | Invalid query parameter value |
| `validation_error` | 422 | Parameter validation failed |
| `trade_not_found` | 404 | Trade ID does not exist |
| `database_error` | 500 | Database query failed |
| `internal_error` | 500 | Unexpected server error |

---

## Performance Characteristics

### Expected Latency

| Endpoint | Target | Notes |
|----------|--------|-------|
| `/explorer/trades` | < 500ms | With filters and pagination |
| `/explorer/trades/:id` | < 200ms | Single record lookup |
| `/explorer/analytics` | < 800ms | Aggregation over filtered set |
| `/explorer/filters` | < 300ms | Distinct value queries |

### Optimization Strategies

1. **Indexes:** Composite index on `(status, symbol, regime, confidence, closed_at)`
2. **Caching:** Cache `/explorer/filters` response (5-minute TTL)
3. **Query Limits:** Max page_size = 200 to prevent excessive results
4. **Derived Metrics:** Compute EQS and classification in application layer (not SQL)

---

## Rate Limiting

**Not implemented in MVP.** Research workload, low concurrency.

**Future consideration:** 100 requests/minute per user if abuse detected.

---

## Versioning

API version embedded in response for future compatibility:

```json
{
  "status": "success",
  "api_version": "1.0",
  ...
}
```

**Current version:** 1.0

---

## Implementation Notes

### Backend Service Structure

```python
# ml_service/services/trade_explorer_service.py

from typing import List, Dict, Optional
from pydantic import BaseModel

class TradeFilters(BaseModel):
    symbol: Optional[str] = None
    status: Optional[str] = None
    direction: Optional[str] = None
    regime: Optional[str] = None
    confidence_min: Optional[int] = None
    confidence_max: Optional[int] = None
    pnl_min: Optional[float] = None
    pnl_max: Optional[float] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    eqs_min: Optional[int] = None
    eqs_max: Optional[int] = None

def get_trades(
    filters: TradeFilters,
    sort_by: str = "closed_at",
    sort_order: str = "desc",
    page: int = 1,
    page_size: int = 50
) -> Dict:
    """Query trades with filters, sorting, pagination."""
    pass

def get_trade_detail(trade_id: int) -> Dict:
    """Get comprehensive trade details."""
    pass

def compute_filtered_analytics(filters: TradeFilters) -> Dict:
    """Compute analytics for filtered trade set."""
    pass

def get_filter_dimensions() -> Dict:
    """Get available filter options."""
    pass
```

### Route Registration

```python
# ml_service/api/routes.py

from ml_service.services import trade_explorer_service as explorer

@router.get("/explorer/trades")
async def get_explorer_trades(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    sort_by: str = Query("closed_at"),
    sort_order: str = Query("desc"),
    symbol: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    # ... other filters
) -> Dict:
    filters = explorer.TradeFilters(
        symbol=symbol,
        status=status,
        # ...
    )
    return explorer.get_trades(filters, sort_by, sort_order, page, page_size)

@router.get("/explorer/trades/{trade_id}")
async def get_explorer_trade_detail(trade_id: int) -> Dict:
    return explorer.get_trade_detail(trade_id)

@router.get("/explorer/analytics")
async def get_explorer_analytics(
    symbol: Optional[str] = Query(None),
    # ... filters
) -> Dict:
    filters = explorer.TradeFilters(symbol=symbol, ...)
    return explorer.compute_filtered_analytics(filters)

@router.get("/explorer/filters")
async def get_explorer_filter_options() -> Dict:
    return explorer.get_filter_dimensions()
```

---

## Testing Strategy

### Unit Tests

```python
# tests/test_trade_explorer_service.py

def test_get_trades_no_filters():
    result = explorer.get_trades(
        TradeFilters(), 
        page=1, 
        page_size=10
    )
    assert result["status"] == "success"
    assert len(result["trades"]) <= 10

def test_get_trades_with_symbol_filter():
    filters = TradeFilters(symbol="BTCUSDT")
    result = explorer.get_trades(filters)
    assert all(t["symbol"] == "BTCUSDT" for t in result["trades"])

def test_trade_detail_not_found():
    with pytest.raises(TradeNotFoundError):
        explorer.get_trade_detail(99999)
```

### Integration Tests

```python
# tests/test_explorer_api.py

def test_trades_endpoint_pagination(client):
    response = client.get("/api/explorer/trades?page=1&page_size=10")
    assert response.status_code == 200
    data = response.json()
    assert data["pagination"]["page"] == 1
    assert len(data["trades"]) <= 10

def test_analytics_endpoint(client):
    response = client.get("/api/explorer/analytics?symbol=BTCUSDT")
    assert response.status_code == 200
    data = response.json()
    assert "summary" in data
    assert "by_confidence" in data
```

---

## Security Considerations

1. **SQL Injection:** Use parameterized queries for all filters
2. **Input Validation:** Validate enum values (status, direction) against allowed sets
3. **Rate Limiting:** Not required for MVP (research workload)
4. **Authentication:** Inherit from existing API auth (if configured)

---

## Future Enhancements

### Phase 2
- **Export endpoint:** `GET /explorer/export?format=csv`
- **Comparison endpoint:** `GET /explorer/compare?policy1=FIXED_SL&policy2=TRAILING`
- **Bulk analytics:** `POST /explorer/analytics/bulk` (multiple filter sets)

### Phase 3
- **WebSocket updates:** Real-time trade additions
- **Aggregation caching:** Redis cache for analytics
- **GraphQL support:** Flexible query language

---

## Appendix: SQL Query Examples

### Base Query with Derived Metrics

```sql
SELECT 
    pp.*,
    s.direction as signal_direction,
    s.timestamp as signal_timestamp,
    
    -- EQS calculation
    CASE 
        WHEN pp.size_usdt > 0 THEN
            50 + 
            COALESCE((pp.profit_capture_ratio * 30), 0) +
            CASE WHEN pp.mae < -0.02 THEN (ABS(pp.mae) * -100) ELSE 10 END +
            CASE pp.status
                WHEN 'TP_HIT' THEN 20
                WHEN 'SL_HIT' THEN 5
                ELSE 10 END
        ELSE 0
    END as eqs,
    
    -- Duration in hours
    CAST((julianday(pp.closed_at) - julianday(pp.opened_at)) * 24 AS REAL) as duration_hours,
    
    -- PnL percentage
    CASE WHEN pp.size_usdt > 0 
        THEN (pp.realized_pnl / pp.size_usdt * 100) 
        ELSE 0 END as pnl_pct

FROM paper_positions pp
LEFT JOIN signals s ON pp.signal_id = s.id
WHERE pp.status != 'OPEN'
ORDER BY pp.closed_at DESC
LIMIT 50 OFFSET 0;
```

---

## Summary

Complete REST API specification for Trade Explorer MVP:
- 4 endpoints (list, detail, analytics, filters)
- Comprehensive filtering and sorting
- Pagination support
- Derived metrics (EQS, classifications)
- Ready for frontend implementation

**Next deliverable:** TradeExplorer_Database.md (schema requirements)
