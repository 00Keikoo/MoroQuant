# Outcome Evaluation Logic Audit
**MoroQuant ML Trading Platform**

This document details the audit of the multi-checkpoint outcome evaluation logic, focusing on premature classification risks, final outcome consistency, duplicate/overwrite risks, and metric biases.

---

## Part 1: Checkpoint Logic & Premature Classification

### 1. The Evaluation Flow
The accelerated outcome collection flow in `evaluate_signal_with_checkpoints()` iterates through the defined checkpoints (`[1, 4, 12, 24, 48]` hours) in ascending order. For each checkpoint, it:
1. Calculates the corresponding window (`timeout_days = hours / 24.0`).
2. Scans forward through the `ohlcv` table using `evaluate_outcome()`.
3. Marks the checkpoint as checked in the database using `_mark_checkpoint_checked()`.
4. If a resolution (WIN/LOSS) occurs, it exits early. Otherwise, it continues looping.
5. If all checkpoints yield `timeout`, it returns `timeout`.

### 2. Premature Timeout Risk: **YES (CRITICAL)**
A signal can be prematurely and permanently classified as a `TIMEOUT` due to two overlapping issues:

#### A. Lack of Real-Time Candle Availability
If a signal was generated recently (e.g., 6 hours ago) or if there is a data synchronization lag (e.g., OHLCV data is missing for the last 24 hours):
*   When evaluating the 12h, 24h, and 48h checkpoints, `evaluate_outcome()` is called with those large windows.
*   However, since forward OHLCV candles only exist up to 6 hours, the database query returns only the available 6 hours of candles.
*   Because the TP or SL boundaries were not hit in those 6 hours of available candles, `evaluate_outcome()` returns `timeout`.
*   The system then marks all of these checkpoints (12h, 24h, 48h) as checked (`checked_at_Xh = 1`) and saves `outcome = 'timeout'` to the database.

#### B. Permanent Exclusion from Pending List
The `get_pending_signals()` query selects signals to evaluate using:
```sql
SELECT s.id
FROM signals s
LEFT JOIN signal_outcomes so ON s.id = so.signal_id
WHERE s.entry_price IS NOT NULL
  AND s.direction != 'neutral'
  AND so.id IS NULL -- Excludes any signal that has a record in signal_outcomes
```
As soon as `_mark_checkpoint_checked()` or `save_outcome()` writes a record to `signal_outcomes` (even with a NULL outcome or a premature `timeout`), a row exists (`so.id IS NOT NULL`). 
*   **Result:** The signal is immediately and permanently removed from the pending evaluation list.
*   **Consequence:** When the missing OHLCV candles are subsequently synced, the signal will **never** be evaluated again, locking in the premature `TIMEOUT`.

---

## Part 2: Final Outcome Consistency

### 1. Outcomes Past 48 Hours: **TIMEOUT**
If a Take Profit (TP) or Stop Loss (SL) hits after 48 hours but before the final 7-day expiry window:
*   The outcome **will remain TIMEOUT** and will **never** be classified as a WIN or LOSS.

### 2. Code Path Analysis
In `ml_service/analytics/outcome_engine.py`:
1.  `evaluate_pending_outcomes()` invokes `evaluate_signal_with_checkpoints(signal_id, check_intervals_hours)` (lines 341-343).
2.  `evaluate_signal_with_checkpoints()` defaults to `check_intervals_hours = [1, 4, 12, 24, 48]` (lines 323, 374).
3.  The loop iterates over these check intervals (line 403). The maximum value evaluated is **48 hours**.
4.  The `timeout_days` argument passed to `evaluate_outcome()` for the final iteration is:
    ```python
    timeout_days = hours / 24.0 # For hours = 48, timeout_days = 2.0
    ```
5.  In `evaluate_outcome()` (lines 134-135):
    ```python
    timeout_ms = timeout_days * 24 * 60 * 60 * 1000 # 2.0 * 24 * 60 * 60 * 1000 = 172,800,000 ms (48h)
    max_timestamp = entry_timestamp + timeout_ms
    ```
6.  The database query scans candles only up to `max_timestamp` (48 hours after entry) (lines 138-144). Any candles or TP/SL hits beyond 48 hours are completely ignored.
7.  Since no TP/SL was hit within the 48-hour window, `evaluate_outcome()` returns `('timeout', None, None, mfe, mae)` (line 198).
8.  `evaluate_signal_with_checkpoints()` returns a `SignalOutcome` with `outcome='timeout'` (line 456).
9.  This is saved to the DB, locking the record. The default 7-day (168-hour) expiry window defined in `OutcomeEngine.TIMEOUT_DAYS = 7` is bypassed entirely.

---

## Part 3: Double Count Risk

*   **Duplicate Outcomes (Risk: None):** The `signal_outcomes` table has a `UNIQUE(signal_id)` constraint. Both `save_outcome()` and `_mark_checkpoint_checked()` use `INSERT ... ON CONFLICT(signal_id) DO UPDATE`, preventing duplicate rows.
*   **Overwritten Outcomes (Risk: None):** Once a signal is resolved and saved to the database, it is excluded from `get_pending_signals()`, meaning its outcome cannot be overwritten.
*   **Inconsistent/Corrupted Outcomes (Risk: High):** If `_mark_checkpoint_checked()` executes for an early checkpoint, it inserts a partial row with `checked_at_Xh = 1` and `outcome = NULL`. This entry immediately satisfies the `so.id IS NOT NULL` condition in the pending query, halting any future evaluation of subsequent checkpoints.

---

## Part 4: Dataset Integrity & Metric Bias

Accelerated checkpoints introduce severe systematic biases into performance metrics:

1.  **Underestimated Win Rate:** Since any trade resolved between 48 hours and 7 days is forced into a `TIMEOUT` (effectively a non-win), the calculated Win Rate is artificially deflated.
2.  **Distorted Profit Factor:** Long-duration winning trades (which often take more than 48 hours to hit TP) are categorized as timeouts, omitting their gross profits. This heavily deflates the Profit Factor.
3.  **Skewed Expectancy:** The exclusion of late-stage wins/losses and the inflation of timeouts biases the average trade expectancy downward, presenting an inaccurate picture of model edge.
4.  **Data-Lag Selection Bias:** Signals generated within 48 hours of a data synchronization gap are permanently corrupted as timeouts, creating a bias where periods of poor database sync appear to have lower model performance.
