# Sprint 3.6E - Execution Logic Duplication Analysis

**Generated:** 2026-07-08  
**Objective:** Analyze execution logic duplication between paper_broker and ExecutionParityChecker

---

## Executive Summary

**Status:** ✓ **No Critical Duplication Found**

The execution logic is appropriately separated:
- **Production (paper_broker):** Live execution with database persistence and side effects
- **Replay (ExecutionParityChecker):** Pure filter evaluation from snapshot without side effects

The filter logic is **intentionally duplicated** for replay fidelity but implemented differently due to different contexts (live vs snapshot).

---

## Comparison Analysis

### Shared Logic Patterns

| Filter | Production Code | Replay Code | Duplication Type |
|--------|----------------|-------------|------------------|
| Confidence Check | paper_broker.py:231-242 | checker.py:76-104 | **Semantic duplicate** (same logic, different data source) |
| Regime Policy | paper_broker.py:244-264 | checker.py:106-139 | **Partial duplicate** (production calls live function, replay uses snapshot) |
| Edge Filter | paper_broker.py:266-282 | checker.py:141-176 | **Semantic duplicate** (same logic) |
| Position Sizing | paper_broker.py:334-343 | checker.py:249-277 | **Semantic duplicate** (same calculation) |

### Why Duplication is Acceptable

**1. Different Execution Contexts**
```python
# Production: Live database queries
cooldown_row = conn.execute("SELECT ... FROM paper_positions WHERE ...").fetchone()

# Replay: Snapshot data
recent_sl_hits = self.position_state.get('recent_sl_hits', [])
```

**2. Different Side Effects**
```python
# Production: Logs, persists to DB, returns position dict
logger.info(f"Paper broker skipped {symbol}: ...")
return None  # or position dict

# Replay: Pure function, returns structured result
return FilterCheckResult(name="...", passed=False, reason="...")
```

**3. Different Error Handling**
```python
# Production: Graceful degradation, fallbacks
if confidence is not None:
    try:
        conf_val = int(confidence)
    except (ValueError, TypeError):
        pass  # Continue execution

# Replay: Structured error capture
return FilterCheckResult(name="...", passed=True, metadata={'error': ...})
```

---

## Should We Extract Shared Logic?

### Option A: Extract to Shared Module (NOT RECOMMENDED)

```python
# ml_service/trading/execution_filters.py
def check_confidence(confidence: Optional[int], min_conf: int) -> bool:
    """Shared confidence check logic."""
    if confidence is None:
        return True
    try:
        return int(confidence) >= min_conf
    except (ValueError, TypeError):
        return True
```

**Problems:**
1. **Loss of context:** Production needs logging, replay needs structured results
2. **Coupling:** Changes for production affect replay and vice versa
3. **Abstraction cost:** Adding parameters to handle both contexts makes code harder to read
4. **Testing complexity:** Need to test shared logic in both contexts

### Option B: Keep Separate (RECOMMENDED) ✓

**Benefits:**
1. **Clarity:** Each implementation optimized for its context
2. **Independence:** Production and replay can evolve separately
3. **Simplicity:** No abstraction overhead
4. **Testability:** Test each in isolation

**Trade-offs:**
- Must manually keep filter logic aligned
- Risk of drift if one is updated without the other

**Mitigation:**
- Filter Parity Audit (already done)
- Integration tests comparing production vs replay
- Documentation linking the two implementations

---

## Regime Execution Policy: Proper Reuse

### Current Architecture (CORRECT) ✓

```python
# Production
from ml_service.trading.regime_execution_policy import evaluate_regime_execution_policy
decision = evaluate_regime_execution_policy(regime, signal_id=None, confidence=confidence)

# Replay (via snapshot)
regime_stats = self.regime_statistics.get(regime)
status = regime_stats.get('status')
if status == 'blocked':
    # Apply block logic
```

**Observation:** 
- Production calls live function (queries database)
- Replay uses pre-computed statistics from snapshot
- This is **correct design** for snapshot purity

**No extraction needed:** The regime policy function is already shared at the right level (production uses it, snapshot captures its output, replay consumes snapshot).

---

## Execution Logic Single Source of Truth

### Decision Engine ✓ Already Unified

```python
# ml_service/research/decision_truth/decision_engine.py
class DecisionEngine:
    def decide(self, context: DecisionContext) -> DecisionResult:
        """Single source of truth for LONG/SHORT/HOLD decisions."""
        # Argmax logic
        probs = [prob_short, prob_neutral, prob_long]
        prediction = int(max(range(len(probs)), key=lambda i: probs[i]))
        direction_map = {0: 'SHORT', 1: 'HOLD', 2: 'LONG'}
        return direction_map[prediction]
```

**Status:** ✓ Already a single source of truth
- Used by replay engine
- Production uses equivalent logic in predictor.py (ML model output)
- No duplication here

### Execution Filters: Intentionally Separate

**Rationale:**
- Production: Imperative, side-effect-heavy, database-coupled
- Replay: Pure, snapshot-based, structured output

**Verdict:** Keep separate, maintain parity through audits

---

## Recommendations

### Do NOT Extract Shared Logic

**Reasoning:**
1. Context differences are fundamental (live vs snapshot)
2. Side effects differ (logging/persistence vs pure functions)
3. Abstraction cost exceeds duplication cost
4. Current separation is clean and maintainable

### DO Maintain Parity Through Process

**1. Document Linkage**

Add to ExecutionParityChecker docstring:
```python
"""Applies production execution filters to replay decisions.

Reproduces the filter pipeline from paper_broker.py::open_paper_position()
without database queries or side effects.

Filter implementations must stay aligned with production:
- Confidence filter: paper_broker.py:231-242
- Regime policy: paper_broker.py:244-264
- Edge filter: paper_broker.py:266-282
- Cooldown: paper_broker.py:295-312
- Max positions: paper_broker.py:314-323
- Symbol conflict: paper_broker.py:325-332
- Position sizing: paper_broker.py:334-343

See Sprint_3.6E_Filter_Parity_Audit.md for alignment verification.
"""
```

**2. Add Integration Test**

```python
def test_filter_logic_parity():
    """Verify replay filters match production behavior."""
    # Create signal with known properties
    signal = {
        'symbol': 'BTCUSDT',
        'confidence': 60,
        'prob_long': 0.7,
        'prob_short': 0.2,
        'prob_neutral': 0.1
    }
    
    # Test production
    production_result = open_paper_position(signal)
    
    # Test replay
    snapshot = create_snapshot()
    checker = ExecutionParityChecker(snapshot)
    replay_result = checker.check_execution(signal, 'LONG')
    
    # Compare results
    assert (production_result is not None) == replay_result.execution_allowed
```

**3. Regular Audits**

- Run Filter Parity Audit after any paper_broker changes
- Update ExecutionParityChecker when production filters change
- Document changes in both locations

---

## Conclusion

**Duplication Status:** ✓ ACCEPTABLE

The execution logic duplication is:
- **Intentional:** Replay must mirror production filters
- **Appropriate:** Different contexts require different implementations
- **Maintainable:** Documented and tested

**Action Items:**
- ✗ Do NOT extract shared execution filter module
- ✓ Keep implementations separate
- ✓ Maintain parity through audits and integration tests
- ✓ Add cross-reference documentation

**Scientific Impact:** None. The replay fidelity depends on filter **behavior** matching, not code sharing. As long as audits verify parity, the duplication is acceptable.
