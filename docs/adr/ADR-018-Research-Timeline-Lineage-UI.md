# ADR-018: Research Timeline & Lineage UI

## Status
Proposed

## Context
Quantitative researchers need a way to inspect model progression from raw data ingest to production deployment. Currently, model development metadata is scattered. We need to introduce a unified **Research Timeline** and **Lineage UI** that acts as the primary landing page of MoroQuant Lab, establishing step-by-step traceability across the entire lifecycle.

## Decision
1.  **Primary Landing Page**: Set the **Research Timeline** as the default dashboard/landing page for the MoroQuant Lab.
2.  **End-to-End Lineage Tracking**: Define an explicit lifecycle trace spanning:
    ```
    Dataset ──► Feature ──► Experiment ──► Validation ──► Calibration ──► Backtest ──► Paper Trading ──► Execution Analytics ──► Promotion ──► Production
    ```
3.  **Visualization Standard**: Standardize on Directed Acyclic Graph (DAG) visual components for interactive lineage tracking.
4.  **Auditability**: Log state transitions chronologically to generate audit logs suitable for compliance.

## Consequences
*   **Benefits**:
    *   Complete visibility from raw data to running strategy.
    *   Traceable audit logs for model risk management.
    *   Identifies exactly where in the pipeline an experiment failed.
*   **Trade-offs**:
    *   Increased frontend complexity to render large DAGs dynamically.
