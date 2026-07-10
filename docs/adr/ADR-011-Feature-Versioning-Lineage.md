# ADR-011: Feature Store Versioning and Lineage Policy

## Status
Proposed (Design Only)

## Context
In quantitative research, inconsistencies in how features are engineered between the research environment (training/backtesting) and the production environment (live trading/replay execution) lead to "research-to-production variance." A feature calculated in training using a slightly different parameter or library version than in production invalidates all performance guarantees.

Furthermore, missing or ambiguous data lineage makes it impossible to reproduce past results. If a model was trained on a set of features, but the underlying dataset or the feature calculation code has changed silently, we cannot rebuild or audibly verify the model.

To solve this, we require a formal Feature Store architecture that guarantees:
1. Determinism: Given the same raw dataset and feature version, the engineered feature outputs are mathematically identical.
2. Lineage tracking: Any computed feature file can trace its origin back to its specific source dataset version and feature version.
3. Lightweight design: Reuses the existing file-based Parquet structure and SQLite metadata catalog without introducing cloud infrastructure, Redis, or Kafka.

## Decision
We will establish a strict Feature Store versioning and lineage registry governed by the following decisions:

### 1. Separation of Feature Definition and Parameterized Version
* **Feature Definition**: A name and mathematical description (e.g., `RSI` definition with formula `RSI(period, column)`).
* **Feature Version**: A distinct, parameterized version of that definition (e.g., `rsi_14_v1.0.0` maps to definition `RSI` with params `{"period": 14, "col": "close"}`).

### 2. Feature Dataset Naming & Lineage Registry
Every computed feature artifact will carry a unique identifier linking its source and transform parameters:
$$\text{feature\_dataset\_id} = \text{fds\_[feature\_version\_id]\_ds\_[source\_dataset\_id]}$$
This identifier is recorded in the SQLite metadata catalog mapping:
$$\text{Feature Dataset} \longrightarrow \text{Feature Version} + \text{Source Dataset Version}$$

### 3. Cryptographic Fingerprinting
A checksum of the canonicalized output feature DataFrame is generated and saved:
$$\text{Fingerprint} = \text{SHA256}(\text{Canonicalized Feature Payloads})$$
* Payload rows are ordered chronologically by `timestamp` and alphabetically by `symbol`.
* Values are formatted to fixed string precision (`%.8f`) prior to serialization.
* This ensures that execution of the pipeline on the same dataset version with the same feature version will yield the same fingerprint.

### 4. Semantic Versioning Rules for Features
* **Major bump (vX.0.0)**: Structural changes to the underlying formula or calculation logic (e.g. switching calculation method from EMA to SMA in RSI).
* **Minor bump (vx.Y.0)**: Parameter list modifications (e.g. adding a new configuration attribute).
* **Patch bump (vx.y.Z)**: Code optimizations, performance improvements, or library dependencies updates that do not alter numerical outputs.

## Consequences
* **Benefits**:
  * **Absolute Reproducibility**: Researchers can regenerate the exact feature matrix for any historical model.
  * **Zero Production Drift**: Replay and trading engines load the identical feature Parquet files or parameter definitions verified by hash signature.
  * **Clean Auditing**: Traceability from any trained model back to the exact features, snapshot, and trades.
* **Trade-offs**:
  * **Disk Footprint**: Storing separate Parquet layers increases disk use. This is mitigated by inner-joining features on demand and compression.

## Related Documents
* [Feature Store Design Specification](file:///home/zafka/trade-dashboard/docs/research/feature_store_design.md)
* [Feature Store Contract Specification](file:///home/zafka/trade-dashboard/docs/research/feature_store_contract.md)
* [Dataset Immutability and Versioning Policy ADR-010](file:///home/zafka/trade-dashboard/docs/adr/ADR-010-Dataset-Immutability-Versioning.md)
