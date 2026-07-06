# Trade Explorer - Data Availability Matrix

**Sprint 3, Task 3.1**  
**Date:** 2026-07-06  
**Status:** Design Phase

## Overview

This matrix maps Trade Explorer requirements to current data availability in the paper trading system.

## Legend

- ✅ **Available** - Data exists and is accessible
- ⚠️ **Partial** - Data exists but needs enhancement
- ❌ **Missing** - Data does not exist or is not captured
- 🔄 **Derived** - Can be computed from existing data

---

## Core Trade Data

| Data Field | Status | Source | Notes |
|------------|--------|--------|-------|
| Position ID | ✅ | `paper_positions.id` | Primary key |
| Symbol | ✅ | `paper_positions.symbol` | Trading pair |
| Direction | ✅ | `paper_positions.direction` | LONG/SHORT |
| Entry Price | ✅ | `paper_positions.entry_price` | Captured at open |
| Exit Price | ✅ | `paper_positions.current_price` | Last price at close |
| Position Size (USDT) | ✅ | `paper_positions.size_usdt` | Risk allocation |
| Quantity | ✅ | `paper_positions.qty` | Asset quantity |
| Realized PnL | ✅ | `paper_positions.realized_pnl` | Final profit/loss |
| Open Timestamp | ✅ | `paper_positions.opened_at` | Entry time |
| Close Timestamp | ✅ | `paper_positions.closed_at` | Exit time (if closed) |
| Status | ✅ | `paper_positions.status` | OPEN, TP_HIT, SL_HIT, EXPIRED, MANUAL_CLOSE |
| Duration | 🔄 | Computed | `closed_at - opened_at` |
| PnL Percentage | 🔄 | Computed | `realized_pnl / size_usdt * 100` |

---

## Execution Intelligence

| Data Field | Status | Source | Notes |
|------------|--------|--------|-------|
| MAE (Max Adverse Excursion) | ✅ | `paper_positions.mae` | Worst drawdown % |
| MFE (Max Favorable Excursion) | ✅ | `paper_positions.mfe` | Best profit % |
| MAE Timestamp | ✅ | `paper_positions.mae_timestamp` | When MAE occurred |
| MFE Timestamp | ✅ | `paper_positions.mfe_timestamp` | When MFE occurred |
| Profit Capture Ratio | ✅ | `paper_positions.profit_capture_ratio` | Realized / MFE |
| Final Exit Reason | ✅ | `paper_positions.final_exit_reason` | TP_HIT, SL_HIT, etc. |
| Execution Policy | ✅ | `paper_positions.execution_policy` | OFF, FIXED_SL, BREAK_EVEN, TRAILING |
| Trailing Stop Activated | ✅ | `paper_positions.trailing_stop_activated` | Boolean flag |
| SL Move Count | ✅ | `paper_positions.sl_move_count` | Number of SL adjustments |
| Break-Even Triggered | ✅ | `paper_positions.break_even_triggered` | Boolean flag |
| Stop Loss | ✅ | `paper_positions.stop_loss` | SL price level |
| Take Profit | ✅ | `paper_positions.take_profit` | TP price level |
| Execution Quality Score (EQS) | 🔄 | Derived | Computed from MAE/MFE/PCR |
| Execution Classification | 🔄 | Derived | MODEL_CORRECT_EXECUTION_CORRECT, etc. |
| Lost Opportunity | 🔄 | Computed | `MFE - profit_capture_ratio` |

---

## Signal Attribution

| Data Field | Status | Source | Notes |
|------------|--------|--------|-------|
| Signal ID | ✅ | `paper_positions.signal_id` | Link to signals table |
| Confidence | ✅ | `paper_positions.confidence` | Model confidence (0-100) |
| Regime | ✅ | `paper_positions.regime` | Market regime at entry |
| Timeframe | ✅ | `paper_positions.timeframe` | Signal timeframe |
| Probability - Short | ✅ | `paper_positions.prob_short` | Model probability |
| Probability - Neutral | ✅ | `paper_positions.prob_neutral` | Model probability |
| Probability - Long | ✅ | `paper_positions.prob_long` | Model probability |
| Execution Edge | ✅ | `paper_positions.execution_edge` | Max prob - 2nd max prob |
| Skip Reason | ✅ | `paper_positions.skip_reason` | Why position wasn't opened |
| Signal Direction | ⚠️ | `signals.direction` | Requires JOIN |
| Signal Timestamp | ⚠️ | `signals.timestamp` | Requires JOIN |
| Signal Created At | ⚠️ | `signals.created_at` | Requires JOIN |

---

## Price History (MISSING)

| Data Field | Status | Source | Notes |
|------------|--------|--------|-------|
| Intra-Trade Price Series | ❌ | Not captured | Price ticks during position lifecycle |
| Price Update Frequency | ❌ | Not captured | When prices were fetched |
| Bid/Ask Spread | ❌ | Not captured | Execution slippage data |
| Mark Price History | ❌ | Not captured | Historical mark prices |
| Funding Rate History | ❌ | Not captured | Perpetual funding costs |

**Impact:** Cannot reconstruct exact price paths or analyze intra-trade behavior beyond MAE/MFE.

---

## Risk Metrics

| Data Field | Status | Source | Notes |
|------------|--------|--------|-------|
| Initial Risk (R) | 🔄 | Computed | `entry_price - stop_loss` |
| Risk Multiple | 🔄 | Computed | `realized_pnl / initial_risk` |
| Risk-Adjusted Return | 🔄 | Computed | PnL / risk allocation |
| Position Risk % | 🔄 | Config | From `RISK_PER_TRADE_PCT` (1%) |
| Account Balance at Entry | ⚠️ | Indirect | Via `paper_equity_history` snapshots |
| Account Equity at Entry | ⚠️ | Indirect | Via `paper_equity_history` snapshots |
| Drawdown from Peak | ❌ | Not tracked | Per-position equity curve impact |

**Impact:** Basic risk metrics available, advanced portfolio-level risk attribution needs development.

---

## Portfolio Context

| Data Field | Status | Source | Notes |
|------------|--------|--------|-------|
| Concurrent Open Positions | 🔄 | Query | Count of OPEN positions at same time |
| Portfolio Exposure | 🔄 | Query | Sum of open position sizes |
| Correlation Risk | ❌ | Not tracked | Multi-asset correlation |
| Sequence of Trades | ✅ | Sort by `opened_at` | Trade ordering |
| Win/Loss Streaks | 🔄 | Computed | Consecutive wins/losses |
| Running Balance | ⚠️ | `paper_equity_history` | 5-minute snapshots (not per-trade) |

---

## Performance Attribution

| Data Field | Status | Source | Notes |
|------------|--------|--------|-------|
| Win Rate by Confidence | 🔄 | Analytics | Available via `compute_confidence_analytics()` |
| Win Rate by Regime | 🔄 | Analytics | Available via `compute_regime_analytics()` |
| Win Rate by Symbol | 🔄 | Query | Group by symbol |
| Win Rate by Timeframe | 🔄 | Query | Group by timeframe |
| Win Rate by Execution Policy | 🔄 | Query | Group by execution_policy |
| Win Rate by Exit Reason | 🔄 | Query | Group by final_exit_reason |
| Average Hold Time | 🔄 | Analytics | Available in `compute_paper_analytics()` |
| Profit Factor | 🔄 | Analytics | Available in analytics |
| Sharpe Ratio | 🔄 | Analytics | Available via `compute_sharpe_ratio()` |
| Expectancy | 🔄 | Analytics | Available in analytics |

---

## Execution Research

| Data Field | Status | Source | Notes |
|------------|--------|--------|-------|
| Trailing Stop Effectiveness | 🔄 | Computed | Compare trailing vs fixed |
| Break-Even Save Rate | 🔄 | Query | Count where `break_even_triggered = 1` |
| SL Movement Analysis | 🔄 | Query | Distribution of `sl_move_count` |
| Exit Quality Distribution | 🔄 | Query | Count by `final_exit_reason` |
| Model vs Execution Split | 🔄 | Analytics | Available via `compute_execution_classifications()` |
| Lost Opportunity Analysis | 🔄 | Analytics | Available in execution analytics |

---

## Gap Summary

### Critical Gaps (Block Trade Explorer MVP)
None - core data is available.

### High-Priority Gaps (Limit Advanced Features)
1. **Intra-trade price history** - Limits reconstruction of price paths
2. **Account balance at entry** - Need per-trade equity context (only 5-min snapshots exist)
3. **Drawdown attribution** - Cannot isolate per-position impact on portfolio

### Medium-Priority Gaps (Future Enhancements)
1. **Bid/Ask spread data** - Execution slippage analysis
2. **Funding rate history** - True cost of holding
3. **Correlation risk** - Multi-asset exposure analysis

### Low-Priority Gaps (Nice-to-Have)
1. **Price update frequency logs** - Latency analysis
2. **Model metadata enrichment** - Better signal JOIN data

---

## Recommendations

### Phase 1: Use Existing Data
Build Trade Explorer MVP using available data:
- Position details with MAE/MFE/PCR
- Execution intelligence metrics
- Signal attribution
- Performance analytics
- Derived metrics (EQS, classifications)

### Phase 2: Add Equity Context
Enhance `paper_equity_history` to capture per-trade snapshots:
- Snapshot equity at position open
- Snapshot equity at position close
- Enable portfolio-level risk attribution

### Phase 3: Price History Collection
Add time-series tracking for advanced analysis:
- Store price updates during position lifecycle
- Track MAE/MFE evolution over time
- Enable precise slippage analysis

---

## Data Readiness Score

| Category | Score | Status |
|----------|-------|--------|
| Core Trade Data | 100% | ✅ Ready |
| Execution Intelligence | 100% | ✅ Ready |
| Signal Attribution | 90% | ✅ Ready (needs JOINs) |
| Risk Metrics | 70% | ⚠️ Basic ready, advanced needs work |
| Portfolio Context | 60% | ⚠️ Partial, gaps in real-time equity |
| Performance Attribution | 95% | ✅ Ready |
| Execution Research | 100% | ✅ Ready |
| **Overall** | **88%** | ✅ **MVP Ready** |

**Conclusion:** Paper trading system has sufficient data for a robust Trade Explorer MVP. Advanced features (portfolio attribution, price path reconstruction) require schema enhancements.
