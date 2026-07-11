# MQDS Workspace Patterns Specification

**Sprint**: 4.9  
**Status**: DESIGN COMPLETE  
**Auditor**: Antigravity

---

## 1. Unified Layout Configurations

MQDS workspaces assemble panels into task-specific presets.

```
┌──────────────────────────────────────────────────────────────┐
│  Nav Rail  │  Center View Canvas (Lineage/Plots)             │
│  (48px)    │                                                 │
│            ├─────────────────────────────────────────────────┤
│            │  Console / Logs Console (Resizable bottom pane) │
└────────────┴─────────────────────────────────────────────────┘
```

### 1.1 Validation Workspace
*   *Main canvas*: Walk-forward folds visual tracker.
*   *Side inspector (right)*: Dynamic metric tables (Precision, Recall, F1-Score breakdown per fold).

### 1.2 Calibration Workspace
*   *Main canvas*: Reliability curve plot side-by-side with probability distribution histograms.
*   *Side inspector (right)*: Calibration ECE bucket selectors.

### 1.3 Execution Workspace
*   *Main canvas*: Acceptance rate funnel and slippage scatter plots.
*   *Bottom console*: Raw order logs with execution decision checkmarks.
