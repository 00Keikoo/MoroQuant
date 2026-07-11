# Research Timeline UI/UX Design Specification

**Sprint**: 4.7A  
**Status**: DESIGN COMPLETE  
**Auditor**: Antigravity

---

## 1. UI/UX Interface Design

The Research Timeline is the landing page and command center of MoroQuant Lab, presenting a vertical chronological log of events nested alongside model run details.

### 1.1 Layout Grid
*   **Split Pane View**:
    *   *Left Pane (35% width)*: Chronological Event Stream with Live Feed updates.
    *   *Right Pane (65% width)*: Selected node details, lineage graph tracker, and metrics validation card.

---

## 2. Interaction Details

### 2.1 Timeline Navigation Flow
Researchers navigate the timeline using standard filter panels:
*   **Event Filtering**: Filter by type (`TRAINING`, `VALIDATION`, `PROMOTION`, `FAILURES`).
*   **Time Range**: Quick-select options (Last Hour, 24 Hours, 7 Days, Custom range).

### 2.2 Expand/Collapse Nodes
*   Hovering over any timeline node expands a mini-hovercard showing primary metrics (e.g. F1-score, ECE, or Dataset source).
*   Clicking "Expand details" updates the Right Pane, opening deep-dive widgets for validation and calibration outcomes.

### 2.3 Progress Visualization
Active runs display a circular progress tracker indicating the active stage:
*   `TRAINING` (pulsing blue outline)
*   `VALIDATING` (pulsing orange outline)
*   `CALIBRATING` (pulsing purple outline)

### 2.4 Compare Timeline
Allows side-by-side comparison of two experiment lifecycles:
*   Visual diff highlighting differences in parameters, dataset versions, and output performance.

### 2.5 Live Timeline
A WebSocket-driven chronological feed. When models update in the background (via scheduler or worker threads), new events roll in dynamically from the top.

### 2.6 Time Travel
A timeline slider control at the bottom. Sliding backwards reconstructs the platform's state (e.g. showing only models active as of July 1st, 2026).
