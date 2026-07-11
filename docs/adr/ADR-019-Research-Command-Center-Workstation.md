# ADR-019: Research Command Center Workstation

## Status
Proposed

## Context
Standard admin dashboards fail to provide the interface structure needed for advanced quantitative trading research. Researchers need an operating-system-like workstation layout that facilitates deep-dive comparative analysis, lineage tracking, and processing queue state management. We need to formalize this design paradigm for the MoroQuant Lab.

## Decision
1.  **Workstation Landing Page**: Set the **Research Command Center** as the primary workbench landing page.
2.  **Terminal-Adjacent UX**: Use high-density layouts (compact charts, unified dark grid lines, tabular summaries, queue streams) instead of generic low-density dashboards.
3.  **Cross-Journey Comparison**: Support unified comparison views across experiments, datasets, validation models, and paper metrics.
4.  **Audit Trail Integration**: Log queue schedules, promotion reviews, and data health monitors to the unified research database.

## Consequences
*   **Benefits**:
    *   Optimized for high-density information analysis.
    *   Speeds up visual evaluation of alpha degradation.
    *   Transparent progression of model promotions.
*   **Trade-offs**:
    *   Steeper learning curve for non-technical users.
