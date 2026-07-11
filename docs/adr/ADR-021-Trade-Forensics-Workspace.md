# ADR-021: Trade Forensics Workspace

## Status
Proposed

## Context
Standard trading platforms treat historical trades as a flat list of transaction records. For quantitative research, every trade is a scientific artifact. We must understand the exact version of the model, features, dataset calibration, and execution latency that was active when the trade occurred. We need to replace the traditional "Trade History" with an institutional-grade **Trade Forensics Workspace**.

## Decision
1.  **Trade Forensics Workspace Adoption**: Replace standard trade listings with the Trade Forensics Workspace.
2.  **Immutable Snapshotting**: Require the system to capture and store an immutable snapshot of all metrics, signal probabilities, and feature weights at the moment of entry. These historical records must never change, even if newer models replace production.
3.  **Visual Replay & Lineage**: Implement step-by-step visual trade playback (scrubber timeline) and dependency lineage tracing back to the raw training datasets.

## Consequences
*   **Benefits**:
    *   Ensures scientific reproducibility of historical execution decisions.
    *   Provides high-density diagnostics for slippage and entry/exit edge leakage.
    *   Enables AI-driven post-trade post-mortems based on model confidence parameters.
*   **Trade-offs**:
    *   Significant storage increase to house immutable JSON snapshots of large feature sets per trade.
