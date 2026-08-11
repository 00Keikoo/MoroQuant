# Sprint 3.9D-9: Model Registry Promotion Workflow

**Status:** ✅ Complete  
**Date:** 2026-08-07  
**Author:** CybxAI

## Overview

Implemented research-only workflow that consumes `RegistryProposal` from the Promotion Decision Engine and creates immutable `PromotionEvent` records. Fully compliant with ADR-024: research layer only, no database, no execution dependencies, no model file mutation.

## Implementation

### Package Structure

Created `ml_service/research/promotion_workflow/` with:

- `__init__.py` - Package exports
- `models.py` - PromotionEvent immutable model
- `interfaces.py` - Protocol definitions
- `policy.py` - Workflow policy enforcement
- `workflow.py` - Workflow orchestration

### Models (models.py)

#### PromotionEvent

Frozen dataclass representing immutable promotion event:

**Fields:**
- `event_id` - Deterministic hash (SHA256, 16 chars)
- `model_id` - Model artifact identifier
- `from_state` - Source lifecycle state
- `to_state` - Target lifecycle state
- `decision` - "APPROVED" or "REJECTED"
- `reason_codes` - Tuple of decision rationale
- `created_at` - ISO8601 timestamp with UTC

**Features:**
- Deterministic event ID generation via `generate_event_id()`
- JSON serialization via `to_dict()` and `to_json()`
- Reconstruction via `from_dict()`
- Full immutability and validation

**Event ID Generation:**
```python
content = f"{model_id}|{from_state}|{to_state}|{created_at}"
event_id = hashlib.sha256(content.encode()).hexdigest()[:16]
```

Deterministic IDs ensure reproducibility and prevent duplicate event creation.

### Policy (policy.py)

`WorkflowPolicy` enforces promotion rules:

**Rules:**

1. **APPROVED proposals** → Can promote
2. **REJECTED proposals** → Cannot promote
3. **BLOCKED proposals** → Cannot promote
4. **Proxy models to PRODUCTION** → Blocked

**Method:**
```python
def can_promote(proposal: RegistryProposal) -> tuple[bool, tuple[str, ...]]
```

Returns `(allowed, reason_codes)` for audit trail.

**Reason Codes:**
- `PROMOTION_APPROVED` - Proposal approved
- `PROPOSAL_REJECTED` - Proposal rejected
- `PROPOSAL_BLOCKED` - Proposal blocked
- `PROXY_CANNOT_BE_PRODUCTION` - Proxy blocked from production
- `PROPOSAL_NOT_APPROVED` - Proposal not in approved state

### Workflow (workflow.py)

`PromotionWorkflow` orchestrates event creation:

**Methods:**

#### evaluate(proposal) → Optional[PromotionEvent]
- Evaluates proposal eligibility
- Returns event if eligible, None if blocked
- Primary entry point for workflow

#### approve(proposal) → PromotionEvent
- Creates promotion event for APPROVED proposal
- Appends `WORKFLOW_APPROVED` reason code
- Generates deterministic event ID
- Sets decision to "APPROVED"

#### reject(proposal) → PromotionEvent
- Creates rejection event
- Appends `WORKFLOW_REJECTED` reason code
- Sets from_state = to_state (no transition)
- Sets decision to "REJECTED"

**Behavior:**
- Never mutates input proposal
- Never mutates model files
- Always creates immutable events
- Accumulates reason codes from proposal

### Interfaces (interfaces.py)

Protocol definitions for type safety:

- `IWorkflowPolicy` - Policy enforcement protocol
- `IPromotionWorkflow` - Workflow orchestration protocol

Enables dependency injection and testing.

## Integration with Sprint 3.9D-8

### Input: RegistryProposal

Consumes proposals from `PromotionEngine.evaluate()`:

```python
from ml_service.research.promotion_engine import PromotionEngine
from ml_service.research.promotion_workflow import PromotionWorkflow

engine = PromotionEngine()
workflow = PromotionWorkflow()

# Generate proposal
proposal = engine.evaluate(model_identity, lifecycle_record, audit_report)

# Create event if eligible
event = workflow.evaluate(proposal)
```

### Output: PromotionEvent

Immutable event record suitable for:
- Event store persistence
- Audit trail generation
- Registry update orchestration (future execution layer)
- Compliance reporting

## Tests

Created `tests/research/test_promotion_workflow.py` with 18 test cases:

### ADR-024 Compliance
- ✅ No database imports
- ✅ No execution layer imports

### Immutability
- ✅ PromotionEvent frozen
- ✅ Workflow never mutates proposals

### Determinism
- ✅ Event IDs deterministic
- ✅ Event IDs unique per transition
- ✅ JSON serialization deterministic

### Validation
- ✅ PromotionEvent field validation

### Workflow Logic
- ✅ Approved proposal creates event
- ✅ Rejected proposal blocked
- ✅ Blocked proposal blocked
- ✅ Proxy production blocked

### Policy Enforcement
- ✅ Policy allows approved
- ✅ Policy blocks rejected
- ✅ Policy blocks proxy production

### Event Creation
- ✅ approve() creates promotion event
- ✅ reject() creates rejection event
- ✅ Reason codes accumulate

## Test Results

```
pytest tests/research/test_promotion_workflow.py -v
```

**Result:** 18/18 passed (0.07s)

**Combined with Sprint 3.9D-8:**
```
pytest tests/research/test_promotion_engine.py tests/research/test_promotion_workflow.py -v
```

**Result:** 35/35 passed (0.26s)
- 17 promotion_engine tests
- 18 promotion_workflow tests

## Architecture Flow

```
ModelIdentity + LifecycleRecord + AuditReport
    ↓
PromotionEngine.evaluate()
    ↓
RegistryProposal (APPROVED/REJECTED/BLOCKED)
    ↓
PromotionWorkflow.evaluate()
    ↓
PromotionEvent (if eligible) or None (if blocked)
```

## Example Usage

### Successful Promotion

```python
from ml_service.research.model_identity import ModelIdentity
from ml_service.research.model_lifecycle import ModelLifecycleRecord, LifecycleState
from ml_service.research.promotion_engine import PromotionEngine
from ml_service.research.promotion_workflow import PromotionWorkflow

# Input data
identity = ModelIdentity(
    artifact_path="models/btc_h1_lgbm.pkl",
    symbol="BTCUSD",
    timeframe="1h",
    model_type="lightgbm",
    asset_class="CRYPTO",
    feature_count=15,
    feature_fingerprint="abc123",
    trained_at="2026-08-07T10:00:00Z",
    validation_available=True,
    calibration_available=True,
    sample_count=10000,
    lifecycle_status="VALIDATED",
)

lifecycle = ModelLifecycleRecord(
    artifact_path="models/btc_h1_lgbm.pkl",
    symbol="BTCUSD",
    asset_class="CRYPTO",
    current_state=LifecycleState.VALIDATED,
    previous_state=LifecycleState.DISCOVERED,
    reason="Validation metrics available",
    timestamp="2026-08-07T12:00:00Z",
)

audit = {"governance_ready": True}

# Decision flow
engine = PromotionEngine()
workflow = PromotionWorkflow()

proposal = engine.evaluate(identity, lifecycle, audit)
# RegistryProposal(status=APPROVED, proposed_state="APPROVED", ...)

event = workflow.evaluate(proposal)
# PromotionEvent(
#     event_id="a1b2c3d4e5f6g7h8",
#     model_id="models/btc_h1_lgbm.pkl",
#     from_state="VALIDATED",
#     to_state="APPROVED",
#     decision="APPROVED",
#     reason_codes=("CRYPTO_VALIDATED_TO_APPROVED", "WORKFLOW_APPROVED"),
#     created_at="2026-08-07T21:45:30Z"
# )
```

### Blocked Promotion (Proxy to Production)

```python
# Proxy model attempting production
identity = ModelIdentity(
    artifact_path="models/spy_proxy.pkl",
    symbol="SPY",
    asset_class="PROXY",
    # ... other fields
)

lifecycle = ModelLifecycleRecord(
    current_state=LifecycleState.APPROVED,
    # ... other fields
)

proposal = engine.evaluate(identity, lifecycle, audit)
# RegistryProposal(status=BLOCKED, reason_codes=("PROXY_BLOCKED_FROM_PRODUCTION",))

event = workflow.evaluate(proposal)
# None (blocked by policy)
```

## Architecture Alignment

✅ **ADR-024 Compliant:**
- Research layer only
- No database dependencies
- No execution layer imports
- No model file mutation
- Immutable outputs
- Deterministic results

✅ **Follows Existing Patterns:**
- Frozen dataclasses (like PromotionScore, ModelLifecycleRecord)
- Protocol interfaces (like IPromotionPolicy)
- Policy-based rules (like LifecyclePolicy, PromotionPolicy)
- Event-driven architecture
- Deterministic event IDs

✅ **Clean Separation:**
- Decision (PromotionEngine) vs Workflow (PromotionWorkflow)
- Proposal (intent) vs Event (fact)
- Research layer vs future execution layer

## Files Created

1. `ml_service/research/promotion_workflow/__init__.py`
2. `ml_service/research/promotion_workflow/models.py`
3. `ml_service/research/promotion_workflow/interfaces.py`
4. `ml_service/research/promotion_workflow/policy.py`
5. `ml_service/research/promotion_workflow/workflow.py`
6. `tests/research/test_promotion_workflow.py`

## Graph Update

Updated graphify knowledge graph:
- 16,179 nodes (+125 from Sprint 3.9D-8)
- 27,376 edges (+205 from Sprint 3.9D-8)
- 818 communities

## Relationship to Sprint 3.9D-8

| Sprint 3.9D-8 | Sprint 3.9D-9 |
|---------------|---------------|
| **PromotionEngine** | **PromotionWorkflow** |
| Evaluates eligibility | Enforces workflow rules |
| Produces RegistryProposal | Consumes RegistryProposal |
| Decision + rationale | Event creation |
| Scoring + policy | Policy + orchestration |
| Immutable proposal | Immutable event |

**Design Principle:** Separation of concerns
- Engine: "Should this model be promoted?" (scoring + policy)
- Workflow: "Can we create an event for this proposal?" (workflow rules)

## Next Steps

Potential future enhancements:

1. **Event Store Integration** (execution layer)
   - Persist PromotionEvent to event store
   - Build event-sourced state from events
   - Query historical promotion decisions

2. **Registry Mutation** (execution layer)
   - Consume PromotionEvent to update registry
   - Apply state transitions to model records
   - Maintain audit trail

3. **Approval Workflows**
   - Multi-stage approvals
   - Human-in-the-loop decisions
   - Rollback mechanisms

4. **Event Subscriptions**
   - Notify on promotion events
   - Trigger downstream workflows
   - Integration with monitoring systems

5. **Batch Workflows**
   - Evaluate multiple models in parallel
   - Atomic batch promotions
   - Transaction-like semantics

## Compliance Verification

✅ **No database dependencies:**
- Verified via `test_no_database_imports`
- Manual inspection of all modules

✅ **No execution layer imports:**
- Verified via `test_no_execution_imports`
- No PortfolioService, ExecutionSimulator, or ml_service.execution

✅ **No model file mutation:**
- Workflow reads proposals only
- Never touches artifact files
- All outputs are new immutable objects

✅ **Immutable outputs:**
- All dataclasses use `frozen=True`
- Tests verify immutability via AttributeError
- JSON serialization preserves immutability

✅ **Deterministic results:**
- Event IDs deterministic from content
- Same inputs always produce same event ID
- Verified via `test_deterministic_event_ids`

## Summary

Sprint 3.9D-9 successfully delivered a research-only promotion workflow with:

- Immutable PromotionEvent model
- Deterministic event ID generation (SHA256, 16 chars)
- Policy enforcement for workflow rules
- Workflow orchestration (evaluate, approve, reject)
- Full test coverage (18 tests)
- ADR-024 compliance verified
- JSON serialization support
- Clean integration with Sprint 3.9D-8

The workflow provides a foundation for event-driven promotion orchestration without database or execution dependencies, maintaining research layer purity while enabling future execution layer integration through immutable event streams.
