# Sprint 3.9D-8: Promotion Decision Engine

**Status:** ✅ Complete  
**Date:** 2026-08-07  
**Author:** CybxAI

## Overview

Implemented deterministic promotion decision engine that evaluates model candidates and produces immutable promotion proposals. Fully compliant with ADR-024: research layer only, no database, no execution dependencies.

## Implementation

### Package Structure

Created `ml_service/research/promotion_engine/` with:

- `__init__.py` - Package exports
- `models.py` - Immutable data models
- `interfaces.py` - Protocol definitions
- `policy.py` - Asset-specific promotion rules
- `scorer.py` - Weighted scoring logic
- `engine.py` - Decision orchestration

### Models (models.py)

#### PromotionStatus Enum

```python
CANDIDATE    # Initial evaluation state
APPROVED     # Passed all criteria
REJECTED     # Failed criteria
BLOCKED      # Policy constraints prevent promotion
```

#### PromotionScore

Frozen dataclass with deterministic weighted scoring:

- `validation_score` (30%)
- `calibration_score` (20%)
- `lifecycle_score` (30%)
- `governance_score` (20%)

Enforces:
- Immutability via `frozen=True`
- Score range validation (0.0-1.0)
- Total score matches weighted sum

#### RegistryProposal

Frozen dataclass representing promotion decision:

Fields:
- `model_id`, `symbol`, `asset_class`
- `current_state`, `proposed_state`
- `status` (PromotionStatus)
- `score` (PromotionScore)
- `reason_codes` (tuple of strings)

Features:
- Deterministic JSON serialization via `to_dict()` and `to_json()`
- Reconstruction via `from_dict()`
- Full immutability and validation

### Scoring (scorer.py)

`PromotionScorer` implements deterministic weighted scoring:

**Validation Score:**
- Binary: 1.0 if validation_available, else 0.0

**Calibration Score:**
- Binary: 1.0 if calibration_available, else 0.0

**Lifecycle Score:**
- DISCOVERED: 0.0
- VALIDATED: 0.4
- GOVERNANCE_READY: 0.7
- APPROVED: 1.0
- PRODUCTION: 1.0
- REJECTED: 0.0

**Governance Score:**
- Binary: 1.0 if governance_ready in audit_report, else 0.0

### Policy (policy.py)

`PromotionPolicy` implements asset-specific rules:

**Crypto Models:**
- VALIDATED → APPROVED (if score ≥ 0.7)
- GOVERNANCE_READY → APPROVED (if score ≥ 0.7)
- APPROVED → PRODUCTION (if score ≥ 0.7)

**Proxy Models:**
- VALIDATED/GOVERNANCE_READY → APPROVED_RESEARCH (if score ≥ 0.7)
- Blocked from PRODUCTION
- Never allowed in production lifecycle

**Rejection Criteria:**
- Missing validation
- Missing calibration
- Lifecycle state = REJECTED
- Lifecycle state = DISCOVERED
- Unknown asset class
- Score below 0.7 threshold

### Engine (engine.py)

`PromotionEngine` orchestrates scoring and policy:

```python
def evaluate(
    model_identity: ModelIdentity,
    lifecycle_record: ModelLifecycleRecord,
    audit_report: dict,
) -> RegistryProposal
```

Flow:
1. Calculate promotion score via `PromotionScorer`
2. Apply policy rules via `PromotionPolicy`
3. Construct immutable `RegistryProposal`
4. Never mutates input objects

## Tests

Created `tests/research/test_promotion_engine.py` with 17 test cases:

### ADR-024 Compliance
- ✅ No database imports
- ✅ No execution layer imports

### Immutability
- ✅ PromotionScore frozen
- ✅ RegistryProposal frozen

### Determinism
- ✅ Scorer produces identical results
- ✅ Reason codes are deterministic
- ✅ Engine never mutates inputs

### Scoring
- ✅ Weighted calculation correctness
- ✅ Score validation

### Policy - Crypto
- ✅ VALIDATED → APPROVED
- ✅ APPROVED → PRODUCTION

### Policy - Proxy
- ✅ Blocked from PRODUCTION
- ✅ VALIDATED → APPROVED_RESEARCH

### Rejection
- ✅ Missing validation rejected
- ✅ Missing calibration rejected

### Serialization
- ✅ JSON round-trip deterministic

## Test Results

```
pytest tests/research/test_promotion_engine.py -v
```

**Result:** 17/17 passed (0.09s)

Full research suite: 7 pre-existing import errors (missing pandas/numpy) unrelated to promotion_engine.

## Integration Points

### Inputs
- `ModelIdentity` from `ml_service/research/model_identity/`
- `ModelLifecycleRecord` from `ml_service/research/model_lifecycle/`
- Audit report dict from `ml_service/research/model_registry_audit/`

### Outputs
- `RegistryProposal` with immutable promotion decision
- JSON serialization for persistence
- Deterministic reason codes for audit trail

## Architecture Alignment

✅ **ADR-024 Compliant:**
- Research layer only
- No database dependencies
- No execution layer imports
- Immutable outputs
- Deterministic results

✅ **Follows Existing Patterns:**
- Frozen dataclasses (like ModelLifecycleRecord)
- Protocol interfaces (like ILifecycleManager)
- Policy-based rules (like LifecyclePolicy)
- Scorer separation (deterministic components)

## Files Created

1. `ml_service/research/promotion_engine/__init__.py`
2. `ml_service/research/promotion_engine/models.py`
3. `ml_service/research/promotion_engine/interfaces.py`
4. `ml_service/research/promotion_engine/policy.py`
5. `ml_service/research/promotion_engine/scorer.py`
6. `ml_service/research/promotion_engine/engine.py`
7. `tests/research/test_promotion_engine.py`

## Graph Update

Updated graphify knowledge graph:
- 16,054 nodes
- 27,171 edges
- 811 communities

## Next Steps

Potential future enhancements:
1. Configurable scoring weights per asset class
2. Historical promotion tracking
3. Multi-stage promotion workflows
4. A/B testing promotion policies
5. Integration with registry mutation layer (execution phase)

## Summary

Sprint 3.9D-8 successfully delivered a deterministic promotion decision engine with:
- Immutable data models
- Weighted scoring (30/20/30/20)
- Asset-specific policies (crypto vs proxy)
- Full test coverage (17 tests)
- ADR-024 compliance
- JSON serialization support

The engine provides a foundation for deterministic model promotion decisions without database or execution dependencies, maintaining research layer purity.
