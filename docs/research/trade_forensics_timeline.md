# Trade Forensics Timeline Specification

**Sprint**: 4.9A  
**Status**: DESIGN COMPLETE  
**Auditor**: Antigravity

---

## 1. Trade Lifecycle States

A trade's forensic timeline logs all events chronologically:

1.  **`SIGNAL GENERATED`**: Model output triggers prediction.
2.  **`ENTRY`**: Order dispatched to the exchange api buffer.
3.  **`EXECUTION`**: Order filled. Inception of position.
4.  **`FLOATING`**: Position active; real-time unrealized PnL updates.
5.  **`PARTIAL CLOSE`**: Optional order reducing exposure.
6.  **`EXIT`**: Target hit (TP/SL) or manual close executed.
7.  **`REVIEW`**: Post-trade assessment and AI review generation.
8.  **`ARCHIVED`**: Locked, read-only state.

---

## 2. Chronological Timeline Visualization

```
[14:02:11.025] 🔔 SIGNAL GENERATED: Buy BTCUSDT, Confidence 85%
[14:02:11.080] 📤 ENTRY ORDER SENT: Size 0.02 BTC, Price 50000.0
[14:02:11.200] ⚡ EXECUTION FILL: Filled at 50025.0 (Slippage: +0.05%, Latency: 120ms)
[14:15:00.000] 📊 REGIME CHANGE DETECTED: TRENDING_LONG ──► RANGE
[14:30:12.440] 🎯 EXIT FILL (TP_HIT): Sold at 52000.0 (PnL: +1.95%)
[14:35:00.000] 🤖 AI REVIEW COMPLETED: Decision quality rated PASS
```
