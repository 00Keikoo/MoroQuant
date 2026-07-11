# Timeline API Contract Specification

**Sprint**: 4.7A  
**Status**: DESIGN COMPLETE  
**Auditor**: Antigravity

---

## 1. REST Endpoints

### 1.1 GET `/api/lab/timeline`
Retrieve chronological timeline events.

*   **Query Parameters**:
    *   `limit`: Integer (default: 50)
    *   `event_type`: String (optional, e.g. `PROMOTION`, `FAILED`)
    *   `start_time`: Integer (optional, timestamp)
*   **Response Payload (`200 OK`)**:
    ```json
    {
      "events": [
        {
          "event_id": "evt_99824f",
          "timestamp": 1783838202,
          "event_type": "MODEL_PROMOTED",
          "summary": "Model XGBoost-BTC 1h promoted to Production",
          "user": "scheduler",
          "run_id": "run_0283",
          "metadata": {
            "model_version": "v1.4.2",
            "f1_score": 0.682,
            "ece": 0.024
          }
        }
      ]
    }
    ```

### 1.2 GET `/api/lab/timeline/{run_id}/lineage`
Retrieve the complete lineage graph for a specific experiment run.

*   **Response Payload (`200 OK`)**:
    ```json
    {
      "nodes": [
        { "id": "ds_v1.0", "type": "DATASET", "label": "BTCUSDT 1h v1.0" },
        { "id": "feat_v1.0", "type": "FEATURE_SET", "label": "Base Features v1.0" },
        { "id": "run_0283", "type": "RUN", "label": "XGBoost Training Run" }
      ],
      "edges": [
        { "source": "ds_v1.0", "target": "run_0283" },
        { "source": "feat_v1.0", "target": "run_0283" }
      ]
    }
    ```

### 1.3 GET `/api/lab/timeline/active-progress`
Get real-time training progress of active runs.

*   **Response Payload (`200 OK`)**:
    ```json
    {
      "active_runs": [
        {
          "run_id": "run_9941",
          "status": "VALIDATING",
          "progress_pct": 65.5,
          "started_at": 1783838000,
          "estimated_completion": 1783838500
        }
      ]
    }
    ```
