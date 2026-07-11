# ADR-020: MoroQuant Design System (MQDS)

## Status
Proposed

## Context
As MoroQuant evolves into an institutional-grade quantitative research workstation, we need a single, cohesive design language. Using ad-hoc styling results in visual inconsistencies, code duplication, and low information density. We must establish the MoroQuant Design System (MQDS) as the system's official visual language.

## Decision
1.  **MQDS Adoption**: Adopt MQDS as the sole UI language across all current and future screens.
2.  **Visual DNA**: Standardize on high-density, keyboard-first, terminal-adjacent UI patterns modeled after Weights & Biases, Grafana, and Bloomberg Terminal.
3.  **UI Implementation Gating**: Any frontend developer must verify component structures against the MQDS design specifications prior to checking in production views.

## Consequences
*   **Benefits**:
    *   Unified look-and-feel across all workspaces.
    *   Fast layout assemblies using pre-designed spatial foundations.
    *   Strict adherence to high information-density patterns.
*   **Trade-offs**:
    *   Increases initial design overhead for new experimental features.
