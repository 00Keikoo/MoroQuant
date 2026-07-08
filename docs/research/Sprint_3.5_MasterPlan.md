# Sprint 3.5 Master Plan - Research Platform

## Overview
This Master Plan outlines the roadmap, risks, dependencies, and Definition of Done for implementing the MoroQuant Research Platform based on the architecture designs established in Sprint 3.5.

---

## Roadmap

```
Phase A: Registries & DB (2 Weeks) ──► Phase B: Tracking & Engine (3 Weeks) ──► Phase C: UI & Integration (2 Weeks)
```

### Phase A: Core Registries and Storage Foundation (Weeks 1-2)
- **Objective**: Establish the database schema and storage APIs for the Feature Store and Dataset Manager.
- **Tasks**:
  1. Implement SQL schema migrations for datasets, feature registries, and experiment tables.
  2. Implement the Feature Registry service to catalog and validate feature dependency DAGs.
  3. Implement the Dataset Manager service to compute fingerprints and freeze dataset files in storage.

### Phase B: Experiment Tracking and Comparison Engine (Weeks 3-5)
- **Objective**: Build the training log client, metric calculators, and run comparison queries.
- **Tasks**:
  1. Build Python clients for logging hyperparameters, metrics, and saving weights to the database.
  2. Implement calculations for expected calibration error (ECE) and Brier scores.
  3. Implement the Comparison Engine API to rank and select candidate runs.
  4. Set up the automated checklist rules for model promotion.

### Phase C: Downstream Integration and Dashboard UI (Weeks 6-7)
- **Objective**: Connect the platform to paper trading systems and expose dashboards.
- **Tasks**:
  1. Connect the paper trading execution loop to the Model Registry to retrieve active models.
  2. Build the Trade Explorer UI pages for comparing experiments.
  3. Conduct end-to-end tests from feature creation to paper trading promotion.

---

## Risks and Mitigations

### 1. Storage Exhaustion
- **Risk**: Storing frozen dataset files for every run can quickly deplete storage space.
- **Mitigation**: Implement the tiered retention policy. Compress dataset files using Parquet format with Snappy compression, and deduplicate datasets with identical feature lists and time bounds.

### 2. Live Feature Drift
- **Risk**: Feature logic computed offline (batch) could differ from live calculations (streaming), leading to execution errors.
- **Mitigation**: Share the same Python class files for calculating features in both training and production. Run daily integrity tests comparing historical offline outputs with live online outputs.

### 3. API Latency
- **Risk**: Querying complex lineages and comparing many runs could slow down dashboard performance.
- **Mitigation**: Cache metrics and comparison scores in the database, and precompute run ranks on completion.

---

## Project Dependencies
- **PostgreSQL Database**: Requires JSONB support for logging parameters, metrics, and metadata.
- **Blob Storage (S3-compatible)**: Required to store model binaries and frozen dataset parquet files.
- **Git Repository Access**: The feature compilation service requires programmatic access to check active commit hashes for data lineage records.

---

## Definition of Done (DoD)
An implementation task is considered complete when it meets the following criteria:
1. **Testing**: Minimum of 90% unit test coverage for the Feature Store and Dataset Manager modules.
2. **Linting & Types**: Code compiles without errors under static analysis check tools.
3. **Data Verification**: Confirm that rebuilding a dataset from feature source files yields a matching cryptographic fingerprint.
4. **Documentation**: Code files must include docstrings, and new API routes must be registered in the OpenAPI spec.
5. **Auditing**: Run a full test tracking run through validation to ensure metadata is written to the database.
