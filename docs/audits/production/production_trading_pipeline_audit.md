# Production Trading Pipeline Audit (Sprint 4.6)

This document presents the full architecture audit of the production trading pipeline to locate the failure preventing new paper trades from opening.

---

## 1. Pipeline Execution Audit Matrix

| Pipeline Stage | Is it running? | Is it scheduled? | Is it producing outputs? | Is downstream consuming? | Status / Findings |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1. Exchange** | **YES** | N/A | **YES** | **NO** | Binance Futures API is online and responding to ping/time checks. |
| **2. OHLCV Ingestion** | **NO** | **NO** | **NO** | **NO** | No periodic (e.g. hourly) job exists in the scheduler to fetch and ingest OHLCV data. Ingestion only runs daily during retraining. |
| **3. Database Persistence** | **YES** | N/A | **N/A** | **YES** | SQLite database `ohlcv` table is writeable, but data is stuck at the last daily retraining timestamp. |
| **4. Scheduler** | **YES** | **YES** | **YES** | **YES** | The background scheduler process is running and successfully triggering registered jobs. |
| **5. Signal Generation** | **YES** | **YES** | **NO** | **NO** | The hourly `signal_generation_job` triggers, but fails to generate signals because it consumes stale data from the DB. |
| **6. Predictor** | **YES** | N/A | **NO** | **NO** | Rejects inference inputs because the latest available database candle is stale (older than `tf_seconds * 2` limit). |
| **7. Paper Broker** | **YES** | N/A | **NO** | **NO** | `open_paper_position` is never called because the predictor returns `None` for all signals. |
| **8. Paper Lifecycle** | **YES** | **YES** | **YES** | N/A | Runs minutely, but checks 0 positions since no new positions are being opened and past positions have closed. |

---

## 2. Detailed Stage Audits

### 2.1 Exchange & Connection Freshness
A direct curl test to the Binance Futures endpoint (`https://fapi.binance.com/fapi/v1/time`) succeeds immediately:
```json
{"serverTime": 1783739217955}
```
The exchange connection is fully operational.

### 2.2 OHLCV Ingestion & Scheduler Registration
Inspecting `start_scheduler()` in `ml_service/scheduler.py` reveals the following registered jobs:
- `trade_sync_job` (every 1h) — Syncs Binance trade history (fills), *not* OHLCV candles.
- `adaptive_retrain_job` (every 24h) — Runs training and calls `fetch_all()`.
- `market_dominance_job` (every 1h)
- `signal_generation_job` (every 1h)
- `drift_snapshot_job` (every 1h)
- `paper_lifecycle_job` (every 1m)

There is **no periodic OHLCV ingestion job** registered to run hourly or minutely. As a result, the database is only updated with fresh candles once every 24 hours during retraining.

### 2.3 Predictor Freshness Gate
When the hourly `signal_generation_job` runs, it queries the SQLite database for the latest candles. Because no ingestion job updates the DB, the latest candle is from the last retraining run.

The predictor contains a strict data freshness check (`ml_service/models/predictor.py`):
```python
if age_seconds > max_staleness_seconds:
    logger.error(f"Market data rejected: stale by {age_seconds:.0f}s...")
    return None
```
For the `1h` timeframe, the maximum allowed staleness is 2 hours. Once 2 hours pass after the daily retraining run, the predictor systematically rejects the database's OHLCV data as stale and aborts signal generation.

---

## 3. Root Cause

**The scheduler lacks a periodic (hourly) OHLCV data ingestion job, causing the database to stagnate between daily retraining runs and triggering the predictor's freshness gate to reject the data as stale.**
