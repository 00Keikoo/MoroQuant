# Trade Case Study Design Specification

**Sprint**: 4.9A  
**Status**: DESIGN COMPLETE  
**Auditor**: Antigravity

---

## 1. Exportable Research Artifacts

Every audited trade can be compiled into a standardized post-mortem case study document to facilitate sharing findings across quant teams.

### 1.1 Document Structure

*   **1. Executive Summary**: Trade ID, symbol, PnL, duration, win/loss designation.
*   **2. Model & Feature State**: The exact features that triggered the entry. Highlight features with high SHAP impacts.
*   **3. Validation & Calibration Profile**: Out-of-sample metrics at promotion time.
*   **4. Execution Analytics Review**: Slippage latency, slippage percentage, execution policy type.
*   **5. Timeline Log**: Step-by-step audit logs of the position lifecycle.
*   **6. Research Post-Mortem**:
    *   *Lessons Learned*: Did the trade execute per plan? Was there high drawup before exit?
    *   *Recommendations*: Actionable steps (e.g. "Reduce position size in volatile regimes").

### 1.2 Export Engines
*   **Markdown Export**: Raw GFM format including embedded data tables and ASCII sparklines.
*   **PDF Export**: Print-ready styled template featuring clean column layouts and rendered chart blocks.
