# MQDS Component Library Specification

**Sprint**: 4.9  
**Status**: DESIGN COMPLETE  
**Auditor**: Antigravity

---

## 1. Shell Components

### 1.1 Navigation Rail
*   A persistent, ultra-narrow left-side sidebar (48px wide). Icons only.
*   Hovering expands tooltip label with shortcut key (e.g. `G + E` for Experiment Registry).

### 1.2 Workspace Layout (Split-Panel Dock)
*   Flex-box layout split into dynamic resize-draggable zones:
    *   *Side Inspector Panel (left/right)*: Displays model properties, metrics.
    *   *Bottom Console Panel*: Chronological log streams and terminal widgets.
    *   *Central Canvas*: Houses lineage graphs or backtesting statistics.

---

## 2. Card Components

### 2.1 Metric Card
*   Contains 3 elements: KPI Value (20px bold mono), Sparkline chart (background vector preview), Delta trend indicator (`+3.4%` green or `-1.2%` red).

### 2.2 Status Pills & Journey Nodes
*   Compact enums with light transparent background tints matching semantic states (e.g., `VALIDATING` pill: purple text, purple background opacity 10%).

---

## 3. Terminal & Search Components

### 3.1 Command Palette
*   Activated via `Ctrl + K`. A search input modal displaying list of actions: `> Run Backtest`, `> Compare Runs`, `> Filter BTCUSDT`.

### 3.2 Terminal Widgets
*   Rich text console logs displaying stdout from scheduler tasks. Integrates auto-scroll toggle and regex log-filter inputs.
