# Research Orchestrator Contract Specification

This document details the interface schemas, data contracts, and input/output payload requirements for each stage of the Research Orchestrator pipeline.

---

## 1. Pipeline Stage Contracts

The Research Orchestrator coordinates the pipeline by passing the output of stage $N$ as the input to stage $N+1$. Below are the precise data shapes for each handoff.

```
[Snapshot]
   │ (SnapshotOutput)
   ▼
[Dataset Manager]
   │ (DatasetOutput)
   ▼
[Feature Store]
   │ (FeatureOutput)
   ▼
[Experiment Engine]
   │ (ExperimentOutput)
   ▼
[Evaluation Engine]
   │ (EvaluationOutput)
   ▼
[Model Registry]
   │ (RegistryOutput)
   ▼
[Research Dashboard]
```

---

### 1.1 Snapshot Engine Handoff

* **Stage 1 Output: `SnapshotOutput`**
  ```json
  {
    "snapshot_id": "snap_btc_20260710",
    "symbols": ["BTCUSDT"],
    "start_time": "2026-01-01T00:00:00Z",
    "end_time": "2026-07-01T00:00:00Z",
    "storage_path": "/home/zafka/trade-dashboard/storage/snapshots/snap_btc_20260710.parquet"
  }
  ```

---

### 1.2 Dataset Manager Handoff

* **Stage 2 Input: `DatasetInput`**
  Requires the snapshot metadata and filtering parameters.
  ```json
  {
    "snapshot_id": "snap_btc_20260710",
    "storage_path": "/home/zafka/trade-dashboard/storage/snapshots/snap_btc_20260710.parquet",
    "imputation_strategy": "forward_fill",
    "resample_interval": "1h"
  }
  ```

* **Stage 2 Output: `DatasetOutput`**
  ```json
  {
    "dataset_id": "ds_btc_1h_v1.0.0",
    "fingerprint": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2",
    "dataset_uri": "/home/zafka/trade-dashboard/storage/datasets/ds_btc_1h_v1.0.0.parquet",
    "row_count": 4320
  }
  ```

---

### 1.3 Feature Store Handoff

* **Stage 3 Input: `FeatureStoreInput`**
  Requires the dataset file and feature calculations configuration.
  ```json
  {
    "dataset_id": "ds_btc_1h_v1.0.0",
    "dataset_uri": "/home/zafka/trade-dashboard/storage/datasets/ds_btc_1h_v1.0.0.parquet",
    "features": [
      {
        "name": "rsi_14",
        "parameters": { "window": 14 }
      },
      {
        "name": "macd_12_26",
        "parameters": { "fast": 12, "slow": 26, "signal": 9 }
      }
    ]
  }
  ```

* **Stage 3 Output: `FeatureStoreOutput`**
  ```json
  {
    "feature_dataset_id": "fds_rsi_macd_ds_btc_1h_v1.0.0",
    "fingerprint": "f2e1d0c9b8a7f6e5d4c3b2a10f9e8d7c6b5a4f3e2d1c0b9a8f7e6d5c4b3a2f1e",
    "feature_dataset_uri": "/home/zafka/trade-dashboard/storage/features/fds_rsi_macd_ds_btc_1h_v1.0.0.parquet"
  }
  ```

---

### 1.4 Experiment Engine Handoff

* **Stage 4 Input: `ExperimentInput`**
  Requires the calculated features and hyperparameter sweep settings.
  ```json
  {
    "feature_dataset_id": "fds_rsi_macd_ds_btc_1h_v1.0.0",
    "feature_dataset_uri": "/home/zafka/trade-dashboard/storage/features/fds_rsi_macd_ds_btc_1h_v1.0.0.parquet",
    "model_type": "xgboost",
    "hyperparameter_grid": {
      "max_depth": [4, 6, 8],
      "learning_rate": [0.01, 0.05, 0.1]
    },
    "cross_validation_folds": 5
  }
  ```

* **Stage 4 Output: `ExperimentOutput`**
  ```json
  {
    "experiment_id": "exp_xgb_rsi_macd_20260710",
    "best_config_id": "cfg_0432",
    "hyperparameters": {
      "max_depth": 6,
      "learning_rate": 0.05
    },
    "model_binary_uri": "/home/zafka/trade-dashboard/storage/experiments/exp_xgb_rsi_macd_20260710/model.bin"
  }
  ```

---

### 1.5 Evaluation Engine Handoff

* **Stage 5 Input: `EvaluationInput`**
  Requires model references to run path-dependent validation simulations.
  ```json
  {
    "experiment_id": "exp_xgb_rsi_macd_20260710",
    "best_config_id": "cfg_0432",
    "model_binary_uri": "/home/zafka/trade-dashboard/storage/experiments/exp_xgb_rsi_macd_20260710/model.bin",
    "validation_rules": {
      "stop_loss_pct": 0.02,
      "take_profit_pct": 0.06
    }
  }
  ```

* **Stage 5 Output: `EvaluationOutput`**
  ```json
  {
    "evaluation_id": "eval_xgb_rsi_macd_20260710",
    "metrics": {
      "sharpe_ratio": 1.78,
      "max_drawdown": -0.112,
      "ece": 0.034,
      "brier_score": 0.185,
      "win_rate": 0.54,
      "profit_factor": 1.62,
      "sortino_ratio": 2.15,
      "trade_count": 142
    },
    "is_approved": true
  }
  ```

---

### 1.6 Model Registry Handoff

* **Stage 6 Input: `ModelRegistryInput`**
  Combines lineage tracking details and evaluation scores for promotion candidate verification.
  ```json
  {
    "model_id": "mdl_xgb_btc_trend",
    "version_bump": "minor",
    "model_binary_uri": "/home/zafka/trade-dashboard/storage/experiments/exp_xgb_rsi_macd_20260710/model.bin",
    "hyperparameters": {
      "max_depth": 6,
      "learning_rate": 0.05
    },
    "lineage": {
      "snapshot_id": "snap_btc_20260710",
      "dataset_id": "ds_btc_1h_v1.0.0",
      "feature_dataset_id": "fds_rsi_macd_ds_btc_1h_v1.0.0",
      "experiment_id": "exp_xgb_rsi_macd_20260710",
      "best_config_id": "cfg_0432"
    },
    "evaluation": {
      "evaluation_id": "eval_xgb_rsi_macd_20260710",
      "sharpe_ratio": 1.78,
      "max_drawdown": -0.112,
      "ece": 0.034,
      "brier_score": 0.185,
      "win_rate": 0.54,
      "profit_factor": 1.62,
      "sortino_ratio": 2.15,
      "trade_count": 142
    }
  }
  ```

* **Stage 6 Output: `ModelRegistryOutput`**
  ```json
  {
    "model_version_id": "mdl_xgb_btc_trend_v1.1.0",
    "lifecycle_state": "CANDIDATE",
    "fingerprint": "8f8a9a2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e",
    "storage_path": "/home/zafka/trade-dashboard/storage/models/mdl_xgb_btc_trend_v1.1.0"
  }
  ```

---

### 1.7 Research Dashboard Handoff

* **Stage 7 Input: `ResearchDashboardInput`**
  Publishes the completed model candidate registration to trigger rendering updates.
  ```json
  {
    "model_version_id": "mdl_xgb_btc_trend_v1.1.0",
    "experiment_id": "exp_xgb_rsi_macd_20260710",
    "status": "PUBLISHED"
  }
  ```

* **Stage 7 Output: `ResearchDashboardOutput`**
  ```json
  {
    "dashboard_url": "/research/experiments/exp_xgb_rsi_macd_20260710",
    "rendered": true
  }
  ```

---

## 2. API Schema Definitions

### 2.1 Create Job Request Payload
* **Endpoint**: `POST /api/research/jobs`
* **Schema**:
  ```json
  {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "CreateResearchJobPayload",
    "type": "object",
    "required": ["name", "initial_config"],
    "properties": {
      "name": { "type": "string" },
      "initial_config": {
        "type": "object",
        "required": ["snapshot_config", "dataset_config", "feature_config", "experiment_config", "evaluation_config"],
        "properties": {
          "snapshot_config": { "type": "object" },
          "dataset_config": { "type": "object" },
          "feature_config": { "type": "object" },
          "experiment_config": { "type": "object" },
          "evaluation_config": { "type": "object" }
        }
      }
    }
  }
  ```

### 2.2 Get Job Status Response Payload
* **Endpoint**: `GET /api/research/jobs/{id}`
* **Schema**:
  ```json
  {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "ResearchJobStatusResponse",
    "type": "object",
    "required": ["job_id", "name", "status", "current_stage", "started_at", "finished_at", "duration_seconds", "stage_results"],
    "properties": {
      "job_id": { "type": "string" },
      "name": { "type": "string" },
      "status": { "type": "string", "enum": ["CREATED", "RUNNING", "COMPLETED", "FAILED", "CANCELLED"] },
      "current_stage": { "type": "string" },
      "started_at": { "type": ["string", "null"] },
      "finished_at": { "type": ["string", "null"] },
      "duration_seconds": { "type": ["number", "null"] },
      "stage_results": {
        "type": "object",
        "properties": {
          "snapshot": { "type": "object" },
          "dataset": { "type": "object" },
          "feature": { "type": "object" },
          "experiment": { "type": "object" },
          "evaluation": { "type": "object" },
          "registry": { "type": "object" },
          "dashboard": { "type": "object" }
        }
      }
    }
  }
  ```

---

## 3. Python Dataclasses (Code Contracts)

```python
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

@dataclass(frozen=True)
def StageExecutionRecord:
    stage_name: str
    status: str          # PENDING, RUNNING, COMPLETED, FAILED, SKIPPED
    input_payload: Dict[str, Any]
    output_payload: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    duration_seconds: Optional[float] = None

@dataclass
class ResearchJobDetails:
    job_id: str
    name: str
    status: str
    current_stage: Optional[str]
    started_at: Optional[str]
    finished_at: Optional[str]
    duration_seconds: Optional[float]
    steps: List[StageExecutionRecord] = field(default_factory=list)
```
