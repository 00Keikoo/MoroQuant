# ADR-017: MoroQuant Lab Research Workbench UI

## Status
Proposed

## Context
The current platform has a "Backtest" panel. However, quantitative research is broader than just running backtests. Quantitative researchers need a workbench that covers dataset lineage, feature validation, model calibration, live paper promotion, and execution analytics. We need to restructure the platform's user experience to treat Backtesting as a module within the MoroQuant Lab, establishing a unified research workspace.

## Decision
1.  **Replace Navigation**: Replace the top-level "Backtest" navigation link with **🧪 MoroQuant Lab**.
2.  **Modularized Backtesting**: Move the existing Backtesting interface into a module within the MoroQuant Lab workbench layout without altering the core backend engines.
3.  **UI Layout**: Implement a unified left-hand sidebar navigation containing the modules:
    *   **Overview**
    *   **Experiment Registry**
    *   **Dataset Registry**
    *   **Feature Registry**
    *   **Validation Center**
    *   **Calibration Center**
    *   **Backtesting**
    *   **Execution Analytics**
    *   **Promotion Center**
    *   **Model Registry**
    *   **Research Timeline**
    *   **Settings**
4.  **Information Isolation**: Enforce pure API consumption guidelines, ensuring the UI remains stateless and decoupled from the SQLite database.

## Consequences
*   **Benefits**:
    *   Unified workflow from raw data to production models.
    *   Extensible design that scales as the system transitions to Rust.
    *   Clearer lineage visualization (Raw data -> Cleaning -> Features -> Dataset -> Run -> Model -> Production).
*   **Trade-offs**:
    *   Users accustomed to the single "Backtest" screen will need to navigate through the Lab to access it.
