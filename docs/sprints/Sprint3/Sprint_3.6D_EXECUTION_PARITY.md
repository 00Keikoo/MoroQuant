# Sprint 3.6D: Execution Parity Layer

**Status:** In Progress  
**Date:** 2026-07-08  
**Objective:** Ensure Replay Engine reproduces production execution constraints, not just trading decisions.

## Motivation

Current replay engine (Sprint 3.6A-C) reconstructs trading decisions based on probabilities but does not verify whether those decisions would have been executed in production. Production execution involves multiple filters and constraints that can block or modify trades.

**Problem:** A signal might reconstruct to LONG, but production might have blocked it due to:
- Insufficient confidence
- Negative regime statistics
- Low probability edge
- Post-SL cooldown
- Max position limits
- Existing position on symbol

Without execution parity, replay results are scientifically incomplete.

## Production Execution Logic Audit

### 1. Entry Point: `paper_broker.py::open_paper_position()`

**Location:** `ml_service/trading/paper_broker.py:196-404`

#### Execution Filters (Applied in Order)

1. **Mode Gate** (line 212-215)
   - Requires `trading_mode == "PAPER"`
   - Blocks: All trades if mode is not PAPER

2. **Direction Filter** (line 217-223)
   - Skips `NEUTRAL` signals
   - Blocks: Unknown directions

3. **Confidence Filter** (line 231-242)
   - Parameter: `MIN_EXECUTION_CONFIDENCE = 55`
   - Requires: `signal.confidence >= 55`
   - Blocks: Low-confidence signals

4. **Regime Execution Policy** (line 245-264)
   - Module: `regime_execution_policy.py::evaluate_regime_execution_policy()`
   - Statistical framework: Bootstrap confidence intervals on R-multiple returns
   - Decision rules:
     - **Structural Block:** Manual regime blacklist
     - **Insufficient Data:** N < 100 trades → PERMIT (default allow)
     - **Negative UCI:** UCI_r < 0 → BLOCK (regime is losing with confidence)
     - **Negative LCI:** LCI_r < 0 → RESTRICT (reduce sizing multiplier)
     - **Positive LCI:** LCI_r >= 0 → PERMIT (regime is profitable)
   - Output: `execution_permitted`, `sizing_multiplier`, `block_reason`

5. **Edge Filter** (line 267-282)
   - Parameter: `MIN_PROBABILITY_EDGE = 0.20`
   - Calculation: `edge = max(prob_long, prob_short, prob_neutral) - second_highest`
   - Requires: `edge >= 0.20`
   - Blocks: Signals with low conviction

6. **Price Resolution** (line 284-289)
   - Fetch entry price from signal or market
   - Blocks: If no valid price available

7. **Cooldown After Stop Loss** (line 296-312)
   - Parameter: `COOLDOWN_AFTER_SL_HOURS = 6`
   - Check: Last SL hit on same symbol+direction within 6 hours
   - Blocks: Prevents revenge trading

8. **Max Open Positions** (line 315-323)
   - Parameter: `MAX_OPEN_POSITIONS = None` (currently disabled)
   - Blocks: When at capacity

9. **One Position Per Symbol** (line 326-332)
   - Check: Existing open position on symbol
   - Blocks: Duplicate symbol exposure

10. **Position Sizing** (line 335-343)
    - Base: `equity * RISK_PER_TRADE_PCT` (1%)
    - Adjusted: `base_size * regime_sizing_multiplier`
    - Blocks: If computed qty <= 0

### 2. Regime Execution Policy: `regime_execution_policy.py`

**Location:** `ml_service/trading/regime_execution_policy.py:171-267`

#### Statistical Framework

**Input:**
- `regime`: Market regime classification
- Historical R-multiple returns for regime

**Process:**
1. Load regime trade history (line 62-100)
2. Check structural block (manual blacklist, line 46-59)
3. Check sample size >= 100 (line 208-219)
4. Compute bootstrap CI (line 136-168)
5. Apply Newey-West autocorrelation adjustment (line 103-133)
6. Decision logic (line 243-263)

**Output:** `ExecutionDecision`
- `execution_permitted`: bool
- `sizing_multiplier`: float [0.0, 1.0]
- `statistical_metadata`: dict
- `block_reason`: str (if blocked)

#### Rejection Reasons

- `structural_block`: Regime manually blacklisted
- `uci_negative`: UCI < 0 (regime is losing with statistical confidence)
- `insufficient_data`: N < 100 (not enough data to evaluate)

### 3. Risk Parameters

**Location:** `ml_service/trading/paper_broker.py:35-54`

```python
STARTING_BALANCE = 10000.0
MAX_OPEN_POSITIONS = None  # Disabled
RISK_PER_TRADE_PCT = 0.01  # 1%
POSITION_EXPIRY_HOURS = 24 * 7  # 7 days
MIN_EXECUTION_CONFIDENCE = 55
MIN_PROBABILITY_EDGE = 0.20
COOLDOWN_AFTER_SL_HOURS = 6
EXECUTION_POLICY = "TRAILING"
BREAK_EVEN_AT_R = 1.0
TRAIL_AT_R = 2.0
TRAIL_DISTANCE_R = 0.5
```

## Execution Context Requirements

To reproduce production execution decisions, replay needs:

### Account State
- `balance`: Current cash balance
- `equity`: Balance + unrealized PnL
- `unrealized_pnl`: Sum of open position P&L

### Position State
- `open_positions`: List of open positions (symbol, direction, status)
- `recent_sl_hits`: Recent SL events per symbol+direction for cooldown

### Regime State
- `regime_statistics`: Per-regime execution policy state
  - `sample_size`: Number of historical trades
  - `mean_return`: Mean R-multiple
  - `lci`, `uci`: Bootstrap confidence intervals
  - `status`: "permitted" | "restricted" | "blocked" | "insufficient_data"

### Risk State
- `max_open_positions`: Global position limit
- `risk_per_trade_pct`: Position sizing parameter
- `min_execution_confidence`: Confidence threshold
- `min_probability_edge`: Edge threshold
- `cooldown_after_sl_hours`: Cooldown parameter

### Execution Constraints
- `execution_policy`: Current policy (TRAILING, BREAK_EVEN, FIXED_SL)
- `structural_blocks`: List of manually blocked regimes

## Implementation Plan

### Step 1: Extend Snapshot Capture

**File:** `ml_service/research/snapshot_engine/capture.py`

Add to `capture_snapshot()`:

```python
account_state = _capture_account_state(conn)
position_state = _capture_position_state(conn)
regime_statistics = _capture_regime_statistics(conn)
execution_constraints = _capture_execution_constraints()
```

New capture functions:
- `_capture_account_state()`: Query `paper_account` table
- `_capture_position_state()`: Query open positions + recent SL hits
- `_capture_regime_statistics()`: Call `get_regime_statistics()` for all regimes
- `_capture_execution_constraints()`: Return constants from `paper_broker.py`

### Step 2: Create Execution Parity Checker

**New File:** `ml_service/research/execution_parity/checker.py`

Purpose: Apply production execution filters to replay decisions.

```python
class ExecutionParityChecker:
    def __init__(self, snapshot: Snapshot):
        self.account_state = snapshot.account_state
        self.position_state = snapshot.position_state
        self.regime_statistics = snapshot.regime_statistics
        self.constraints = snapshot.execution_constraints
    
    def check_execution(self, signal: Dict, decision: str) -> ExecutionParityResult:
        """Apply all production filters to a signal+decision."""
        if decision == "HOLD":
            return ExecutionParityResult(
                execution_allowed=False,
                block_reason="decision_is_hold",
                passed_filters=[]
            )
        
        # Apply filters in production order
        checks = [
            self._check_confidence(signal),
            self._check_regime_policy(signal),
            self._check_edge(signal),
            self._check_cooldown(signal),
            self._check_max_positions(),
            self._check_symbol_conflict(signal),
            self._check_position_sizing(signal)
        ]
        
        for check in checks:
            if not check.passed:
                return ExecutionParityResult(
                    execution_allowed=False,
                    block_reason=check.reason,
                    passed_filters=[c.name for c in checks if c.passed]
                )
        
        return ExecutionParityResult(
            execution_allowed=True,
            block_reason=None,
            passed_filters=[c.name for c in checks]
        )
```

### Step 3: Extend Replay Output

**File:** `ml_service/research/replay_engine/replay.py`

Modify `run_replay()` to include execution parity:

```python
def run_replay(snapshot: Snapshot, ...) -> ReplayResult:
    checker = ExecutionParityChecker(snapshot)
    
    for signal in snapshot.signals:
        # Existing decision logic
        decision_result = decision_engine.decide(context)
        reconstructed_decision = decision_result.action
        
        # NEW: Check execution parity
        execution_result = checker.check_execution(signal, reconstructed_decision)
        
        decisions.append({
            # Existing fields...
            'reconstructed': reconstructed_decision,
            'actual': actual_decision,
            'matched': matched,
            
            # NEW: Execution parity fields
            'execution_allowed': execution_result.execution_allowed,
            'execution_block_reason': execution_result.block_reason,
            'risk_check_result': execution_result.risk_passed,
            'regime_check_result': execution_result.regime_passed,
            'position_size_match': execution_result.size_match
        })
```

### Step 4: Add Verification

**New File:** `ml_service/research/execution_parity/verify.py`

```python
def verify_execution_parity(snapshot: Snapshot, result: ReplayResult) -> ParityReport:
    """Verify replay execution matches production execution."""
    
    decision_matches = 0
    execution_matches = 0
    
    for decision in result.decisions:
        if decision['matched']:
            decision_matches += 1
        
        # Check execution parity
        was_executed = decision['executed']
        replay_allows = decision['execution_allowed']
        
        if was_executed == replay_allows:
            execution_matches += 1
    
    return ParityReport(
        decision_parity_rate=decision_matches / len(result.decisions),
        execution_parity_rate=execution_matches / len(result.decisions),
        divergence_analysis=[...]
    )
```

## Testing Strategy

### Unit Tests

1. **Test execution filter logic** (`test_execution_parity_checker.py`)
   - Each filter in isolation
   - Filter combinations
   - Edge cases (None values, zero confidence, etc.)

2. **Test snapshot capture** (`test_snapshot_execution_context.py`)
   - Account state capture
   - Position state capture
   - Regime statistics capture
   - Execution constraints capture

### Integration Tests

1. **Test full replay with execution parity** (`test_replay_execution_parity.py`)
   - Create snapshot with known state
   - Run replay
   - Verify execution decisions match production

2. **Test determinism** (`test_execution_parity_determinism.py`)
   - Same snapshot → same execution results

### Verification Script

**File:** `ml_service/verify_execution_parity.py`

```python
"""Verify execution parity implementation."""

snapshot = create_snapshot()
result = run_replay(snapshot)
parity_report = verify_execution_parity(snapshot, result)

print(f"Decision Parity: {parity_report.decision_parity_rate:.2%}")
print(f"Execution Parity: {parity_report.execution_parity_rate:.2%}")
```

## Success Criteria

1. **Snapshot includes execution context**
   - Account state (balance, equity)
   - Position state (open positions, SL cooldowns)
   - Regime statistics (all regimes)
   - Execution constraints (all parameters)

2. **Replay output includes execution results**
   - `execution_allowed`: bool
   - `execution_block_reason`: str
   - `risk_check_result`: dict
   - `regime_check_result`: dict
   - `position_size_match`: bool

3. **Execution parity verification passes**
   - Same snapshot → same execution decisions
   - Execution parity rate >= 95%
   - All production filters implemented

4. **No new dependencies**
   - Reuse existing production logic
   - No database queries in replay
   - Snapshot-only execution

## Limitations

1. **Snapshot-only**: Replay cannot query database
2. **Frozen state**: Execution context is point-in-time
3. **No price feeds**: Uses snapshot prices, not live market
4. **No side effects**: Replay does not modify account/positions

## Next Steps

After Sprint 3.6D:
- Sprint 3.7: Execution outcome parity (TP/SL hit prediction)
- Sprint 3.8: MAE/MFE parity (excursion tracking)
- Sprint 3.9: Full lifecycle replay (open → close)
