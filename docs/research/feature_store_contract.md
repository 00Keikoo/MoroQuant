# Feature Store Data Contract Specification

This document details the data contracts, schemas, and representation formats for the Feature Store.

---

## 1. Schema Definitions

### 1.1 Feature Metadata JSON Schema
Each computed feature dataset must register a metadata payload conforming to this schema:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "FeatureDatasetMetadata",
  "type": "object",
  "required": [
    "feature_dataset_id",
    "source_dataset_id",
    "feature_version_id",
    "fingerprint",
    "created_at",
    "lifecycle_state",
    "storage_path"
  ],
  "properties": {
    "feature_dataset_id": {
      "type": "string",
      "pattern": "^fds_[a-z0-9_]+_v[0-9]+\\.[0-9]+\\.[0-9]+_ds_[a-z0-9_]+$"
    },
    "source_dataset_id": {
      "type": "string",
      "description": "Identifier of the parent dataset"
    },
    "feature_version_id": {
      "type": "string",
      "description": "Identifier of the feature definition version"
    },
    "fingerprint": {
      "type": "string",
      "description": "SHA256 signature of canonicalized feature columns"
    },
    "created_at": {
      "type": "string",
      "format": "date-time"
    },
    "lifecycle_state": {
      "type": "string",
      "enum": ["CREATED", "COMPUTED", "VALIDATED", "FROZEN", "DEPRECATED", "ARCHIVED"]
    },
    "storage_path": {
      "type": "string",
      "description": "Absolute filesystem path to the immutable feature parquet payload"
    }
  }
}
```

### 1.2 Python Dataclasses (Code Contract)

```python
from dataclasses import dataclass
from typing import Dict, Any, Optional

@dataclass(frozen=True)
class FeatureDefinition:
    feature_name: str
    description: str
    formula_ref: str
    created_at: str

@dataclass(frozen=True)
class FeatureVersion:
    feature_version_id: str
    feature_name: str
    version: str
    parameters: Dict[str, Any]
    created_at: str

@dataclass(frozen=True)
class FeatureDatasetMetadata:
    feature_dataset_id: str
    source_dataset_id: str
    feature_version_id: str
    fingerprint: str
    created_at: str
    lifecycle_state: str
    storage_path: str
    is_frozen: bool = False
```

---

## 2. Payload Format & Storage Design

* **File Format**: Apache Parquet.
* **Storage Location**: `/home/zafka/trade-dashboard/storage/features/{feature_dataset_id}.parquet`
* **Structure Alignment**:
  * Feature parquet payloads store the index keys (`timestamp`, `symbol`) followed by the computed feature columns.
  * Col order rule:
    1. `timestamp` (Unix timestamp, type `int64`)
    2. `symbol` (String index)
    3. Engineered feature columns (sorted alphabetically)

---

## 3. Serialization and Merging Rules

When the Experiment Engine or Replay Engine requests features, the Feature Service merges the source dataset with the requested feature dataset:

```python
def merge_dataset_features(
    source_df: pd.DataFrame, 
    feature_df: pd.DataFrame
) -> pd.DataFrame:
    """Combines a base dataset with computed features.
    
    Enforces:
    - Primary index verification: (timestamp, symbol) must match exactly.
    - No rows added or dropped (Inner Join with assertion checks).
    """
    assert len(source_df) == len(feature_df), "Row count mismatch in feature merge"
    merged = pd.merge(
        source_df, 
        feature_df, 
        on=['timestamp', 'symbol'], 
        how='inner'
    )
    assert len(merged) == len(source_df), "Index alignment mismatch in feature merge"
    return merged
```
