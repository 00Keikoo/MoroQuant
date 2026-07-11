# Institutional Research Workstation Design Specification

**Sprint**: 4.8B  
**Status**: DESIGN COMPLETE  
**Auditor**: Antigravity

---

## 1. Institutional UX Principles

1.  **High Information Density**: Eliminate whitespace. Use grid layouts, compact tables, and micro-charts (sparklines) to present a high volume of metrics.
2.  **Stateless API Dependency**: The interface acts as a visualization overlay of the backend API, containing zero logic or direct database connections.
3.  **Cross-Context State Syncing**: Use global session state keys (e.g. `active_run_id`, `compare_run_ids`, `selected_dataset`) to link dashboards seamlessly.

---

## 2. Workstation Modules

### 2.1 Research Command Center (Landing Page)
*   **Purpose**: The central workspace hub presenting model pipelines, queue summaries, and active alerts.
*   **Layout**: 3-Column high-density grid.
    *   *Col 1 (25%)*: Research Queue & Promotion status cards.
    *   *Col 2 (50%)*: Interactive Lineage Tracker and active model KPIs.
    *   *Col 3 (25%)*: Research Chronicle feed.
*   **KPIs**: Active Workers, F1-Target Delta, ECE System Mean, Weekly Promotions.

### 2.2 Research Chronicle (Global Activity Feed)
*   **Purpose**: GitHub/CI-Timeline style activity feed tracking training jobs, promotions, and data ingest.
*   **Interactions**: Infinite scroll, tag filtering, clicking an item navigates directly to the model's journey.

### 2.3 Model Journey (Single Run Lifecycle)
*   **Purpose**: Visualize the sequential progression of an individual model candidate.
*   **Clickable Lifecycle Nodes**:
    ```
    [Dataset] ──► [Feature] ──► [Training] ──► [Validation] ──► [Calibration] ──► [Backtest] ──► [Paper] ──► [Execution] ──► [Promotion] ──► [Production] ──► [Archived]
    ```
*   **Interactions**: Clicking a node swaps the Right Detail Pane to that specific stage's diagnostic widgets (e.g., clicking *Calibration* displays ECE reliability charts).

### 2.4 Interactive Lineage Explorer
*   **Purpose**: Interactive zoomable DAG showing parent-child links between datasets, feature versions, experiments, and production runs.
*   **Interactions**: Pan & Zoom controls, highlight path from dataset to production, search by feature version.

### 2.5 Compare Journey
*   **Purpose**: Side-by-side performance review of multiple models, feature variants, or dataset slices.
*   **Layout**: Dynamic vertical split-screen comparing:
    *   Walk-forward metrics (confusion matrix, ROC plots).
    *   Slippage & latency distributions from execution records.

### 2.6 Dataset Health Dashboard
*   **Purpose**: Inspect raw data health before feature engineering begins.
*   **KPIs**: Missing values (%), Ingest delay (s), Outliers count, Schema drifts.
*   **Charts**: Ingestion latency bar charts, null value heatmap grids.

### 2.7 Research Queue
*   **Purpose**: Monitor active and scheduled model training runs.
*   **Widgets**: Queue lists (Running, Pending, Completed, Failed).
*   **KPIs**: Estimated Time to Ingestion, Worker utilization.

### 2.8 Promotion Queue
*   **Purpose**: Stage gate workflow management for candidates awaiting production sign-off.
*   **KPIs**: Staged Candidates, Review Time, Success Rate.

### 2.9 Research KPI Dashboard
*   **Purpose**: Overview of strategy alpha decay, win-rate profiles, and model lifecycle durations.
*   **Charts**: Cumulative PnL curves, F1 degradation over time.

### 2.10 Experiment Monitoring Workspace
*   **Purpose**: Deep-dive monitor for active training iterations.
*   **Charts**: Epoch-by-epoch loss convergence line charts, active CPU/GPU footprint metrics.

---

## 3. Future Extension Strategy

1.  **Rust Engine Adapter**: The UI data schema is decoupled via abstraction interfaces. When the backend shifts to Rust, the frontend changes only its API ingestion routes, preserving the visualization layers.
2.  **Distributed Worker Support**: Queue systems are built with multi-node setups in mind, supporting fields like `worker_node_id` in telemetry objects.
