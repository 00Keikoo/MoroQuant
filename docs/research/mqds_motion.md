# MQDS Motion Specification

**Sprint**: 4.9  
**Status**: DESIGN COMPLETE  
**Auditor**: Antigravity

---

## 1. Animation Principles

As an institutional research workbench, animations must be **functional, direct, and zero-latency**. Avoid decorative ease-ins that slow down navigation.

| Interaction | Animation Style | Duration | Curve |
| :--- | :--- | :--- | :--- |
| **Tab Transition** | Immediate cut (no fade) | 0ms | Linear |
| **Panel Expand/Collapse** | Slide scale transition | 150ms | Cubic Bezier `(0.25, 1, 0.5, 1)` |
| **Node Selection** | Outline draw animation | 100ms | Ease-out |
| **Graph Zoom** | Vector transform scale | 80ms | Ease-in-out |

---

## 2. Interactive States

### 2.1 Streaming Timeline (Research Chronicle)
*   When a new event arrives via WebSocket, the feed shifts down by the height of one node. The incoming node fades in from `0%` to `100%` opacity in `150ms`.

### 2.2 Node Traversal
*   Clicking a downstream lineage node triggers an animated flow pulse along the connector arrow to highlight the dependency path.
