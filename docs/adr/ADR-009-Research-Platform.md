# ADR-009: Research Platform Architecture Design

## Status
Proposed (Design Only)

## Context
MoroQuant's current backend handles raw data ingestion and executes backtests, but lacks a systematic layer before model training. Researchers define features and assemble datasets in an ad-hoc manner, which creates several problems:
1. **Train-Test Leakage**: Subtle time-alignment errors when creating features can lead to historical leakage, causing overly optimistic backtest results that fail in live markets.
2. **Reproducibility Gaps**: Without immutable dataset freezing and fingerprinting, matching a specific trained model back to the exact version of the input data is difficult.
3. **Lax Promotion Standards**: Transitioning a model from backtest to paper trading is currently manual, lacking formalized statistical thresholds (such as ECE or Brier scores) or automated audit trails.

To resolve these issues, we propose establishing a dedicated **Research Platform** comprising a Dataset Manager, Feature Store, and Experiment Tracker to sit between raw repositories and the model training logic.

---

## Decision
We will establish a dedicated, metadata-driven Research Platform before the model training layer. The platform will enforce:
- **Centralized Feature Registry**: Feature definitions are registered with schemas, source code snippets, and explicit version trees.
- **Immutable Dataset Freezing**: Dataset queries are materialized, crytographically hashed, and written as read-only files.
- **Automated Experiment Tracking**: All hyperparameters, metrics (including ECE, Brier, Sharpe, Sortino, Calmar), and model weights are tracked and logged to a central database.
- **Formal Gatekeeping**: Models are ranked automatically and must meet quantitative thresholds to be promoted to paper or live trading environments.

---

## Benefits
- **Zero Train-Test Leakage**: A point-in-time join engine ensures features cannot look into the future, guaranteeing backtest validity.
- **Deterministic Reproducibility**: Cryptographic hashes of datasets allow exact reproduction of any experiment run.
- **Improved Model Quality**: Rigorous calibration metrics (ECE, Brier) filter out overconfident models.
- **Reusable Feature Logic**: Centralizing feature definitions enables reuse across different models, reducing development effort.

---

## Tradeoffs
- **Storage Overhead**: Freezing datasets in storage requires more disk space compared to running queries dynamically.
- **Process Complexity**: Forcing researchers to register features and datasets before training introduces extra steps in the prototyping loop.
- **Metadata Management**: Maintaining registries for features, datasets, and experiments increases database schema complexity.

---

## Alternatives Considered
1. **Ad-hoc Notebook Workflow (Status Quo)**: Continue using standalone Python scripts and Jupyter notebooks. This was rejected due to lack of reproducibility and risk of train-test leakage.
2. **Third-Party MLOps Platform (e.g., MLflow + Feast)**: Implement third-party platforms. This was rejected because MoroQuant is designed to be a self-contained system. Integrating, hosting, and maintaining separate MLOps infrastructure would exceed the complexity of our lightweight SQLite/PostgreSQL architecture.

---

## Future Evolution
- **Dynamic Online Serving**: Enable the Feature Store to serve live features from Redis with low latency, supporting real-time model inferences in paper and live trading.
- **Automated Hyperparameter Optimization**: Integrate Optuna with the Experiment Tracker to automate hyperparameter sweeps and log results.
- **Continuous Deployment (CD) for Models**: Automate model promotion to paper trading once validation thresholds are met, removing the need for manual approval.
