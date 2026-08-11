# Sprint 3.9D-12: Registry Governance API Layer

**Status**: ✅ Complete  
**Date**: 2026-08-11  
**ADR**: ADR-024 (Research Layer Boundaries)

## Objective

Expose registry governance queries through read-only FastAPI endpoints.

## Implementation

### Architecture

```
FastAPI Router
    ↓
RegistryAPIService (business logic)
    ↓
RegistryQueryEngine (data source)
    ↓
RegistrySnapshot + RegistryEventLedger
```

### Components Created

**ml_service/research/registry_api/**
- `__init__.py` - Module exports
- `schemas.py` - Pydantic response models (immutable)
- `service.py` - Business logic layer
- `router.py` - FastAPI endpoint definitions

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/registry/models` | GET | List all models with current state |
| `/api/v1/registry/models/{artifact_id}` | GET | Get model detail by artifact ID |
| `/api/v1/registry/summary` | GET | Get registry statistics |
| `/api/v1/registry/production-candidates` | GET | Get models ready for production |
| `/api/v1/registry/history/{artifact_id}` | GET | Get lifecycle history for model |

### Key Design Decisions

**1. Immutable Response Schemas**
- All Pydantic models use `ConfigDict(frozen=True)`
- Updated from deprecated `class Config` to modern ConfigDict syntax
- Prevents accidental mutation of API responses

**2. Deterministic Ordering**
- Models sorted by (symbol, timeframe)
- Guarantees consistent response order
- Essential for caching and testing

**3. Dependency Injection**
- `get_registry_service()` builds full dependency chain
- RegistryStoreService → Snapshot + Ledger → QueryEngine → APIService
- Clean separation of concerns, testable

**4. Read-Only Design**
- No database access in research layer
- No write operations
- All endpoints are GET only
- Delegates to registry_query as single source of truth

**5. Error Handling**
- 404 for missing models
- Proper HTTP status codes
- Clear error messages

### ADR-024 Compliance

✅ **API layer only** - No database imports  
✅ **No execution dependencies** - Pure research layer  
✅ **Immutable outputs** - All responses frozen  
✅ **Deterministic ordering** - Consistent sort order  
✅ **Delegates to registry_query** - Single source of truth

## Test Coverage

**tests/research/test_registry_api.py** - 19 tests, all passing

### Test Categories

1. **Service Layer Tests**
   - Empty result handling
   - Data transformation
   - Model lookup by ID
   - Summary statistics
   - Production candidates
   - History retrieval

2. **Schema Validation Tests**
   - Immutability enforcement
   - Structure validation
   - Frozen configuration

3. **Router Integration Tests**
   - Endpoint behavior
   - 404 handling
   - Dependency injection

4. **Determinism Tests**
   - Ordering consistency
   - Mutation prevention

5. **Route Integration Tests**
   - Verification of router registration on FastAPI app instance
   - Assert all 5 endpoints are exposed (/models, /models/{artifact_id:path}, /summary, /production-candidates, /history/{artifact_id:path})

### Test Results

```bash
PYTHONPATH=ml_service pytest tests/research/test_registry_api.py -v
# 19 passed

PYTHONPATH=ml_service pytest tests/research/ -v --tb=short
# 342 passed, 16 warnings
```

## Integration Points

### Existing Modules Used
- `registry_query` - Data source for all queries
- `registry_snapshot` - Current state provider
- `registry_event_ledger` - History provider
- `registry_store` - Persistence layer

### Router Integration
- The registry API router has been successfully registered in `ml_service/api/main.py`:
  ```python
  from ml_service.research.registry_api.router import router as registry_router
  app.include_router(registry_router)
  ```

## Response Schema Examples

### ModelSummaryResponse
```json
{
  "model_id": "models/BTCUSD_1h/20260801_120000",
  "symbol": "BTCUSD",
  "timeframe": "1h",
  "asset_class": "CRYPTO",
  "lifecycle_state": "APPROVED",
  "latest_event_type": "LIFECYCLE_TRANSITION"
}
```

### RegistrySummaryResponse
```json
{
  "total_models": 10,
  "by_asset_class": {"CRYPTO": 8, "PROXY": 2},
  "by_lifecycle_state": {"PRODUCTION": 3, "APPROVED": 5, "DEVELOPMENT": 2},
  "production_count": 3,
  "approved_count": 5
}
```

### ModelHistoryResponse
```json
{
  "query_type": "LIFECYCLE_HISTORY",
  "result_count": 2,
  "model_id": "models/BTCUSD_1h/20260801_120000",
  "history": [
    {
      "artifact_path": "models/BTCUSD_1h/20260801_120000",
      "event_type": "LIFECYCLE_TRANSITION",
      "from_state": null,
      "to_state": null,
      "timestamp": "2026-08-11T10:00:00Z",
      "metadata": null
    }
  ]
}
```

## Technical Notes

### Pydantic V2 Migration
- Updated from deprecated `class Config` pattern
- Using `ConfigDict(frozen=True)` for immutability
- Eliminates 7 deprecation warnings

### Registry Event Record Mapping
- `RegistryEventRecord` has limited fields (event_id, model_id, event_type, created_at, payload_hash)
- Mapped to `HistoryRecordResponse` with nullable from_state/to_state/metadata
- Future enhancement: deserialize payloads for richer history

### Path Parameter Handling
- Using `{artifact_id:path}` in router for artifact paths with slashes
- Allows IDs like "models/BTCUSD_1h/20260801_120000"

## Files Modified

**Created:**
- `ml_service/research/registry_api/__init__.py`
- `ml_service/research/registry_api/schemas.py`
- `ml_service/research/registry_api/service.py`
- `ml_service/research/registry_api/router.py`

**Updated:**
- `ml_service/api/main.py`
- `tests/research/test_registry_api.py`
- `graphify-out/graph.json` (knowledge graph)
- `graphify-out/GRAPH_REPORT.md` (graph documentation)

## Verification Commands

```bash
# Run registry API tests
pytest tests/research/test_registry_api.py -v

# Run all research tests
pytest tests/research/ -v --tb=short

# Update knowledge graph
graphify update .
```

## Next Steps

1. **Integration**: Add registry_api router to main.py
2. **Documentation**: Add API endpoint examples to README
3. **Enhancement**: Deserialize event payloads for richer history details
4. **Monitoring**: Add endpoint metrics/logging if needed

## Dependencies

- FastAPI
- Pydantic V2
- registry_query (Sprint 3.9D-11)
- registry_snapshot (Sprint 3.9D-5)
- registry_event_ledger (Sprint 3.9D-10)
- registry_store (Sprint 3.9D-6)

## Success Criteria

✅ All 5 endpoints implemented and registered  
✅ Immutable response schemas  
✅ Deterministic ordering  
✅ Read-only design  
✅ 19 tests passing  
✅ No database access in research layer  
✅ ADR-024 compliant  
✅ All research tests passing (342/342)  
✅ Knowledge graph updated

## Conclusion

Sprint 3.9D-12 successfully implements a read-only FastAPI layer for registry governance queries. The implementation follows ADR-024 boundaries, maintains immutability, provides deterministic ordering, and delegates all queries to the registry_query module. All tests pass with comprehensive coverage of service logic, schema validation, router behavior, and determinism guarantees.
