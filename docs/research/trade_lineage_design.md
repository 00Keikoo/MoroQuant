# Trade Lineage Design Specification

**Sprint**: 4.9A  
**Status**: DESIGN COMPLETE  
**Auditor**: Antigravity

---

## 1. Visual Provenance Path

Every trade snapshot details its complete history upstream to the source files:

```mermaid
graph TD
    T[Trade: snap_tr_981] --> S[Signal: sig_20084]
    S --> M[Model: candidate_v1.4.2]
    M --> E[Experiment: run_0283]
    E --> DS[Dataset: ds_v2.4.1]
    DS --> FV[Feature Version: feat_v1.0]
    FV --> MD[Raw Market Data: BTCUSDT-1h-binance]
    
    style T fill:#f9f,stroke:#333,stroke-width:2px;
    style MD fill:#bbf,stroke:#333,stroke-width:2px;
```

---

## 2. Interactive Traceability Rules

1.  **Fully Clickable Nodes**: Clicking any lineage node opens its metadata window inside the Right Inspector.
2.  **Highlight Code State**: Clicking the *Model* node highlights the exact Git commit SHA in the inspector, with a click-to-open link targeting the GitHub repository.
3.  **Trace Raw Ingest**: Clicking *Raw Market Data* displays ingestion timestamps, verifying that no data leakage occurred during training folds.
