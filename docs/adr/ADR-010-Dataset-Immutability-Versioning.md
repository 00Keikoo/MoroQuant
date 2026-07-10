# ADR-010: Dataset Immutability and Versioning Policy

## Status
Proposed (Design Only)

## Context
In quantitative research, data leakage, lookahead bias, and mutating underlying datasets represent severe risks to backtest validity. If research datasets can be modified, appended, or recalculated post-run, establishing mathematical reproducibility for trained models becomes impossible. 

Previously, MoroQuant's Snapshot Engine captured system states, but without a dedicated dataset isolation layer. Replay and Experiment Engines consumed snapshots directly, but snapshots are snapshot-in-time states rather than structured, validated machine learning training/evaluation datasets.

To support rigorous research under Sprint 4.1, we require a mechanism to:
1. Construct frozen, validated datasets from existing snapshots.
2. Guarantee that once a dataset is defined, it can never be altered (immutability).
3. Trace any trained model or experiment directly back to a unique, fingerprinted dataset version.
4. Keep the architecture simple, avoiding heavy distributed components, S3/blob storage, or dedicated feature stores, using instead a local SQLite-backed metadata registry and file-based payload immutability.

## Decision
We will establish a strict Dataset Immutability and Versioning system governed by the following rules:

### 1. Versioning Scheme
Datasets will use a semantic identifier format: `DS_[Major].[Minor].[Patch]`.
* **Major**: Structural changes. e.g., changes to target labeling logic, classification to regression shifts, or underlying sample frequency changes (e.g., 1h to 5m resampling).
* **Minor**: Schema changes. e.g., adding, removing, or renaming feature fields or metadata attributes.
* **Patch**: Temporal bounds or filter changes. e.g., adjusting time windows (shifting start/end dates), changing outlier thresholds, or updating imputation parameters.

### 2. Cryptographic Fingerprinting (Signature)
Every dataset is hashed at creation to enforce a tamper-proof signature:
$$\text{Fingerprint} = \text{SHA256}(\text{Canonicalized Data Payload})$$
Canonicalization requires:
* Rows sorted chronologically by primary index (`timestamp`).
* Columns sorted alphabetically by name.
* Numeric values formatted as string representations with fixed precision (e.g., `%.8f` float conversion) to prevent float representation variance across platforms.
* Hashing the resulting serialized CSV/JSON string.

### 3. Storage and Database Freezing
* **SQLite Registry Lock**: The dataset metadata record is saved in a SQLite database with a strict state transition model. Once a dataset transitions to `FROZEN`, the SQLite database record sets `is_frozen = 1`, and database-level triggers/checks block updates to the record.
* **File System Immutability**: The materialized dataset payloads (stored as compressed CSV or Parquet files in `/storage/datasets/`) are marked as read-only at the operating system level (e.g., `chmod 444` in Linux).

## Consequences
* **Benefits**:
  * **Deterministic Backtests**: Guaranteed zero data mutation, meaning multiple strategy runs on the same dataset version are scientifically comparable.
  * **Complete Auditability**: Models can refer to a dataset hash, which is verifiable at any time.
  * **Zero External Dependencies**: Implemented natively within python standard libraries and SQLite.
* **Trade-offs / Risks**:
  * **Disk Consumption**: Materializing and freezing files increases storage usage. Mitigated by applying a tiered retention policy and Gzip compression.
  * **Prototyping Friction**: Researchers cannot "hot-fix" a dataset. They must register a new version (e.g., bump Patch or Minor) if a feature is added or dates change.

## Related Documents
* [Dataset Manager Design Specification](file:///home/zafka/trade-dashboard/docs/research/dataset_manager_design.md)
* [Dataset Contract](file:///home/zafka/trade-dashboard/docs/research/dataset_contract.md)
* [Repository Pattern ADR-002](file:///home/zafka/trade-dashboard/docs/adr/ADR-002-Repository-Pattern.md)
