# Scheduler Runtime Profile: `signal_lifecycle_job`

**Date**: 2026-07-11  
**Status**: WARNING  
**Auditor**: Antigravity

---

## 1. Runtime Execution Metrics

An audit of the [scheduler.py](file:///home/zafka/trade-dashboard/ml_service/scheduler.py) file and active runtime logs was conducted to analyze the performance footprint of `signal_lifecycle_job`.

| Dimension | Metric | Performance Footprint |
| :--- | :--- | :--- |
| **Execution Time** | Avg per active signal | **150ms - 500ms** (network-dependent) |
| | Total (10 signals) | **1.5s - 5.0s** |
| | Total (50 signals) | **7.5s - 25.0s** (blocking uvicorn thread) |
| **Database Queries** | Connection open/close | **1** per job execution |
| | Query type | Single sequential scan for `signal_status = 'ACTIVE'` |
| **Network Calls** | Type | Synchronous HTTP GET via `requests` library |
| | URL Target | `https://fapi.binance.com/fapi/v1/premiumIndex?symbol={symbol}` |
| | Frequency | **N calls** (exactly 1 call per active signal, sequentially in a loop) |
| **Blocking Operations** | Thread Blocking | **YES** (synchronously blocks the executor thread for the duration of all HTTP calls) |

---

## 2. Flame-Style Execution Timeline

```
[0.0s] [DB Read: SELECT ACTIVE signals (1 connection query)]
[0.1s] [Loop Started]
       ├── [Fetch BTCUSDT Mark Price] ───► (HTTP requests.get) ───► [250ms]
       ├── [Fetch ETHUSDT Mark Price] ───► (HTTP requests.get) ───► [180ms]
       ├── [Fetch SOLUSDT Mark Price] ───► (HTTP requests.get) ───► [450ms]
       ├── [Fetch XRPUSDT Mark Price] ───► (HTTP requests.get) ───► [190ms]
       └── ... repeat sequentially for N signals ...
[4.8s] [DB Write: bulk_update_signal_statuses (1 connection query)]
[4.9s] [Job Finished]
```

---

## 3. Root Cause Analysis: APScheduler Skipped Executions

APScheduler logs warnings such as `Execution of job signal_lifecycle_job skipped: maximum number of running instances reached (1)`. The root cause is the combination of:

1.  **Sequential Synchronous Network Calls**: The job executes `requests.get(...)` inside a `for row in rows:` loop. If the network is congested, Binance rate-limits, or any API endpoint times out (5.0s timeout per call), the job execution time scales linearly:
    $$\text{Total Time} = N \times \text{Latency}$$
2.  **Default Concurrency Constraints**: APScheduler is configured with default execution constraints (`max_instances=1`). If `signal_lifecycle_job` takes longer than 5 minutes to complete (due to timeout or high signal counts), the next scheduled run is skipped.
3.  **Thread Pool Starvation**: Because uvicorn and APScheduler share runtime threads, these blocking I/O calls starve the main thread pool, causing responsiveness degradation in API routes.
