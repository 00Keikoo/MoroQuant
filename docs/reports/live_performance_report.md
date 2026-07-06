# Production Live Performance Audit Report
**MoroQuant Production ML Trading System**
**Date:** 2026-06-22 12:17:17

---

## Executive Summary
This audit report evaluates the live production performance of MoroQuant's trading system, matching synced Binance Futures trades with generated ML signals and computing key risk-return statistics.

### Performance Metrics Summary

| Metric | Value | Description |
|---|---|---|
| **Total Synced Trades** | 22 | Total number of executions recorded on Binance Futures |
| **Win Rate** | 22.73% | Percentage of profitable trades (net of fees) |
| **Winning / Losing Trades** | 5 / 17 | Ratio of profitable to unprofitable executions |
| **Net Realized Profit** | $1.66 | Total net return in USDT (after commissions) |
| **Average Win / Loss** | $1.37 / $-0.31 | Mean profit per winning trade vs loss per losing trade |
| **Profit Factor** | 1.32 | Gross Profit / Gross Loss ratio |
| **Expectancy** | $0.08 | Expected net return per executed trade |
| **ROI** | 0.0166% | Return on Investment based on $10,000 baseline capital |
| **Max Drawdown** | $2.23 | Largest peak-to-trough drop in equity |
| **Max Drawdown %** | 57.23% | Max drawdown relative to running peak capital |
| **Sharpe Ratio (Annualized)** | 1.07 | Risk-adjusted return metric (using trade-by-trade standard deviation) |
| **Average Hold Time** | 6.35 hrs | Estimated hold duration for completed positions |

---

## Signal-to-Trade Attribution Audit
A total of **22 / 22** trades have been successfully linked to signals (**100% Attribution**).
This has been achieved using a multi-fallback matching pipeline:
1. **Strict Direction Match:** Matches trades to signals of the same symbol and same predicted direction (BUY->long, SELL->short) within timeframe windows (1h = ±90m, 4h = ±4h).
2. **Exit Trade Propagation:** Automatically attributes exit trades (which capture the realized PnL) to the signal associated with the preceding entry trade.
3. **Relaxed Match:** Matches trades to the closest signal ignoring direction, to account for live vs historical model predictions (e.g. after model retrain/promotions).

---

## Closed Trades & Attribution Log

| Trade ID | Time | Symbol | Side | Price | Qty | Realized PnL | Commission | Matched Signal ID | Signal Prediction | Market Regime |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2026-06-16 01:49:58 | HYPEUSDT | BUY | 68.333 | 1.49 | $0.0000 | $0.0509 | #22767 (long - 81%) | long | unknown |
| 2 | 2026-06-16 01:59:06 | ZECUSDT | SELL | 527.81 | 0.01 | $0.0000 | $0.0026 | #22781 (short - 78%) | short | unknown |
| 8 | 2026-06-16 02:19:17 | HYPEUSDT | SELL | 67.332 | 1.49 | $-1.4915 | $0.0502 | #22767 (long - 81%) | long | unknown |
| 9 | 2026-06-16 02:20:19 | ADAUSDT | SELL | 0.1856 | 550.0 | $0.0000 | $0.0510 | #22787 (short - 96%) | short | unknown |
| 10 | 2026-06-16 13:17:51 | ADAUSDT | BUY | 0.1778 | 550.0 | $4.2900 | $0.0489 | #22787 (short - 96%) | short | unknown |
| 11 | 2026-06-16 13:17:55 | ZECUSDT | BUY | 525.24 | 0.099 | $0.2512 | $0.0260 | #22781 (short - 78%) | short | unknown |
| 12 | 2026-06-16 13:20:49 | ADAUSDT | BUY | 0.1776 | 574.0 | $0.0000 | $0.0510 | #22796 (short - 96%) | short | unknown |
| 13 | 2026-06-16 13:22:54 | SOLUSDT | BUY | 73.77 | 1.35 | $0.0000 | $0.0498 | #22769 (short - 97%) | short | unknown |
| 14 | 2026-06-16 20:13:12 | ADAUSDT | SELL | 0.1777 | 574.0 | $0.0574 | $0.0510 | #22796 (short - 96%) | short | unknown |
| 15 | 2026-06-16 20:13:15 | SOLUSDT | SELL | 74.26 | 1.35 | $0.6615 | $0.0501 | #22769 (short - 97%) | short | unknown |
| 16 | 2026-06-16 20:17:29 | ZECUSDT | SELL | 507.58 | 0.197 | $0.0000 | $0.0500 | #22805 (short - 78%) | short | unknown |
| 17 | 2026-06-16 20:18:35 | SUIUSDT | SELL | 0.7921 | 126.2 | $0.0000 | $0.0500 | #22808 (long - 76%) | long | unknown |
| 18 | 2026-06-17 07:28:24 | SUIUSDT | BUY | 0.8007 | 38.0 | $-0.3268 | $0.0152 | #22808 (long - 76%) | long | unknown |
| 22 | 2026-06-17 21:18:57 | SUIUSDT | SELL | 0.7894 | 6.5 | $0.0000 | $0.0026 | #22814 (long - 76%) | long | unknown |
| 28 | 2026-06-17 22:25:26 | SUIUSDT | BUY | 0.7947 | 128.9 | $-0.6832 | $0.0512 | #22814 (long - 76%) | long | unknown |
| 29 | 2026-06-17 23:18:11 | HYPEUSDT | BUY | 76.046 | 1.42 | $0.0000 | $0.0540 | #22775 (long - 89%) | long | unknown |
| 31 | 2026-06-17 23:27:31 | ZECUSDT | BUY | 498.25 | 0.197 | $1.8380 | $0.0491 | #22805 (short - 78%) | short | unknown |
| 32 | 2026-06-17 23:28:34 | LINKUSDT | BUY | 8.357 | 24.02 | $0.0000 | $0.1004 | #22824 (long - 52%) | long | unknown |
| 33 | 2026-06-17 23:52:55 | LINKUSDT | SELL | 8.266 | 2.43 | $-0.2211 | $0.0100 | #22824 (long - 52%) | long | unknown |
| 35 | 2026-06-17 23:56:31 | HYPEUSDT | SELL | 75.41 | 2.67 | $-1.6981 | $0.1007 | #22775 (long - 89%) | long | unknown |
| 36 | 2026-06-18 11:14:19 | ZECUSDT | SELL | 471.91 | 0.215 | $0.0000 | $0.0507 | #22707 (short - 78%) | short | unknown |
| 37 | 2026-06-18 11:17:42 | SUIUSDT | SELL | 0.753 | 125.2 | $0.0000 | $0.0471 | #22829 (long - 76%) | long | unknown |

---
*Report generated automatically by Antigravity.*
