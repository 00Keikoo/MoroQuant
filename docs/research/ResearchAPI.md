# Research Platform API Specification

## Overview
This document specifies the REST API contracts for interacting with the MoroQuant Research Platform. These endpoints allow developers and quantitative researchers to register features, manage dataset creation, log experiments, perform model comparisons, and register promotion histories.

---

## 1. Datasets Endpoints

### `POST /api/v1/research/datasets`
Creates and registers a new dataset definition.
- **Request Body**:
  ```json
  {
    "name": "btc_volatility_dataset",
    "description": "Hourly dataset tracking BTC volatility metrics",
    "feature_ids": ["volatility.atr_14", "momentum.rsi_14"]
  }
  ```
- **Response (201 Created)**:
  ```json
  {
    "dataset_id": "c3e98f72-8705-4c07-b2f7-ec63a152e804",
    "name": "btc_volatility_dataset",
    "created_at": "2026-07-06T18:30:00Z"
  }
  ```

### `POST /api/v1/research/datasets/{dataset_id}/versions`
Generates a new, frozen dataset version for a specific timeframe.
- **Request Body**:
  ```json
  {
    "version": "1.0.0",
    "start_time": "2024-01-01T00:00:00Z",
    "end_time": "2025-12-31T23:00:00Z",
    "imputation_strategy": "forward_fill"
  }
  ```
- **Response (202 Accepted)**:
  ```json
  {
    "dataset_version_id": "8c7a10be-0985-48fa-95ee-d03b680790e6",
    "status": "PROCESSING",
    "fingerprint": null
  }
  ```

### `GET /api/v1/research/datasets/versions/{version_id}`
Retrieves metadata for a specific dataset version.
- **Response (200 OK)**:
  ```json
  {
    "dataset_version_id": "8c7a10be-0985-48fa-95ee-d03b680790e6",
    "dataset_id": "c3e98f72-8705-4c07-b2f7-ec63a152e804",
    "version": "1.0.0",
    "fingerprint": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "storage_uri": "s3://moroquant-datasets/btc_volatility_dataset_v1.0.0.parquet",
    "is_frozen": true,
    "created_at": "2026-07-06T18:32:00Z"
  }
  ```

---

## 2. Features Endpoints

### `POST /api/v1/research/features`
Registers a new feature definition in the system.
- **Request Body**:
  ```json
  {
    "name": "volatility.atr_14",
    "description": "Average True Range with window size 14",
    "feature_group": "volatility",
    "data_type": "float64",
    "version": "1.0.0",
    "source_code": "def get_atr(df): return talib.ATR(df.high, df.low, df.close, timeperiod=14)",
    "dependencies": ["ohlcv.high", "ohlcv.low", "ohlcv.close"]
  }
  ```
- **Response (201 Created)**:
  ```json
  {
    "feature_id": "a90f1d44-0b1e-450f-a2e6-df0cf6f6e520",
    "name": "volatility.atr_14",
    "version": "1.0.0"
  }
  ```

### `GET /api/v1/research/features`
Lists all registered features.
- **Query Params**: `group=volatility`, `status=ACTIVE`
- **Response (200 OK)**:
  ```json
  {
    "features": [
      {
        "feature_id": "a90f1d44-0b1e-450f-a2e6-df0cf6f6e520",
        "name": "volatility.atr_14",
        "version": "1.0.0",
        "status": "ACTIVE"
      }
    ]
  }
  ```

---

## 3. Experiments & Runs Endpoints

### `POST /api/v1/research/experiments`
Creates a new experiment.
- **Request Body**:
  ```json
  {
    "name": "exp_btc_trend_v1",
    "description": "BTC Trend-following model validation trials"
  }
  ```
- **Response (201 Created)**:
  ```json
  {
    "experiment_id": "b1b0deef-dcd2-4c28-98e3-0d322efef125",
    "name": "exp_btc_trend_v1"
  }
  ```

### `POST /api/v1/research/experiments/{experiment_id}/runs`
Initializes a new run under an experiment.
- **Request Body**:
  ```json
  {
    "dataset_version_id": "8c7a10be-0985-48fa-95ee-d03b680790e6",
    "hyperparameters": {
      "learning_rate": 0.05,
      "max_depth": 5
    }
  }
  ```
- **Response (201 Created)**:
  ```json
  {
    "run_id": "673f8a00-cb6b-4bfe-bb77-2c974c2d58cb",
    "status": "RUNNING"
  }
  ```

### `POST /api/v1/research/runs/{run_id}/metrics`
Logs key performance metrics for a specific run.
- **Request Body**:
  ```json
  {
    "metrics": [
      {"key": "sharpe_ratio", "value": 1.85, "step": 1},
      {"key": "max_drawdown", "value": -11.2, "step": 1},
      {"key": "ece", "value": 0.034, "step": 1}
    ]
  }
  ```
- **Response (200 OK)**:
  ```json
  {
    "status": "SUCCESS",
    "logged_metrics_count": 3
  }
  ```

---

## 4. Comparisons Endpoints

### `POST /api/v1/research/comparisons`
Retrieves a comparative analysis matrix for a list of runs.
- **Request Body**:
  ```json
  {
    "run_ids": [
      "673f8a00-cb6b-4bfe-bb77-2c974c2d58cb",
      "ae5891fc-f55a-40d6-b6b1-4a1e94de8d54"
    ]
  }
  ```
- **Response (200 OK)**:
  ```json
  {
    "comparison_matrix": {
      "673f8a00-cb6b-4bfe-bb77-2c974c2d58cb": {
        "sharpe": 1.85,
        "max_drawdown": -11.2,
        "ece": 0.034,
        "rank": 1
      },
      "ae5891fc-f55a-40d6-b6b1-4a1e94de8d54": {
        "sharpe": 1.42,
        "max_drawdown": -18.4,
        "ece": 0.076,
        "rank": 2
      }
    }
  }
  ```

---

## 5. Reports Endpoints

### `POST /api/v1/research/reports`
Generates a markdown summary evaluation report.
- **Request Body**:
  ```json
  {
    "name": "sprint_3_5_btc_volatility_summary",
    "run_ids": [
      "673f8a00-cb6b-4bfe-bb77-2c974c2d58cb",
      "ae5891fc-f55a-40d6-b6b1-4a1e94de8d54"
    ]
  }
  ```
- **Response (201 Created)**:
  ```json
  {
    "report_id": "f51950d2-43bb-4d7a-8b89-3df28d68962f",
    "report_url": "/api/v1/research/reports/f51950d2-43bb-4d7a-8b89-3df28d68962f"
  }
  ```

---

## 6. Metadata Endpoints

### `GET /api/v1/research/metadata`
Retrieves information about system properties, status, and size.
- **Response (200 OK)**:
  ```json
  {
    "registered_features_count": 142,
    "frozen_datasets_count": 38,
    "active_experiments_count": 9,
    "database_status": "CONNECTED",
    "storage_space_used_bytes": 1405892010
  }
  ```
