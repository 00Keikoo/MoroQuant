# Sprint 3.9D-6: Registry Persistence Layer

**Status**: ✅ Complete  
**Date**: 2026-08-07  
**Branch**: quant-research

## Overview

Implemented persistence abstraction for registry snapshots, enabling deterministic storage and retrieval of model registry state over time.

## Objectives

Create filesystem-based persistence for `RegistrySnapshot` with:
- No database dependency
- No execution layer coupling
- Deterministic JSON serialization
- Immutable artifacts
- Research layer only

## Implementation

### Package Structure

```
ml_service/research/registry_store/
├── __init__.py
├── models.py              # RegistrySnapshotRecord
├── interfaces.py          # RegistrySnapshotStore interface
├── json_store.py          # JsonRegistrySnapshotStore implementation
└── service.py             # RegistryStoreService high-level API
```

### Core Components

#### 1. RegistrySnapshotStore Interface

Abstract interface defining persistence contract:
- `save(snapshot) -> str` - persist snapshot, return ID
- `load(snapshot_id) -> RegistrySnapshot` - retrieve by ID
- `list_snapshots() -> tuple[RegistrySnapshotRecord, ...]` - sorted listing
- `get_latest() -> RegistrySnapshot | None` - most recent snapshot

**Location**: `ml_service/research/registry_store/interfaces.py`

#### 2. RegistrySnapshotRecord

Immutable frozen dataclass for snapshot metadata:
```python
@dataclass(frozen=True)
class RegistrySnapshotRecord:
    snapshot_id: str
    file_path: str
    created_at: str
    model_count: int
```

**Location**: `ml_service/research/registry_store/models.py`

#### 3. JsonRegistrySnapshotStore

Filesystem-based implementation:
- **Storage**: `storage/research_registry_snapshots/snapshot_*.json`
- **Format**: Deterministic JSON (sorted keys, indent=2)
- **Write**: Atomic (temp file + rename)
- **Serialization**: Full roundtrip of `RegistrySnapshot` → JSON → `RegistrySnapshot`

Key implementation details:
- No pickle - pure JSON only
- Atomic file writes prevent partial snapshots
- Corrupted files gracefully skipped during listing
- Deterministic key ordering for git-friendly diffs

**Location**: `ml_service/research/registry_store/json_store.py`

#### 4. RegistryStoreService

High-level service coordinating snapshot workflow:

```python
def create_snapshot(models: tuple[ModelIdentity, ...]) -> RegistrySnapshot
def get_latest_snapshot() -> RegistrySnapshot | None
def compare_with_latest(models) -> RegistryDiff | None
```

Workflow:
```
models → RegistrySnapshotBuilder → RegistrySnapshot → JsonRegistrySnapshotStore
```

**Location**: `ml_service/research/registry_store/service.py`

## ADR-024 Compliance

✅ **Research layer only** - no execution imports  
✅ **No sqlite** - pure JSON persistence  
✅ **No database dependency** - filesystem only  
✅ **No execution dependency** - verified in tests  
✅ **No PortfolioService** - no execution coupling  
✅ **No ExecutionSimulator** - research isolated  
✅ **Immutable artifacts** - frozen dataclasses  
✅ **Deterministic behavior** - sorted JSON, stable serialization

## Testing

### Test Coverage

Created `tests/research/test_registry_store.py` with 22 tests:

**JsonRegistrySnapshotStore Tests (13)**:
- Save/load roundtrip
- Serialization determinism
- Multiple snapshots ordering
- Latest snapshot retrieval
- Atomic file writes
- Corrupted file handling
- Empty store behavior

**RegistryStoreService Tests (5)**:
- Snapshot creation and persistence
- Latest snapshot retrieval
- Diff with previous snapshot
- Empty store handling

**Compliance Tests (4)**:
- No sqlite import verification
- No execution dependency verification
- Immutable record enforcement
- Frozen dataclass behavior

### Test Results

```
tests/research/test_registry_store.py: 22 passed
tests/research/: 223 passed, 14 warnings
```

All tests pass. No regressions in existing research test suite.

## Integration Points

### Upstream Dependencies
- `ml_service/research/model_identity` (ModelIdentity)
- `ml_service/research/registry_snapshot` (RegistrySnapshot, RegistrySnapshotBuilder, RegistryDiff, RegistryDiffEngine)

### Usage Example

```python
from ml_service.research.registry_store import RegistryStoreService
from ml_service.research.model_identity import ModelArtifactScanner

# Scan and persist
scanner = ModelArtifactScanner("models/")
models = scanner.scan()

service = RegistryStoreService()
snapshot = service.create_snapshot(models)

# Retrieve latest
latest = service.get_latest_snapshot()

# Compare with latest
diff = service.compare_with_latest(models)
if diff:
    print(f"Added: {len(diff.added_models)}")
    print(f"Removed: {len(diff.removed_models)}")
    print(f"Modified: {len(diff.modified_models)}")
```

## File Manifest

### Created Files
- `ml_service/research/registry_store/__init__.py`
- `ml_service/research/registry_store/models.py`
- `ml_service/research/registry_store/interfaces.py`
- `ml_service/research/registry_store/json_store.py`
- `ml_service/research/registry_store/service.py`
- `tests/research/test_registry_store.py`
- `docs/sprints/Sprint_3.9D-6_Registry_Store_Report.md`

### Modified Files
None - pure addition to codebase.

## Storage Format

### Snapshot File Structure

```json
{
  "created_at": "2024-01-15T10:00:00Z",
  "models": [
    {
      "artifact_path": "models/BTCUSDT_4h_xgboost_crypto.pkl",
      "asset_class": "crypto",
      "calibration_available": true,
      "feature_count": 42,
      "feature_fingerprint": "abc123",
      "lifecycle_status": "production",
      "model_type": "xgboost",
      "sample_count": 1000,
      "symbol": "BTCUSDT",
      "timeframe": "4h",
      "trained_at": "2024-01-15T10:00:00Z",
      "validation_available": true
    }
  ],
  "snapshot_id": "registry_20240115_100000_a1b2c3",
  "summary": {
    "crypto": 2,
    "production": 2
  },
  "total_models": 2
}
```

### File Naming

Pattern: `snapshot_{snapshot_id}.json`  
Location: `storage/research_registry_snapshots/`

## Knowledge Graph Update

Updated graphify knowledge graph with new registry_store components:
- 15,767 nodes (+7 new)
- 26,661 edges
- 793 communities

## Next Steps

Potential future enhancements (not in scope):
1. Snapshot compression for large registries
2. Incremental diffs between arbitrary snapshots
3. Snapshot retention policies
4. Migration tooling for schema evolution

## Sprint Metrics

- **Lines Added**: ~350 (implementation + tests)
- **Test Coverage**: 22 tests, 100% pass rate
- **Dependencies**: 0 new external dependencies
- **ADR Violations**: 0

## Conclusion

Sprint 3.9D-6 successfully delivered a clean persistence abstraction for registry snapshots. The implementation maintains strict isolation from execution layers, uses deterministic JSON serialization, and provides comprehensive test coverage. All ADR-024 requirements met.
