# Research Architecture Continuation Audit

**Date:** 2026-08-13  
**Auditor:** CybxAI  
**Context:** Post-Sprint 3.9D-13 State Analysis  
**Branch:** quant-research  
**Test Baseline:** 342 passing tests

---

## 1. Current State

### Completed Sprints
- **Sprint 3.9D-1**: Research Benchmark (5 tests)
- **Sprint 3.9D-2**: Model Promotion (12 tests)
- **Sprint 3.9D-3**: Model Governance (12 tests)
- **Sprint 3.9D-5**: Registry Snapshot (17 tests)
- **Sprint 3.9D-6**: Registry Store (22 tests)
- **Sprint 3.9D-7**: Model Lifecycle (26 tests)
- **Sprint 3.9D-8**: Promotion Decision Engine (17 tests)
- **Sprint 3.9D-9**: Promotion Workflow (18 tests)
- **Sprint 3.9D-10**: Registry Event Ledger (18 tests)
- **Sprint 3.9D-11**: Registry Query Engine (21 tests)
- **Sprint 3.9D-12**: Registry Governance API (19 tests)
- **Sprint 3.9D-13**: Registry API Integration Verification (COMPLETE)

### Registry Governance Stack (Sprints 3.9D-5 through 3.9D-13)
The last 9 sprints built a complete registry governance subsystem:
- **State Management**: RegistrySnapshot, RegistryStore
- **Lifecycle**: ModelLifecycleManager with asset-specific policies
- **Decision Engine**: PromotionEngine with weighted scoring (30/20/30/20)
- **Workflow**: PromotionWorkflow with policy enforcement
- **Event Sourcing**: RegistryEventLedger (append-only JSONL)
- **Query Layer**: RegistryQueryEngine (read-only)
- **API Layer**: FastAPI endpoints (GET-only, immutable responses)

**Total Registry Stack**: ~2,800 lines of implementation + 187 tests

---

## 2. Pipeline Coverage Matrix

| Pipeline Stage | Status | Existing Component | Integration Status |
|---|---|---|---|
| **DatasetSnapshot / DatasetMetadata** | ⚠️ PARTIAL | `dataset_snapshot.py`, `DatasetManager` | Exists but isolated |
| **Replay Engine** | ⚠️ BROKEN | `replay_engine/` | **FAIL** per Sprint 3.5 Audit (API mismatch, trade mapping bug) |
| **FeatureContext** | ✅ COMPLETE | `strategy/features/context.py`, `FeatureContextService` | Integrated |
| **FeatureSnapshot** | ✅ COMPLETE | `feature_snapshot.py` | Integrated |
| **MLInferenceAdapter** | ✅ COMPLETE | `strategy/inference/adapter.py` | Integrated |
| **DecisionTruth / DecisionEngine** | ✅ COMPLETE | `decision_truth/decision_engine.py` | Verified, deterministic |
| **SignalGenerator** | ✅ COMPLETE | `strategy/signal/generator.py` | Integrated |
| **Evaluation Engine** | ⚠️ BROKEN | `evaluation_engine/` | **FAIL** per Sprint 3.5 Audit (hardcoded metrics, broken profit factor) |
| **Reporting / ResearchReport** | ⚠️ PARTIAL | `reporting/` | Exists but disconnected from benchmark |
| **Research Benchmark** | ✅ COMPLETE | `benchmark/` (Sprint 3.9D-1) | **ISOLATED** - not connected to evaluation engine |
| **Promotion Engine** | ✅ COMPLETE | `promotion_engine/` (Sprint 3.9D-8) | **ISOLATED** - not connected to benchmark |
| **Governance Engine** | ✅ COMPLETE | `governance/` (Sprint 3.9D-3) | **ISOLATED** - not connected to promotion |
| **Registry Proposal** | ✅ COMPLETE | `promotion_workflow/models.py` | **ISOLATED** - end of governance chain |

**Key Finding**: The registry governance stack (3.9D-1 through 3.9D-13) exists as a **parallel, disconnected subsystem**. It does NOT consume outputs from the earlier research pipeline (DatasetSnapshot → Replay → Evaluation → Reporting).

---

## 3. Registry Governance Coverage

### What 3.9D-5 through 3.9D-13 Provides

**Snapshot & Storage (3.9D-5, 3.9D-6)**:
- Deterministic registry state capture
- Immutable filesystem persistence (JSONL)
- Diff detection between snapshots
- Zero database dependencies

**Lifecycle Management (3.9D-7)**:
- State machine: DISCOVERED → VALIDATED → GOVERNANCE_READY → APPROVED → PRODUCTION
- Asset-specific policies (crypto full path, proxy blocked from production)
- Immutable lifecycle records

**Promotion Decision (3.9D-8)**:
- Weighted scoring: validation (30%), calibration (20%), lifecycle (30%), governance (20%)
- Asset-specific promotion rules
- Immutable RegistryProposal output

**Workflow & Events (3.9D-9, 3.9D-10)**:
- Event creation with deterministic IDs (SHA256)
- Append-only event ledger (JSONL)
- Workflow policy enforcement (proxy blocking, approval gates)

**Query & API (3.9D-11, 3.9D-12)**:
- Read-only query engine combining snapshot + ledger
- Production candidate filtering
- FastAPI endpoints with immutable responses

**What It Does NOT Provide**:
- No connection to `EvaluationEngine` outputs
- No consumption of `ResearchReport` from evaluation
- No integration with `BenchmarkResult` scoring
- No bridge from replay/experiment results to promotion decisions

---

## 4. Missing / Disconnected Components

### Critical Gaps

**1. Evaluation Engine is Broken** (Sprint 3.5 Audit, Section 5)
- Hardcoded Sharpe = 0.0, Max Drawdown = 0.0
- Algebraically broken Profit Factor calculation
- Heuristic Sortino ratio (Sharpe × √2) mathematically invalid
- **Status**: FAIL

**2. Replay Engine is Broken** (Sprint 3.5 Audit, Section 4)
- Trade mapping bug: maps `trade.id` to `signal_id` (wrong join key)
- Verification script crashes (API mismatch)
- **Status**: FAIL

**3. Benchmark → Promotion Integration Missing**
- `BenchmarkResult` (3.9D-1) is NOT consumed by `PromotionEngine` (3.9D-8)
- `PromotionEngine.evaluate()` expects `ModelIdentity`, `ModelLifecycleRecord`, `audit_report`
- **No bridge** from benchmark scores to promotion scoring

**4. Evaluation → Benchmark Integration Missing**
- `EvaluationEngine` outputs need to feed `BenchmarkResult`
- Currently no path from evaluation metrics to benchmark composite scoring
- Evaluation engine is broken anyway (see #1)

**5. Reporting → Benchmark Integration Missing**
- `ResearchReport` (Sprint 3.9C-6) exists but not connected to benchmark
- Benchmark expects `BenchmarkResult`, not `ResearchReport`

**6. DatasetSnapshot → Research Pipeline Integration Unclear**
- `DatasetSnapshot` exists but integration with replay/evaluation unclear
- No clear path from dataset capture to experiment execution

### Components That Exist But Are Isolated

**Research Benchmark** (3.9D-1):
- Composite scoring: Sharpe (30%), Sortino (20%), Profit Factor (20%), Win Rate (15%), Drawdown Recovery (15%)
- Deterministic ranking with tie-breaking
- **Problem**: No upstream inputs, no downstream consumers

**Promotion/Governance Stack** (3.9D-2, 3.9D-3, 3.9D-8, 3.9D-9):
- Complete promotion decision → workflow → event → query pipeline
- **Problem**: Operates on `ModelIdentity` and lifecycle states, not on evaluation results

**Reporting** (3.9C-6):
- ResearchReport generation exists
- **Problem**: Not connected to benchmark or promotion

---

## 5. Architecture Drift

### Deviations from ADR-024 / Full Architecture Audit

**POSITIVE DRIFT** (Good):
1. **Registry governance is now research-layer-pure**: All Sprint 3.9D components maintain ADR-024 boundaries (no database, no execution coupling, immutable outputs)
2. **Event sourcing added**: RegistryEventLedger provides append-only audit trail not in original design
3. **Query layer added**: RegistryQueryEngine provides read-only access pattern

**NEGATIVE DRIFT** (Problems):
1. **Evaluation Engine remains broken**: Sprint 3.5 Audit identified critical flaws (hardcoded metrics, broken profit factor) that were never fixed
2. **Replay Engine remains broken**: Sprint 3.5 Audit identified API mismatches and trade mapping bugs that were never fixed
3. **Pipeline fragmentation**: Registry governance built as parallel system instead of downstream consumer of evaluation results
4. **No ResearchSession orchestration**: ADR-024 Section 11 defined `ResearchSession` as umbrella entity linking all components. This was never implemented.

### Duplicate Abstractions

**Promotion Decision Models**:
- `promotion/models.py`: PromotionDecision (3.9D-2, older)
- `promotion_engine/models.py`: RegistryProposal (3.9D-8, newer)
- **Status**: Both exist, unclear which is canonical

**Governance Models**:
- `governance/models.py`: RegistryProposal (3.9D-3, older)
- `promotion_engine/models.py`: RegistryProposal (3.9D-8, newer)
- **Status**: Naming collision, unclear integration

**Recommendation**: Audit and consolidate. Likely the newer promotion_engine/promotion_workflow stack (3.9D-8, 3.9D-9) supersedes the older promotion/governance stack (3.9D-2, 3.9D-3).

---

## 6. Existing Roadmap Candidates

### Sprint 3.5 Remediation (Never Completed)

**Sprint 3.5 Audit Verdict**: FAIL  
**Recommended Next Sprint**: Sprint 3.6 - Research Rigor & Integration Remediation

**Required Fixes** (from Sprint 3.5 Audit, Section 9):
1. Fix API and ID mappings in `replay_engine/replay.py`
2. Implement true metric calculations in `experiment_engine/engine.py`
3. Correct bootstrapping in `comparison_engine/bootstrap.py`
4. Implement purged/embargoed time-series splitters in `validation_engine/splitter.py`

**Status**: NEVER COMPLETED. Sprint 3.9D work bypassed these critical fixes.

### ADR-024 Section 14: Sprint Breakdown

**Sprint 3.5**: Research Reports & Automated Promotion Gatekeeping  
**Deliverables**:
- Automated markdown report compiler
- Model transition constraints (digital signatures, quality gates)
- Connect paper trading to registry lookups

**Status**: PARTIALLY COMPLETE (reporting exists, promotion logic exists, integration missing)

### Missing Pipeline Integration Sprint

**No existing sprint document** covers:
- Connecting `EvaluationEngine` → `BenchmarkResult`
- Connecting `BenchmarkResult` → `PromotionEngine`
- Connecting `PromotionEngine` → Registry state updates
- End-to-end pipeline: Dataset → Replay → Evaluation → Benchmark → Promotion → Registry

---

## 7. Recommended Next Sprint

**Sprint 3.9D-14: Research Pipeline Integration & Evaluation Repair**

### Objective
Fix broken evaluation/replay engines and connect the research pipeline to the registry governance stack.

### Scope

**Phase 1: Evaluation Engine Repair (Critical)**
1. Fix hardcoded Sharpe/Drawdown in `experiment_engine/engine.py`
2. Fix algebraically broken Profit Factor in `evaluation_engine/engine.py`
3. Replace heuristic Sortino with actual downside deviation calculation
4. Verify metrics against known test cases

**Phase 2: Replay Engine Repair (Critical)**
1. Fix trade mapping bug in `replay_engine/replay.py` (use `trade['signal_id']` as key)
2. Fix API mismatches in `verify_replay_engine.py`
3. Verify replay determinism

**Phase 3: Pipeline Integration (High Priority)**
1. Create `EvaluationResult → BenchmarkResult` adapter
2. Wire `BenchmarkResult` as input to existing `PromotionEngine`
3. Create end-to-end integration test: evaluation → benchmark → promotion → proposal

**Phase 4: Deduplication (Medium Priority)**
1. Audit `promotion/` vs `promotion_engine/` for canonical models
2. Remove duplicate RegistryProposal definitions
3. Update imports across codebase

### Dependencies
- None (all work is internal to research layer)
- Requires fixing Sprint 3.5 audit failures before integration

### Expected Outputs
1. Fixed `EvaluationEngine` with real metrics
2. Fixed `ReplayEngine` with correct trade mapping
3. Adapter: `EvaluationResult → BenchmarkResult`
4. Integration test covering full pipeline
5. Architecture diagram showing connected flow

### Explicit Non-Goals
- ❌ DO NOT build new abstractions
- ❌ DO NOT modify production execution layer
- ❌ DO NOT touch database schemas
- ❌ DO NOT modify frontend
- ❌ DO NOT extend registry API with write endpoints

### Architecture Boundaries
- Research layer only (ADR-024 compliance)
- No database writes
- No execution layer coupling
- RegistryProposal remains the boundary into production (future work)

### Acceptance Criteria
1. ✅ All evaluation metrics computed from actual return series (no hardcoded 0.0)
2. ✅ Replay engine correctly maps trades via `signal_id`
3. ✅ `verification_evaluation_engine.py` passes
4. ✅ `verify_replay_engine.py` passes
5. ✅ Integration test: mock evaluation → benchmark → promotion succeeds
6. ✅ All existing 342 tests still pass
7. ✅ Zero ADR-024 violations introduced

---

## 8. ADR-024 Compliance

### Audit of Registry Governance Stack (Sprints 3.9D-5 through 3.9D-13)

**✅ PASS**: All 9 sprints maintain ADR-024 boundaries:

**Research Layer Purity**:
- ✅ No SQLite/SQLAlchemy/database imports (verified in tests)
- ✅ No execution layer imports (PortfolioService, ExecutionSimulator)
- ✅ No direct production exchange access
- ✅ Pure functional logic (deterministic, stateless)

**Immutability**:
- ✅ All domain objects are frozen dataclasses
- ✅ Collections are tuples (not lists)
- ✅ Deterministic JSON serialization (sorted keys)

**Unidirectional Dependencies**:
- ✅ Snapshot → Store → Lifecycle → Engine → Workflow → Ledger → Query → API
- ✅ No circular dependencies
- ✅ No upstream mutations

**Boundary Enforcement**:
- ✅ RegistryProposal is the output boundary
- ✅ No registry mutation within research layer
- ✅ API is read-only (GET endpoints only)

### Audit of Broken Components (Sprint 3.5)

**❌ FAIL**: Evaluation and Replay engines violate ADR-024 intent:

**Determinism Violations**:
- ❌ Hardcoded metrics prevent reproducible evaluation
- ❌ Broken profit factor calculation produces invalid scores

**Correctness Violations**:
- ❌ Trade mapping bug causes false divergence detection
- ❌ API mismatches prevent verification

**Recommendation**: Fix Sprint 3.5 audit failures before claiming ADR-024 compliance for full research pipeline.

---

## 9. Test Baseline

**Current Verified Research Test Count**: 342 passing tests

**Breakdown by Subsystem**:
- Benchmark: 5
- Promotion (old): 12
- Governance (old): 12
- Registry Snapshot: 17
- Registry Store: 22
- Model Lifecycle: 26
- Promotion Engine: 17
- Promotion Workflow: 18
- Registry Event Ledger: 18
- Registry Query: 21
- Registry API: 19
- (Other research tests): ~155

**Test Health**: ✅ All passing, no regressions

**Coverage Gaps**:
- ⚠️ No integration tests spanning evaluation → benchmark → promotion
- ⚠️ Evaluation engine tests exist but test broken implementation
- ⚠️ Replay engine tests exist but test broken implementation

---

## 10. CTO Decision

**NEEDS ARCHITECTURAL DECISION**

### Critical Issues Requiring Resolution

**1. Sprint 3.5 Audit Failures (BLOCKING)**

The Sprint 3.5 Full Audit (dated 2026-07-07) identified **FAIL** verdict with critical flaws:
- Broken evaluation metrics (hardcoded 0.0)
- Broken replay trade mapping
- Statistical violations in comparison engine
- Mathematical invalidity in profit factor calculation

**Decision Required**: Must these be fixed before continuing? Or are they superseded by the registry governance work?

**2. Pipeline Integration Strategy (BLOCKING)**

The registry governance stack (3.9D-5 through 3.9D-13) was built in isolation from the earlier research pipeline (Dataset → Replay → Evaluation → Reporting).

**Decision Required**:
- **Option A**: Repair evaluation/replay engines first, then integrate with registry governance
- **Option B**: Build new evaluation overlay that directly produces `BenchmarkResult`, deprecating old evaluation engine
- **Option C**: Declare registry governance complete and defer pipeline integration

**3. Duplicate Abstractions (MEDIUM PRIORITY)**

Multiple `RegistryProposal` definitions exist:
- `promotion/models.py` (3.9D-2)
- `governance/models.py` (3.9D-3)
- `promotion_engine/models.py` (3.9D-8)

**Decision Required**: Which is canonical? Should older implementations be deprecated?

### Recommended Decision Path

**Recommendation**: **Option A** - Fix evaluation/replay, then integrate

**Rationale**:
1. Sprint 3.5 audit identified scientifically invalid implementations
2. Building on broken foundations risks compounding errors
3. Integration requires working evaluation engine to produce benchmark inputs
4. Registry governance stack is solid but has no upstream data source

**Estimated Effort**:
- Evaluation repair: 2-3 days
- Replay repair: 1-2 days
- Integration adapters: 2-3 days
- Testing and verification: 2 days
- **Total**: ~7-10 days for Sprint 3.9D-14

### Alternatives

**Option B: New Evaluation Overlay**
- **Pros**: Clean slate, avoid repairing broken code
- **Cons**: Duplicates effort, leaves broken code in place, higher risk

**Option C: Defer Integration**
- **Pros**: Registry governance is complete and testable in isolation
- **Cons**: No end-to-end pipeline, evaluation remains broken, technical debt grows

---

## Conclusion

The registry governance stack built across Sprints 3.9D-5 through 3.9D-13 is **architecturally sound, well-tested, and ADR-024 compliant**. However, it exists as an **isolated subsystem** disconnected from the upstream research pipeline (Dataset → Replay → Evaluation).

The earlier research pipeline components (Evaluation Engine, Replay Engine) remain **broken** per the Sprint 3.5 Full Audit (FAIL verdict, dated 2026-07-07). Critical issues include hardcoded metrics, broken profit factor calculations, and trade mapping bugs.

**Before implementing Sprint 3.9D-14 or any new work**, the CTO must decide:
1. Whether to repair broken evaluation/replay engines or replace them
2. Whether pipeline integration is required or optional
3. Which promotion/governance abstractions are canonical

**Status**: NEEDS ARCHITECTURAL DECISION

---

**Prepared by**: CybxAI  
**Date**: 2026-08-13  
**Branch**: quant-research  
**Commit**: 6bd561d
