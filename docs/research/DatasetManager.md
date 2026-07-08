# Dataset Manager Design Specification

## Overview
The Dataset Manager ensures that data used for training and evaluating machine learning models remains immutable, reproducible, and verifiable. It provides a formal system for cataloging datasets, tracking their lineages, verifying data integrity using fingerprints, and enforcing data lifecycle rules.

---

## Dataset Versioning
A dataset represents a collection of technical and structural features over a designated time period. To prevent model degradation, data drift, and debugging challenges, every dataset query output is versioned using semantic-like versioning rules:

`DS_[Major].[Minor].[Patch]`
- **Major**: Structural changes, such as modifying target definitions (e.g., changing classification boundaries or moving from regression to classification targets) or changing the frequency/resolution of the underlying rows (e.g., 1-hour candles to 5-minute candles).
- **Minor**: Schema modifications, such as adding, renaming, or removing features from the feature list.
- **Patch**: Retraining updates or adjustments to time windows, start/end boundaries, or data cleaning/imputation rules.

---

## Dataset Metadata
Metadata is stored as a structured JSON document in the registry database. It contains complete information needed to understand how the dataset was constructed and what it contains:

```json
{
  "dataset_id": "ds_btc_hourly_volatility_v1.0.0",
  "name": "btc_hourly_volatility",
  "version": "1.0.0",
  "created_at": "2026-07-06T18:30:00Z",
  "created_by": "quant_researcher_alpha",
  "time_bounds": {
    "start_time": "2024-01-01T00:00:00Z",
    "end_time": "2025-12-31T23:00:00Z"
  },
  "dimensions": {
    "num_rows": 17520,
    "num_columns": 32,
    "features_count": 30,
    "targets_count": 2
  },
  "features": [
    "close_log_returns_1h",
    "rsi_14_1h",
    "atr_14_1h",
    "volume_profile_va_ratio",
    "regime_index"
  ],
  "targets": [
    "target_returns_24h_class",
    "target_returns_24h_regression"
  ],
  "data_types": {
    "close_log_returns_1h": "float64",
    "rsi_14_1h": "float64",
    "volume_profile_va_ratio": "float64",
    "target_returns_24h_class": "int32"
  },
  "preprocessing": {
    "imputation_strategy": "forward_fill",
    "scaling_method": "robust_scaler",
    "outlier_cutoff_std": 4.5
  }
}
```

---

## Dataset Registry
The Dataset Registry maintains a global ledger of all created datasets. No model training run can occur using data that has not been registered in the registry. It enforces:
- **Uniqueness**: A dataset version combined with its fingerprint must be globally unique.
- **Traceability**: All datasets must reference valid feature versions in the Feature Store.
- **Searchability**: Researchers can search by features used, time spans, or target configurations.

---

## Dataset Fingerprint
To ensure mathematical reproducibility, the Dataset Manager computes a cryptographic fingerprint of the data payload when registering a dataset.

$$\text{Fingerprint} = \text{HMAC-SHA256}(\text{Sorted CSV Payload}, \text{Salt})$$

### Generation Rules:
1. Sort rows chronologically by the primary timestamp index.
2. Sort columns alphabetically by name.
3. Drop metadata columns that do not affect model parameters.
4. Convert columns to formatted strings with fixed float precision to avoid differences between platforms.
5. Compute the hash of the resulting payload.
6. The registry compares this fingerprint during training to guarantee the dataset has not been modified.

---

## Data Lineage
Data lineage tracks the path from raw exchange inputs to the final model features. It provides a visual and queryable dependency graph representing how data was transformed.

```
[Binance Exchange Ingest]
       │
       ▼ (Raw Trades & Orderbook)
[SQLite Raw Repositories]
       │
       ▼ (Resampling & Imputation)
[SQLite Resampled Candles]
       │
       ▼ (Feature Store Pipeline)
[Feature Store: Volatility Group v1.2] ────► [Feature: ATR_14 (Version 3)]
       │                                                   │
       ▼                                                   ▼
[Dataset Manager: btc_volatility_v1.0.0] ◄────────[Dataset Feature Mapping]
```

---

## Dataset Reproducibility
To ensure that a dataset can be fully reconstructed if it is deleted or lost:
1. **Deterministic Processing**: Scaling parameters (e.g., standard deviation, mean) must be computed on the training fold and saved inside the Dataset Metadata.
2. **Deterministic Sampling**: Train, validation, and test fold indices must be explicitly saved as metadata instead of randomly generated during training.
3. **Exact Code Versioning**: The Git commit hash of the feature extraction pipeline must be recorded as part of the lineage information.

---

## Dataset Freeze
A dataset freeze marks a dataset version as immutable. 
- **Read-Only Status**: The file is set to read-only in storage.
- **Database Lock**: The database record is marked as `is_frozen = true`. Attempts to overwrite, append, or update rows in this dataset version will trigger an immediate exception.
- **Guaranteed Consistency**: Freezing ensures that if multiple models are trained on the same dataset version, they are using identical data.

---

## Retention Policy
Datasets consume significant storage. The Dataset Manager implements a tiered retention policy:

| Tier | Status | Storage Location | Retention Period | Action on Expiry |
| :--- | :--- | :--- | :--- | :--- |
| **Tier 1 (Active)** | Linked to production or active paper trading models. | High-performance SSD block store | Indefinite | Keep active. |
| **Tier 2 (Research)** | Under review or used in recent experiments (<90 days). | Object Storage (Hot) | 90 Days | Move to Tier 3. |
| **Tier 3 (Archive)** | Historical research runs. | Object Storage (Cold / Glacier) | 365 Days | Delete actual files, retain Metadata and Fingerprints. |
| **Tier 4 (Expired)** | Metadata registry entry. | Metadata Database | Indefinite | Retain metadata for historic auditability. |
