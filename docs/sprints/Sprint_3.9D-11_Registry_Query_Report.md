# Sprint 3.9D-11: Registry Query Engine

**Status:** ✅ Complete  
**Date:** 2026-08-08  
**Author:** CybxAI

## Overview

Implemented read-only query layer combining RegistrySnapshot and RegistryEventLedger data to provide comprehensive governance queries. Fully compliant with ADR-024: research layer only, no database, immutable outputs.

## Implementation

### Package Structure

Created `ml_service/research/registry_query/` with:

- `__init__.py` - Package exports
- `models.py` - Query result models
- `interfaces.py` - Protocol definitions
- `query.py` - Query engine implementation

### Models (models.py)

#### RegistryQueryResult

Frozen dataclass for immutable query results:

**Fields:**
- `query_type` - Type of query executed
- `result_count` - Number of results returned
- `results` - Tuple of result objects
- `metadata` - Optional query metadata dict

**Validation:**
- Enforces result_count matches tuple length
- Ensures query_type is non-empty
- Validates results is a tuple

#### ModelSummary

Lightweight model summary for list queries:

**Fields:**
- `model_id`, `symbol`, `timeframe`
- `asset_class`, `lifecycle_state`
- `latest_event_type` - Optional latest promotion decision

#### RegistrySummary

Summary statistics for entire registry:

**Fields:**
- `total_models` - Total model count
- `by_asset_class` - Dict of counts per asset class
- `by_lifecycle_state` - Dict of counts per state
- `production_count` - Models in PRODUCTION
- `approved_count` - Models in APPROVED

### Query Engine (query.py)

`RegistryQueryEngine` provides read-only query interface:

**Constructor:**
```python
def __init__(self, snapshot: RegistrySnapshot, ledger: RegistryEventLedger)
```

Combines current state (snapshot) with event history (ledger).

#### list_models() → RegistryQueryResult

Lists all models with current state and latest event:

**Returns:**
- Query type: "LIST_MODELS"
- Results: Tuple of ModelSummary objects
- Sorted by (symbol, timeframe) deterministically

**Example:**
```python
result = engine.list_models()
for model in result.results:
    print(f"{model.symbol} {model.timeframe}: {model.lifecycle_state}")
```

#### find_model(symbol, timeframe) → Optional[ModelSummary]

Finds specific model by symbol and timeframe:

**Returns:**
- ModelSummary if found
- None if not found

**Example:**
```python
btc_model = engine.find_model("BTCUSD", "1h")
if btc_model:
    print(f"Found: {btc_model.lifecycle_state}")
```

#### get_lifecycle_history(model_id) → RegistryQueryResult

Retrieves lifecycle event history for specific model:

**Returns:**
- Query type: "LIFECYCLE_HISTORY"
- Results: Tuple of RegistryEventRecord objects
- Metadata: {"model_id": model_id}

**Example:**
```python
history = engine.get_lifecycle_history("models/btc_1h.pkl")
for event in history.results:
    print(f"{event.created_at}: {event.event_type}")
```

#### get_promotion_history(model_id) → RegistryQueryResult

Retrieves promotion event history for specific model:

**Returns:**
- Query type: "PROMOTION_HISTORY"  
- Results: Tuple of RegistryEventRecord objects
- Metadata: {"model_id": model_id}

Identical to get_lifecycle_history (events are the same), provided for semantic clarity.

#### get_production_candidates() → RegistryQueryResult

Finds models ready for production promotion:

**Criteria:**
- Lifecycle state = APPROVED
- Validation available = True
- Calibration available = True
- Asset class = CRYPTO (excludes proxy)

**Returns:**
- Query type: "PRODUCTION_CANDIDATES"
- Results: Tuple of ModelSummary objects
- Sorted by (symbol, timeframe)

**Example:**
```python
candidates = engine.get_production_candidates()
print(f"Found {candidates.result_count} production candidates")
for model in candidates.results:
    print(f"  {model.symbol} {model.timeframe}")
```

#### get_registry_summary() → RegistrySummary

Aggregates statistics across entire registry:

**Returns:**
- Total model count
- Breakdown by asset class
- Breakdown by lifecycle state
- Production and approved counts

**Example:**
```python
summary = engine.get_registry_summary()
print(f"Total models: {summary.total_models}")
print(f"Crypto: {summary.by_asset_class.get('CRYPTO', 0)}")
print(f"Production: {summary.production_count}")
```

### Interfaces (interfaces.py)

`IRegistryQueryEngine` protocol defines query interface for type safety and dependency injection.

## Integration Flow

```
RegistrySnapshot (current state) + RegistryEventLedger (history)
    ↓
RegistryQueryEngine
    ↓
list_models() / find_model() / get_production_candidates()
get_lifecycle_history() / get_promotion_history()
get_registry_summary()
    ↓
Immutable query results
```

### Complete Example

```python
from ml_service.research.registry_snapshot import RegistrySnapshot
from ml_service.research.registry_event_ledger import RegistryEventLedger
from ml_service.research.registry_query import RegistryQueryEngine

# Load current state
snapshot = RegistrySnapshot.load("data/registry_snapshot.json")

# Load event history
ledger = RegistryEventLedger("data/promotion_events.jsonl")

# Create query engine
engine = RegistryQueryEngine(snapshot, ledger)

# Query 1: List all models
all_models = engine.list_models()
print(f"Total models: {all_models.result_count}")

# Query 2: Find specific model
btc_model = engine.find_model("BTCUSD", "1h")
if btc_model:
    print(f"BTC 1h status: {btc_model.lifecycle_state}")
    print(f"Latest event: {btc_model.latest_event_type}")

# Query 3: Production candidates
candidates = engine.get_production_candidates()
print(f"\nProduction candidates ({candidates.result_count}):")
for model in candidates.results:
    print(f"  {model.symbol} {model.timeframe}")

# Query 4: Model history
history = engine.get_lifecycle_history("models/btc_1h.pkl")
print(f"\nBTC 1h history ({history.result_count} events):")
for event in history.results:
    print(f"  {event.created_at}: {event.event_type}")

# Query 5: Registry summary
summary = engine.get_registry_summary()
print(f"\nRegistry Summary:")
print(f"  Total: {summary.total_models}")
print(f"  By asset class: {summary.by_asset_class}")
print(f"  By lifecycle: {summary.by_lifecycle_state}")
print(f"  Production: {summary.production_count}")
```

## Tests

Created `tests/research/test_registry_query.py` with 21 test cases:

### ADR-024 Compliance
- ✅ No SQLite imports
- ✅ No execution layer imports

### Immutability
- ✅ RegistryQueryResult frozen
- ✅ ModelSummary frozen
- ✅ RegistrySummary frozen
- ✅ Query engine never mutates inputs

### Query Operations
- ✅ list_models returns all models
- ✅ find_model returns model when found
- ✅ find_model returns None when not found
- ✅ get_lifecycle_history returns events
- ✅ get_promotion_history returns events
- ✅ get_production_candidates filters correctly
- ✅ Production candidates exclude proxy
- ✅ Production candidates require validation
- ✅ get_registry_summary aggregates stats

### Determinism
- ✅ Deterministic ordering (symbol, timeframe)
- ✅ Production candidates sorted deterministically

### Edge Cases
- ✅ Empty ledger integration
- ✅ Empty snapshot integration
- ✅ Query results with metadata

### Validation
- ✅ RegistryQueryResult validation

## Test Results

```
pytest tests/research/test_registry_query.py -v
```

**Result:** 21/21 passed (0.28s)

**Complete Promotion System Tests:**
```
pytest tests/research/test_promotion_engine.py \
       tests/research/test_promotion_workflow.py \
       tests/research/test_registry_event_ledger.py \
       tests/research/test_registry_query.py -v
```

**Result:** 74/74 passed
- 17 promotion_engine tests
- 18 promotion_workflow tests
- 18 registry_event_ledger tests
- 21 registry_query tests

## Architecture Alignment

✅ **ADR-024 Compliant:**
- Research layer only
- No database dependencies
- No execution layer imports
- Immutable outputs
- Deterministic ordering

✅ **Follows Existing Patterns:**
- Frozen dataclasses (like all sprint 3.9D models)
- Protocol interfaces (like IPromotionWorkflow)
- Read-only queries (no mutations)
- Tuple results (immutable collections)

✅ **Clean Separation:**
- Snapshot: Current state
- Ledger: Event history
- Query: Combined read-only view

## Files Created

1. `ml_service/research/registry_query/__init__.py`
2. `ml_service/research/registry_query/models.py`
3. `ml_service/research/registry_query/interfaces.py`
4. `ml_service/research/registry_query/query.py`
5. `tests/research/test_registry_query.py`

## Graph Update

Updated graphify knowledge graph:
- 16,447 nodes (+138 from Sprint 3.9D-10)
- 27,795 edges (+227 from Sprint 3.9D-10)
- 818 communities

## Relationship to Previous Sprints

| Sprint | Component | Purpose |
|--------|-----------|---------|
| 3.9D-5 | RegistrySnapshot | Current state |
| 3.9D-6 | RegistryStore | Persistence |
| 3.9D-7 | ModelLifecycle | State transitions |
| 3.9D-8 | PromotionEngine | Decision + scoring |
| 3.9D-9 | PromotionWorkflow | Event creation |
| 3.9D-10 | RegistryEventLedger | Durable history |
| 3.9D-11 | RegistryQueryEngine | Read-only queries |

**Design Principle:** Layered architecture
- Storage: Snapshot + Ledger
- Logic: Engine + Workflow
- Access: Query layer

## Query Patterns

### Pattern 1: Model Discovery

```python
# Find all crypto models in APPROVED state
all_models = engine.list_models()
approved_crypto = [
    m for m in all_models.results
    if m.asset_class == "CRYPTO" and m.lifecycle_state == "APPROVED"
]
```

### Pattern 2: Model Lookup

```python
# Check if specific model exists
model = engine.find_model("BTCUSD", "1h")
if model:
    print(f"Status: {model.lifecycle_state}")
else:
    print("Model not found")
```

### Pattern 3: Audit Trail

```python
# Review complete history of model
history = engine.get_lifecycle_history("models/btc_1h.pkl")
for event in history.results:
    print(f"{event.created_at}: {event.event_type} - {event.event_id}")
```

### Pattern 4: Production Readiness

```python
# Find models ready for production
candidates = engine.get_production_candidates()
if candidates.result_count > 0:
    print(f"Ready for production: {candidates.result_count}")
    for model in candidates.results:
        latest = model.latest_event_type or "NONE"
        print(f"  {model.symbol} {model.timeframe} - last: {latest}")
```

### Pattern 5: Registry Health

```python
# Check overall registry health
summary = engine.get_registry_summary()
print(f"Total models: {summary.total_models}")
print(f"Production: {summary.production_count} ({summary.production_count/summary.total_models*100:.1f}%)")
print(f"Approved: {summary.approved_count}")
print(f"Asset classes: {list(summary.by_asset_class.keys())}")
```

## Performance Characteristics

### Query Complexity

**list_models():** O(n) where n = model count
- Iterates all models once
- Looks up latest event per model (O(1) with ledger index)

**find_model():** O(n) linear search
- Could be optimized with index (future)
- Acceptable for research layer scale

**get_lifecycle_history():** O(m) where m = model events
- Delegates to ledger.get_model_history()
- Already filtered by model_id

**get_production_candidates():** O(n)
- Filters models by criteria
- Returns sorted results

**get_registry_summary():** O(n)
- Single pass aggregation
- Dict updates are O(1)

### Scalability

**Research layer scale:**
- Tens of models: instant
- Hundreds of models: fast
- Thousands of models: acceptable

**Future optimization options:**
- Index by symbol+timeframe for O(1) find_model()
- Cache get_registry_summary() if snapshot rarely changes
- Materialize view for common queries

## Use Cases

### 1. Model Governance Dashboard

Query engine provides data for governance UI:
- Registry summary for overview
- Production candidates for promotion workflow
- Model history for audit trail

### 2. Model Lifecycle Tracking

Track individual model progression:
- Current state from snapshot
- Event history from ledger
- Combined view from query engine

### 3. Production Readiness Reports

Generate reports on production readiness:
- Filter by lifecycle state
- Check validation/calibration availability
- Exclude proxy models

### 4. Compliance Auditing

Support compliance requirements:
- Complete event history per model
- Deterministic query results
- Immutable audit trail

### 5. Research Analysis

Support research queries:
- List models by criteria
- Aggregate statistics
- Track promotion patterns

## Future Enhancements

Potential extensions (execution layer):

1. **Query Optimization**
   - Index by symbol+timeframe
   - Cache registry summary
   - Materialized views

2. **Advanced Filters**
   - Date range queries
   - Complex criteria composition
   - Full-text search on metadata

3. **Aggregations**
   - Time-series metrics
   - Promotion rate analysis
   - Model performance correlation

4. **Export Formats**
   - CSV export for reports
   - JSON API endpoints
   - Graphical visualizations

5. **Real-time Queries**
   - Subscribe to query results
   - Incremental updates
   - Change notifications

## Design Decisions

### Why combine snapshot + ledger?

**Benefits:**
- Snapshot: Fast current state access
- Ledger: Complete event history
- Query: Unified read interface

**Alternative rejected:**
- Single source of truth → Either slow queries or incomplete history
- Separate APIs → Client complexity, inconsistent data

### Why deterministic ordering?

**Benefits:**
- Reproducible results
- Testability
- Cache-friendly

**Implementation:**
- Sort by (symbol, timeframe)
- Stable sort algorithm
- Consistent across queries

### Why immutable results?

**Benefits:**
- Thread-safe queries
- No accidental mutations
- Clear data flow

**Implementation:**
- Frozen dataclasses
- Tuple results (not lists)
- No setters or mutators

### Why no caching?

**Current approach:**
- Stateless query engine
- Read from snapshot + ledger on each query
- Simple, correct, transparent

**Future consideration:**
- Cache registry_summary if snapshot static
- Invalidate on snapshot change
- Measure before optimizing

## Compliance Verification

✅ **No database dependencies:**
- Verified via `test_no_sqlite_imports`
- Only uses RegistrySnapshot + RegistryEventLedger

✅ **No execution layer imports:**
- Verified via `test_no_execution_imports`
- Pure research layer component

✅ **Immutable outputs:**
- All dataclasses use `frozen=True`
- Results are tuples (not lists)
- Tests verify immutability

✅ **Deterministic ordering:**
- Sorted by (symbol, timeframe)
- Verified via `test_deterministic_ordering`
- Consistent across runs

## Summary

Sprint 3.9D-11 successfully delivered a read-only query engine with:

- RegistryQueryResult model for immutable results
- ModelSummary and RegistrySummary models
- RegistryQueryEngine with 6 query methods
- Full test coverage (21 tests)
- ADR-024 compliance verified
- Deterministic ordering
- Integration with snapshot + ledger

The query engine provides a clean, read-only interface for governance queries without database dependencies, completing the promotion system stack built across sprints 3.9D-8 through 3.9D-11.

**Complete Promotion System (Sprints 3.9D-8 through 3.9D-11):**

1. **PromotionEngine** (3.9D-8) - Decision + scoring
2. **PromotionWorkflow** (3.9D-9) - Event creation
3. **RegistryEventLedger** (3.9D-10) - Durable history
4. **RegistryQueryEngine** (3.9D-11) - Read-only queries

All four components work together to create a complete, immutable, auditable promotion and query system for model registry governance.
