# Model Registry Data Contract Specification

This document details the data contracts, schemas, and representation formats for the Model Registry.

---

## 1. Schema Definitions

### 1.1 Model Metadata and Lineage JSON Schema
Every registered model version must have metadata conforming to this schema.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "ModelVersionMetadata",
  "type": "object",
  "required": [
    "model_version_id",
    "model_id",
    "version",
    "lifecycle_state",
    "fingerprint",
    "storage_path",
    "hyperparameters",
    "lineage",
    "created_at"
  ],
  "properties": {
    "model_version_id": {
      "type": "string",
      "pattern": "^mdl_[a-z0-9_]+_v[0-9]+\\.[0-9]+\\.[0-9]+$"
    },
    "model_id": {
      "type": "string",
      "pattern": "^mdl_[a-z0-9_]+$"
    },
    "version": {
      "type": "string",
      "pattern": "^[0-9]+\\.[0-9]+\\.[0-9]+$"
    },
    "lifecycle_state": {
      "type": "string",
      "enum": ["CANDIDATE", "VALIDATED", "PRODUCTION", "ARCHIVED"]
    },
    "fingerprint": {
      "type": "string",
      "description": "SHA256 checksum of canonical model weights file + hyperparameter JSON configuration"
    },
    "storage_path": {
      "type": "string",
      "description": "Absolute path to model weights binary directory"
    },
    "hyperparameters": {
      "type": "object",
      "description": "Key-value map of model parameters"
    },
    "lineage": {
      "type": "object",
      "required": [
        "snapshot_id",
        "dataset_id",
        "feature_dataset_id",
        "experiment_id",
        "best_config_id"
      ],
      "properties": {
        "snapshot_id": { "type": "string" },
        "dataset_id": { "type": "string" },
        "feature_dataset_id": { "type": "string" },
        "experiment_id": { "type": "string" },
        "best_config_id": { "type": "string" }
      }
    },
    "created_at": {
      "type": "string",
      "format": "date-time"
    }
  }
}
```

### 1.2 Python Dataclasses (Code Contract)

```python
from dataclasses import dataclass, field
from typing import Dict, Any, Optional

@dataclass(frozen=True)
def ModelLineage:
    snapshot_id: str
    dataset_id: str
    feature_dataset_id: str
    experiment_id: str
    best_config_id: str

@dataclass(frozen=True)
def ModelEvaluation:
    sharpe_ratio: float
    max_drawdown: float
    ece: float
    brier_score: float
    win_rate: float
    profit_factor: float
    sortino_ratio: float
    trade_count: int
    is_approved: bool = False
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None

@dataclass
class ModelVersionMetadata:
    model_version_id: str
    model_id: str
    version: str
    lifecycle_state: str
    fingerprint: str
    storage_path: str
    hyperparameters: Dict[str, Any]
    lineage: ModelLineage
    created_at: str
    evaluation: Optional[ModelEvaluation] = None
    is_frozen: bool = False
```

---

## 2. Storage Directory and Fingerprint Policy

* **Artifact Directory**: `/home/zafka/trade-dashboard/storage/models/{model_version_id}/`
* **File Structure**:
  * `model.bin`: Serialized binary payload of the model weights (e.g. LightGBM text representation, PyTorch trace).
  * `hyperparameters.json`: Configuration mapping for model execution.
  * `signature.sha256`: Text file containing the hash of `model.bin` + `hyperparameters.json`.

* **Fingerprint Formula**:
  $$\text{Fingerprint} = \text{SHA256}(\text{SHA256}(\text{model.bin}) + \text{SHA256}(\text{hyperparameters.json}))$$

---

## 3. API Contracts

### 3.1 Register Model Candidate
* **Endpoint**: `POST /api/v1/models/register`
* **Request Payload**:
  ```json
  {
    "model_id": "mdl_xgb_btc_trend",
    "version_bump": "minor",
    "storage_path": "/home/zafka/trade-dashboard/storage/models/mdl_xgb_btc_trend_v1.1.0",
    "hyperparameters": {
      "max_depth": 6,
      "learning_rate": 0.05
    },
    "lineage": {
      "snapshot_id": "snap_20260710",
      "dataset_id": "ds_btc_vol_v1.0.0",
      "feature_dataset_id": "fds_rsi14_ds_btc_vol_v1.0.0",
      "experiment_id": "exp_btc_trend_v1",
      "best_config_id": "cfg_0432"
    }
  }
  ```
* **Response Payload**:
  ```json
  {
    "status": "success",
    "model_version_id": "mdl_xgb_btc_trend_v1.1.0",
    "lifecycle_state": "CANDIDATE",
    "fingerprint": "8f8a9a2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e"
  }
  ```

### 3.2 Validate and Promote Model
* **Endpoint**: `POST /api/v1/models/{model_version_id}/promote`
* **Request Payload**:
  ```json
  {
    "promoter": "principal_quant_architect",
    "notes": "Walk-forward validation check passed on all metric benchmarks."
  }
  ```
* **Response Payload**:
  ```json
  {
    "status": "success",
    "model_version_id": "mdl_xgb_btc_trend_v1.1.0",
    "lifecycle_state": "PRODUCTION",
    "activated_at": "2026-07-10T14:00:00Z"
  }
  ```
