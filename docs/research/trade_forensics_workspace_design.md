# Trade Forensics Workspace Design Specification

**Sprint**: 4.9A  
**Status**: DESIGN COMPLETE  
**Auditor**: Antigravity

---

## 1. Workspace Layout & Navigation

The Trade Forensics Workspace utilizes a high-density, multi-pane docking grid.

```
┌────────────────────────────────────────────────────────┐
│  Nav Rail  │  Active Trade Explorer List               │
│            │  (Rows represent trade run ID hashes)    │
│            ├───────────────────────────────────────────┤
│            │  Visual Trade Replay Canvas               │
│            │  (Timeline scrubber, tick price stream)   │
│            ├───────────────────────────────────────────┤
│            │  Right inspector (AI review, properties)  │
└────────────┴───────────────────────────────────────────┘
```

### 1.1 Panels Configuration
*   **Trade Explorer (Left, 25%)**: Compact, pagination-free list showing: `Symbol`, `PnL (%)`, `Confidence`, `Execution Latency (ms)`.
*   **Replay Canvas (Center, 50%)**: Candlestick charts overlaid with execution markers (`Entry`, `TP`, `SL`, `Exits`).
*   **Property Inspector (Right, 25%)**: Read-only pane detailing model parameters, active features list, and AI post-mortem logs.

---

## 2. Interaction & Keyboard Shortcuts

*   `J` / `K`: Move down/up in the Trade Explorer list.
*   `Space`: Play/pause the trade replay scrubber.
*   `L`: Toggle full-width lineage view.
*   `B`: Bookmark selected trade for team case studies.
*   `F`: Focus search palette (`/symbol`, `/pnl>5`, `/reason=SL_HIT`).
