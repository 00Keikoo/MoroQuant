# ADR-013: Model Registry Lifecycle and Lineage Policy

## Status
Proposed (Design Only)

## Context
In automated quantitative trading, model degradation, training-to-production divergence, and untraceable black-box models present critical operational risks. If a live model begins making erroneous trading decisions, we must be able to audit its exact origin and trace the mathematical pipeline that generated it. 

Furthermore, models must undergo rigorous validation checks before they are permitted to execute orders in paper or live environments. Promoting an unvalidated or poorly calibrated model violates MoroQuant's engineering guidelines.

To resolve these challenges, we require a formal **Model Registry** design that guarantees:
1. **Immutable Lineage**: Every model version must be traceably linked to its complete upstream lineage:
   $$\text{Snapshot} \longrightarrow \text{Dataset} \longrightarrow \text{Feature Dataset} \longrightarrow \text{Experiment} \longrightarrow \text{Evaluation} \longrightarrow \text{Model Version}$$
2. **Deterministic Versioning and Fingerprinting**: A unique artifact versioning and cryptographic check policy that ensures the serialized model weights cannot be modified.
3. **Structured Lifecycle States**: A deterministic state machine defining how models progress from discovery to production execution:
   $$\text{Candidate} \longrightarrow \text{Validated} \longrightarrow \text{Production} \longrightarrow \text{Archived}$$
4. **Lightweight Design**: Reuses the file-based Parquet structure and SQLite metadata catalog without introducing cloud infrastructure, external model registries (like MLflow), or dedicated database systems.

## Decisions

### 1. Model Lifecycle States
We establish four formal states for any model:
* **Candidate**: Initial state upon successful training and artifact serialization. Ready for quantitative validation.
* **Validated**: The model has passed the strict quantitative check rules (Sharpe, drawdown, ECE, Brier score) and has been digitally signed by the verifying architect.
* **Production**: The model is actively serving predictions in live or paper trading environments. Only one version of a specific model ID may be in this state at any time.
* **Archived**: The model artifact is retired. The serialized binary may be purged from disk to conserve space, but its metadata, lineage history, and cryptographic fingerprint are permanently retained in SQLite for historical auditability.

### 2. Complete Lineage Ledger
The Model Registry SQLite database must enforce referential integrity for all models. A model version registration requires validation of the entire lineage graph:
* **Snapshot**: Raw database state snapshot (`snapshot_id`).
* **Dataset**: Extracted clean dataset version (`dataset_id`).
* **Feature Dataset**: Engineered feature table with verified columns (`feature_dataset_id`).
* **Experiment**: The optimization sweep that identified this hyperparameter configuration (`experiment_id`).
* **Evaluation**: The quantitative scorecard evaluation (`evaluation_id`/`best_config_id`).
* **Model**: The resulting serialized model artifact (`model_version_id`).

### 3. Cryptographic Fingerprinting & Artifact Policy
Model binaries (e.g., serialized JSON/txt models) are stored under a standardized folder structure. To prevent tampering:
* A sha256 checksum is computed on the serialized model binary alongside its hyperparameters configuration file:
  $$\text{Fingerprint} = \text{SHA256}(\text{model\_binary\_payload} + \text{hyperparameters\_json})$$
* Filesystem write locks (`chmod 0444`) are applied to the directory immediately upon transition to `Validated`.
* The registry checks this signature at model load time. If a fingerprint mismatch is detected, execution is aborted immediately.

### 4. Promotion Policy
To transition from `Candidate` to `Validated`, a model must satisfy the Sprint 3.5 quality gate:
1. **Walk-Forward Sharpe**: $\ge 1.5$
2. **Maximum Drawdown**: $\ge -15\%$ (drawdown value is less negative than $-15\%$)
3. **Expected Calibration Error (ECE)**: $< 0.05$
4. **Brier Score**: $< 0.22$
5. **Trade Count**: $\ge 100$ trades in the validation set.
6. **Digital Verification**: A hash signature matching the Principal Quant Architect approval.

To transition from `Validated` to `Production`, the active production model for the given symbol/target must first be demoted, ensuring a strict 1-to-1 mapping.

## Consequences

### Benefits
* **Complete Auditability**: In the event of a trading anomaly, the model can be traced back to the exact code parameters, training datasets, and features that produced it.
* **Operational Safety**: Eliminates the risk of running untested or drift-impacted models in live environments.
* **Zero Production Drift**: Enforces signature checks at model load time, eliminating file corruption or manual modification risks.

### Trade-offs
* **Storage Allocation**: Retaining serialized model weights and configs increases local disk space requirements.
* **Operation Latency**: Loading models with strict signature verification adds a slight overhead at startup (mitigated by caching fingerprints).

## Related Documents
* [Model Registry Design Specification](file:///home/zafka/trade-dashboard/docs/research/model_registry_design.md)
* [Model Registry Contract Specification](file:///home/zafka/trade-dashboard/docs/research/model_registry_contract.md)
* [Dataset Immutability ADR-010](file:///home/zafka/trade-dashboard/docs/adr/ADR-010-Dataset-Immutability-Versioning.md)
* [Feature Store Versioning ADR-011](file:///home/zafka/trade-dashboard/docs/adr/ADR-011-Feature-Versioning-Lineage.md)
