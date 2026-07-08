# Research Data Flow

This document details the movement of prediction and trading data from production inference to evaluation reports.

## Data Movement Sequence

```
ML Inference Output
       ↓ (1)
SQLite database (signals / paper_positions)
       ↓ (2)
Snapshot Service (Capture / serialization)
       ↓ (3)
Replay Service (run_replay)
       ↓ (4)
Strategy Optimization (Experiment Engine)
       ↓ (5)
generalization Tests (Validation Engine)
       ↓ (6)
Research Integrity Layer (Bias / Leakage Checks)
       ↓ (7)
Final Report Generation (JSON / markdown UI)
```

### 1. Production Logging (Production → Database)
When live or paper models execute predictions inside `models/predictor.py`, the following variables are written:
- **Features**: Top features written to `features_json`.
- **Probabilities**: Raw and calibrated probability distributions (`prob_short`, `prob_neutral`, `prob_long`).
- **Metadata**: Model path and execution timestamps.
These are stored as a SQLite row.

### 2. Snapshot Extraction (Database → Snapshot JSON)
`SnapshotService` queries rows from SQLite using `SignalRepository` and `TradeRepository`. It maps variables into dictionary objects, enriches signals with corresponding trade directions, and hashes the content to construct a snapshot.

### 3. Replay Engine Processing (Snapshot → ReplayResult)
The snapshot signals and trades are loaded. Probabilities are extracted and processed by the `DecisionEngine`. Reconstructed actions are fed into `ExecutionParityChecker` to compute decision matches.

### 4. Strategy Iteration (ReplayResult → StrategyResult)
`ExperimentEngine` accepts the `ReplayResult` and runs parameters (such as `threshold_long`) functionally over the decisions. It estimates win rates and PnL.

### 5. Out-of-Sample Validation (StrategyResult → ValidationReport)
Timestamps are chronologically split to calculate training vs test performance decay (detecting overfit) and walk-forward stability scores.

### 6. Research Verification (ValidationReport → IntegrityReport)
The research integrity layer reviews the metrics to flag potential data leakage or survivorship biases before final reporting.
