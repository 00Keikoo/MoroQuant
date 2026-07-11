# SQLite Database Health Report

**Date**: 2026-07-11  
**Status**: PASS WITH WARNINGS  
**Auditor**: Antigravity

---

## 1. General Database Metrics

The SQLite database `/home/zafka/trade-dashboard/ml_service/storage/database.db` was inspected for storage capacity, integrity, and performance index coverage.

| Parameter | Value | Status | Assessment |
| :--- | :--- | :--- | :--- |
| **File Size** | **164.73 MB** (172,732,416 bytes) | OK | Within limits for local operations. |
| **Integrity Check** | `ok` | **PASS** | No database corruption detected. |
| **Page Size** | 4,096 bytes | OK | Standard default page configuration. |
| **Page Count** | 42,171 | OK | Balanced file sizing. |
| **Freelist Count** | 0 pages | OK | **0.00% Fragmentation**. No immediate `VACUUM` required. |

---

## 2. Table Size & Growth Audit

The following table lists all database tables ordered by row count:

| Table Name | Row Count | Growth Risk |
| :--- | :--- | :--- |
| `ohlcv` | **942,925** | **HIGH**: Grows continuously with historical data ingestion. |
| `signals` | **22,804** | **MEDIUM**: Grows with every prediction run. |
| `signal_reconstruction` | **19,785** | **MEDIUM**: Grows in tandem with signal predictions. |
| `signal_outcomes` | 100 | LOW |
| `execution_decisions` | 44 | LOW |
| `user_trade_history` | 22 | LOW |
| `user_trades` | 10 | LOW |
| `paper_positions` | 6 | LOW |
| `paper_positions_backup_025` | 6 | LOW (Static backup) |
| *Others (equity, registry config, etc.)* | < 5 | LOW |

---

## 3. Relational & Foreign Key Integrity

`PRAGMA foreign_key_check` was run and identified **28 relational integrity violations**:

1.  **`execution_decisions` (ID: 2)**: References `position_id = 2` in `paper_positions`, which does not exist.
2.  **`signal_outcomes` (27 Rows)**: Multiple rows (IDs 18, 21, 24, 27, 30, 33, 36, 39, 42, 45, 48, 50, 53, 54, 55, 56, 67, 69, 71, 74, 76, 77, 78, 82, 84, 86, 88) reference non-existent `signals` records.

---

## 4. Index Coverage Review

All high-impact tables have sufficient indexes.
*   `ohlcv`: Covered by `sqlite_autoindex_ohlcv_1` and `idx_ohlcv_symbol_timeframe`.
*   `signals`: Covered by `idx_signals_symbol_timeframe`, `idx_signals_entry_price`, and `idx_unique_signal`.
*   `execution_decisions`: Covered by `idx_execution_decisions_symbol`, `idx_execution_decisions_decision`, `idx_execution_decisions_created_at`, and `idx_execution_decisions_reason`.

---

## 5. Recommended Actions

*   **Purge Dangling Records**: Run a remediation query to delete or repair orphans in `signal_outcomes` and `execution_decisions` pointing to missing parents.
*   **Establish Partitioning/Retention Policy**: As `ohlcv` nears 1 million rows, queries will slow. Implement a data retention policy (e.g., purge data older than 180 days for non-active symbols).
