# Execution Analytics Platform Data Contract Specification

This document details the data schemas, Python dataclasses, and API contracts for the Execution Analytics Platform in Sprint 4.6.

---

## 1. Python Dataclasses (Code Contracts)

All data structures returned from repositories or passed between the service and analytics layers must be immutable dataclasses.

```python
from dataclasses import dataclass
from typing import Dict, List, Optional
from datetime import datetime

@dataclass(frozen=True)
class ExecutionDecisionRecord:
    id: int
    symbol: str
    direction: Optional[str]
    decision: str  # 'ACCEPTED', 'REJECTED'
    reason: Optional[str]  # e.g., 'LOW_CONFIDENCE', 'MAX_POSITIONS'
    reason_detail: Optional[str]
    signal_id: Optional[int]
    position_id: Optional[int]
    confidence: Optional[int]
    regime: Optional[str]
    timeframe: Optional[str]
    execution_edge: Optional[float]
    signal_price: Optional[float]
    execution_price: Optional[float]
    slippage_pct: Optional[float]
    execution_latency_ms: Optional[int]
    created_at: datetime
    source: str  # 'PAPER', 'LIVE', 'BACKTEST', 'RESEARCH'
    execution_policy: Optional[str]

@dataclass(frozen=True)
class TradePositionRecord:
    id: int
    symbol: str
    direction: str  # 'LONG', 'SHORT'
    entry_price: float
    current_price: Optional[float]
    size_usdt: float
    qty: float
    stop_loss: Optional[float]
    take_profit: Optional[float]
    status: str  # 'OPEN', 'TP_HIT', 'SL_HIT', 'EXPIRED', 'MANUAL_CLOSE'
    realized_pnl: float
    opened_at: datetime
    closed_at: Optional[datetime]
    confidence: Optional[int]
    regime: Optional[str]
    timeframe: Optional[str]
    execution_edge: Optional[float]
    mae: float
    mfe: float
    final_exit_reason: Optional[str]
    execution_policy: str
    signal_price: Optional[float]
    execution_price: Optional[float]
    slippage_pct: Optional[float]
    execution_latency_ms: Optional[int]

@dataclass(frozen=True)
class FunnelMetrics:
    signals_generated: int
    accepted_count: int
    rejected_count: int
    opened_positions: int
    closed_positions: int
    acceptance_rate: float
    fill_rate: float

@dataclass(frozen=True)
class QualityMetrics:
    avg_slippage_pct: float
    median_slippage_pct: float
    max_slippage_pct: float
    avg_latency_ms: float
    median_latency_ms: float
    p95_latency_ms: float

@dataclass(frozen=True)
class PerformanceMetrics:
    win_rate: float
    profit_factor: float
    expectancy: float
    total_pnl: float
    avg_holding_duration_seconds: float
    median_holding_duration_seconds: float
    exit_reason_distribution: Dict[str, int]

@dataclass(frozen=True)
class SegmentationGroup:
    segment_value: str
    funnel: FunnelMetrics
    quality: QualityMetrics
    performance: PerformanceMetrics

@dataclass(frozen=True)
class ExecutionAnalyticsReport:
    source: str  # 'PAPER' or 'LIVE'
    start_time: str
    end_time: str
    overall_funnel: FunnelMetrics
    overall_quality: QualityMetrics
    overall_performance: PerformanceMetrics
    rejection_reasons: Dict[str, int]
    by_symbol: List[SegmentationGroup]
    by_regime: List[SegmentationGroup]
    by_policy: List[SegmentationGroup]
```

---

## 2. API Endpoint Specifications

All endpoints are registered under `/api/v1/analytics/execution`.

### 2.1 Get Execution Analytics Report
* **Endpoint**: `GET /api/v1/analytics/execution/report`
* **Query Parameters**:
  - `source`: `str` (required, choice: `PAPER`, `LIVE`)
  - `start_time`: `str` (optional ISO 8601 string)
  - `end_time`: `str` (optional ISO 8601 string)
  - `symbol`: `str` (optional filter)
* **Response Payload (JSON)**:
  ```json
  {
    "source": "PAPER",
    "start_time": "2026-07-01T00:00:00Z",
    "end_time": "2026-07-11T00:00:00Z",
    "overall_funnel": {
      "signals_generated": 1000,
      "accepted_count": 800,
      "rejected_count": 200,
      "opened_positions": 750,
      "closed_positions": 700,
      "acceptance_rate": 0.8,
      "fill_rate": 0.9375
    },
    "overall_quality": {
      "avg_slippage_pct": 0.05,
      "median_slippage_pct": 0.02,
      "max_slippage_pct": 0.45,
      "avg_latency_ms": 124.5,
      "median_latency_ms": 85.0,
      "p95_latency_ms": 350.0
    },
    "overall_performance": {
      "win_rate": 0.58,
      "profit_factor": 1.45,
      "expectancy": 12.50,
      "total_pnl": 8750.0,
      "avg_holding_duration_seconds": 14400.0,
      "median_holding_duration_seconds": 7200.0,
      "exit_reason_distribution": {
        "TP_HIT": 406,
        "SL_HIT": 250,
        "EXPIRED": 30,
        "MANUAL_CLOSE": 14
      }
    },
    "rejection_reasons": {
      "LOW_CONFIDENCE": 120,
      "MAX_POSITIONS": 50,
      "BAD_REGIME": 30,
      "NEGATIVE_EDGE": 0
    },
    "by_symbol": [
      {
        "segment_value": "BTCUSDT",
        "funnel": { ... },
        "quality": { ... },
        "performance": { ... }
      }
    ],
    "by_regime": [
      {
        "segment_value": "TRENDING_LONG",
        "funnel": { ... },
        "quality": { ... },
        "performance": { ... }
      }
    ],
    "by_policy": [
      {
        "segment_value": "TRAILING",
        "funnel": { ... },
        "quality": { ... },
        "performance": { ... }
      }
    ]
  }
  ```

### 2.2 Get Detailed Rejections Log
* **Endpoint**: `GET /api/v1/analytics/execution/rejections`
* **Query Parameters**:
  - `source`: `str` (required, choice: `PAPER`, `LIVE`)
  - `reason`: `str` (optional filter, e.g., `LOW_CONFIDENCE`)
  - `limit`: `int` (default `100`)
* **Response Payload (JSON)**:
  ```json
  [
    {
      "id": 1450,
      "symbol": "BTCUSDT",
      "direction": "LONG",
      "reason": "LOW_CONFIDENCE",
      "reason_detail": "Signal confidence of 45 is below the policy minimum threshold of 60",
      "confidence": 45,
      "regime": "RANGE",
      "created_at": "2026-07-11T09:30:00Z"
    }
  ]
  ```

---

## 3. Data Integrity & Verification Strategy

To guarantee the immutability and accuracy of execution metrics:
1. **Schema Check Constraints**:
   - Database level: Column checks enforce `decision IN ('ACCEPTED', 'REJECTED')`, `source IN ('PAPER', 'LIVE', 'BACKTEST', 'RESEARCH')`.
2. **Missing Data Handling Rules**:
   - Records with null values for execution metadata are omitted from quality averages, preventing skew from un-filled or partial order attempts.
3. **Data Parity Assertion**:
   - `TradeRepository` will run validation checks verifying that:
     $$\text{slippage\_pct} = \frac{\text{execution\_price} - \text{signal\_price}}{\text{signal\_price}} \times 100 \pm 1e^{-6}$$
