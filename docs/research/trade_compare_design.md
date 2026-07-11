# Trade Compare Design Specification

**Sprint**: 4.9A  
**Status**: DESIGN COMPLETE  
**Auditor**: Antigravity

---

## 1. Dual-Trace Visual Comparison

Researchers can select two trades in the Forensics Explorer list to compare metrics and execution parameters side-by-side.

| Dimension | Trade Alpha (ID: 981) | Trade Beta (ID: 1024) | Delta / Assessment |
| :--- | :--- | :--- | :--- |
| **Symbol / Direction**| BTCUSDT / LONG | BTCUSDT / LONG | Identical strategy context. |
| **PnL (%)** | **+1.95%** | **-0.50%** | Alpha outperformed by 2.45%. |
| **Duration** | 2h 15m | 8h 40m | Beta held during flat regime. |
| **Confidence** | 85 (High) | 61 (Medium) | Alpha had higher signal support. |
| **Market Regime** | `TRENDING_LONG` | `RANGE` | Beta was caught in mean reversion. |
| **Slippage (%)** | 0.05% | 0.28% | **Beta suffered high slippage**. |
| **Latency (ms)** | 120ms | 450ms | **Beta suffered execution delay**. |

---

## 2. Feature & Model Snapshot Diff

Clicking "Compare Features" highlights row discrepancies:
*   Red rows indicate feature values that diverged significantly (e.g. `RSI_14` was 62.4 in Alpha vs 41.2 in Beta).
*   Model configuration diffs highlight if different model hyperparameter sets were active.
