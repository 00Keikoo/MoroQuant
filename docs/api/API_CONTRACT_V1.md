# Trade Explorer API Contract v1.0

**Version:** 1.0.0  
**Status:** Stable  
**Effective Date:** 2026-07-06  
**Base URL:** `/api/v1/explorer`

---

## Overview

The Trade Explorer API provides read-only access to paper trading positions, analytics, and metadata. This document serves as the official API contract and governs backward compatibility guarantees.

---

## Endpoints

### 1. List Trades

**Endpoint:** `GET /api/v1/explorer/trades`

**Description:** Query trades with filtering, pagination, and sorting.

**Query Parameters:**

| Parameter | Type | Required | Default | Constraints | Description |
|-----------|------|----------|---------|-------------|-------------|
| `status` | string | No | - | - | Filter by trade status |
| `symbol` | string | No | - | - | Filter by trading symbol |
| `direction` | string | No | - | - | Filter by trade direction |
| `limit` | integer | No | 100 | 1-1000 | Maximum results per page |
| `offset` | integer | No | 0 | ≥0 | Results to skip for pagination |
| `sort_by` | string | No | "opened_at" | - | Column to sort by |
| `sort_order` | string | No | "DESC" | ASC, DESC | Sort order |

**Response:** `200 OK`

```json
{
  "trades": [
    {
      "id": 1,
      "symbol": "BTCUSDT",
      "direction": "LONG",
      "entry_price": 50000.0,
      "current_price": 51000.0,
      "size_usdt": 1000.0,
      "qty": 0.02,
      "stop_loss": 49000.0,
      "take_profit": 52000.0,
      "signal_id": 10,
      "status": "OPEN",
      "realized_pnl": 0.0,
      "opened_at": "2026-07-06T08:00:00",
      "closed_at": null,
      "confidence": 85,
      "regime": "TRENDING",
      "timeframe": "1h"
    }
  ],
  "total": 100,
  "limit": 100,
  "offset": 0
}
```

**Error Responses:**
- `422 Unprocessable Entity` - Invalid query parameters

---

### 2. Get Trade Detail

**Endpoint:** `GET /api/v1/explorer/trades/{trade_id}`

**Description:** Get detailed information about a specific trade, including linked signal if available.

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `trade_id` | integer | Yes | Trade position ID |

**Response:** `200 OK`

```json
{
  "trade": {
    "id": 1,
    "symbol": "BTCUSDT",
    "direction": "LONG",
    "entry_price": 50000.0,
    "current_price": 51000.0,
    "size_usdt": 1000.0,
    "qty": 0.02,
    "stop_loss": 49000.0,
    "take_profit": 52000.0,
    "signal_id": 10,
    "status": "OPEN",
    "realized_pnl": 0.0,
    "opened_at": "2026-07-06T08:00:00",
    "closed_at": null,
    "confidence": 85,
    "regime": "TRENDING",
    "timeframe": "1h"
  },
  "signal": {
    "id": 10,
    "symbol": "BTCUSDT",
    "timeframe": "1h",
    "timestamp": 1720252800,
    "direction": "long",
    "confidence": 85
  }
}
```

**Error Responses:**
- `404 Not Found` - Trade does not exist
- `422 Unprocessable Entity` - Invalid trade_id format

---

### 3. Get Summary

**Endpoint:** `GET /api/v1/explorer/summary`

**Description:** Get aggregated trading performance analytics.

**Response:** `200 OK`

```json
{
  "total_trades": 100,
  "winning_trades": 65,
  "losing_trades": 35,
  "win_rate": 0.65,
  "gross_profit": 25000.0,
  "gross_loss": 8000.0,
  "net_profit": 17000.0,
  "average_profit": 384.62,
  "average_loss": 228.57,
  "average_hold_duration_seconds": 72000.0,
  "average_trade_duration_seconds": 86400.0,
  "largest_win": 1500.0,
  "largest_loss": -800.0,
  "long_count": 58,
  "short_count": 42,
  "open_count": 5,
  "closed_count": 95
}
```

---

### 4. Get Metadata

**Endpoint:** `GET /api/v1/explorer/metadata`

**Description:** Get available filter values for symbols, directions, and statuses.

**Response:** `200 OK`

```json
{
  "symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
  "directions": ["LONG", "SHORT"],
  "statuses": ["OPEN", "TP_HIT", "SL_HIT", "EXPIRED", "MANUAL_CLOSE"]
}
```

---

## Data Models

### TradePosition

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `id` | integer | No | Unique trade identifier |
| `symbol` | string | No | Trading pair symbol |
| `direction` | string | No | Trade direction (LONG, SHORT) |
| `entry_price` | float | No | Entry price |
| `current_price` | float | Yes | Current market price |
| `size_usdt` | float | No | Position size in USDT |
| `qty` | float | No | Position quantity in base asset |
| `stop_loss` | float | Yes | Stop loss price |
| `take_profit` | float | Yes | Take profit price |
| `signal_id` | integer | Yes | Linked signal ID |
| `status` | string | No | Trade status |
| `realized_pnl` | float | No | Realized profit/loss |
| `opened_at` | string | No | ISO 8601 timestamp |
| `closed_at` | string | Yes | ISO 8601 timestamp |
| `confidence` | integer | Yes | Signal confidence (0-100) |
| `regime` | string | Yes | Market regime |
| `timeframe` | string | Yes | Signal timeframe |

### Signal

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `id` | integer | No | Unique signal identifier |
| `symbol` | string | No | Trading pair symbol |
| `timeframe` | string | No | Signal timeframe |
| `timestamp` | integer | No | Unix timestamp |
| `direction` | string | No | Signal direction (long, short, neutral) |
| `confidence` | integer | No | Confidence score (0-100) |

### Summary

| Field | Type | Description |
|-------|------|-------------|
| `total_trades` | integer | Total number of trades |
| `winning_trades` | integer | Number of profitable trades |
| `losing_trades` | integer | Number of losing trades |
| `win_rate` | float | Win rate (0-1) |
| `gross_profit` | float | Total profit from winning trades |
| `gross_loss` | float | Total loss from losing trades |
| `net_profit` | float | Net profit/loss |
| `average_profit` | float | Average profit per winning trade |
| `average_loss` | float | Average loss per losing trade |
| `average_hold_duration_seconds` | float | Average hold time in seconds |
| `average_trade_duration_seconds` | float | Average trade duration in seconds |
| `largest_win` | float | Largest single win |
| `largest_loss` | float | Largest single loss |
| `long_count` | integer | Number of long trades |
| `short_count` | integer | Number of short trades |
| `open_count` | integer | Number of open trades |
| `closed_count` | integer | Number of closed trades |

---

## Backward Compatibility

### Versioning Strategy

This API uses **URL versioning** (`/api/v1/`). Version changes follow these rules:

1. **Major version increment (v1 → v2)** when:
   - Breaking changes to request/response structure
   - Removing endpoints
   - Changing field types
   - Renaming fields

2. **No version change** for:
   - Adding new optional fields
   - Adding new endpoints
   - Adding new query parameters (optional)
   - Internal implementation changes

### Backward Compatibility Guarantees

Within a major version (v1.x), the following are **guaranteed stable**:

- ✅ Endpoint paths
- ✅ Required fields in responses
- ✅ Field data types
- ✅ Field names
- ✅ HTTP status codes for documented scenarios
- ✅ Query parameter names and constraints

The following may change **without breaking compatibility**:

- ✅ New optional response fields may be added
- ✅ New endpoints may be added
- ✅ New optional query parameters may be added
- ✅ Internal implementation details
- ✅ Response field ordering

---

## Deprecation Policy

When an endpoint or field must be deprecated:

1. **Announcement Period:** Minimum 90 days notice via:
   - API changelog
   - Deprecation header in responses: `X-Deprecated-Endpoint: true`
   - Documentation updates

2. **Deprecation Period:** Minimum 180 days of continued support with:
   - Documented migration path
   - Warning headers in responses
   - Both old and new versions available

3. **Removal:** Only in a new major version (v2)

**Example Deprecation Header:**

```
X-Deprecated-Endpoint: true
X-Deprecation-Info: This endpoint will be removed in v2. Use /api/v2/explorer/trades instead.
X-Sunset-Date: 2027-01-06
```

---

## Rate Limiting

**Current Status:** No rate limiting enforced

**Future Consideration:** Rate limits may be introduced with:
- Advance notice (90 days minimum)
- Documented limits in response headers
- Graceful degradation

---

## Error Handling

### Standard Error Response

```json
{
  "detail": "Error message describing what went wrong",
  "status_code": 400
}
```

### HTTP Status Codes

| Code | Meaning | Usage |
|------|---------|-------|
| 200 | OK | Successful request |
| 404 | Not Found | Resource does not exist |
| 422 | Unprocessable Entity | Invalid request parameters |
| 500 | Internal Server Error | Server-side error |

---

## Data Formats

### Timestamps

All timestamps use **ISO 8601 format**: `YYYY-MM-DDTHH:MM:SS`

Example: `2026-07-06T08:00:00`

### Numbers

- Prices and quantities: float with arbitrary precision
- Counts: integer
- Ratios (e.g., win_rate): float between 0 and 1

### Null Handling

- Optional fields may be `null` or omitted
- Required fields will never be `null`

---

## Security

### Authentication

**Current:** No authentication required (internal API)

**Future:** If authentication is added, it will be:
- Introduced as an optional feature first
- Required only after 90-day transition period
- Documented with migration guide

### HTTPS

**Recommendation:** Use HTTPS in production environments

---

## SLA and Support

### Availability

**Target:** 99.9% uptime during business hours

### Response Times

**Target:** 95th percentile < 200ms for all endpoints

### Breaking Changes

**Commitment:** No breaking changes within major version (v1.x)

---

## Changelog

### v1.0.0 (2026-07-06)

- Initial stable release
- Four endpoints: trades list, trade detail, summary, metadata
- Complete OpenAPI specification
- Pagination support
- Filtering and sorting support

---

## Contact

For API questions, issues, or feature requests:
- Technical Documentation: `/docs/api/`
- OpenAPI Specification: `/openapi.json`
- Interactive Documentation: `/docs`

---

## Appendix: Migration Guide

This section will be populated when breaking changes are introduced in future versions.

---

**Document Version:** 1.0.0  
**Last Updated:** 2026-07-06  
**Next Review:** 2027-01-06
