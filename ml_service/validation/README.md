# Execution Validation Suite

Internal validation framework ensuring every execution metric recorded by MoroQuant is mathematically correct and internally consistent before use in quantitative research.

## Purpose

Execution metrics form the foundation of future research. Research quality depends entirely on data quality. This validation suite fails fast whenever execution instrumentation becomes inconsistent.

## Architecture

```
ml_service/validation/
├── __init__.py              # Package exports
├── __main__.py              # CLI entry point
├── execution_rules.py       # 12 validation rules
├── execution_validator.py   # Validation engine
└── execution_report.py      # Report formatting
```

## Validation Rules

### Rule 1: MAE Non-Positive
- **Invariant**: `MAE <= 0`
- **Rationale**: Maximum Adverse Excursion must be non-positive (drawdown)

### Rule 2: MFE Non-Negative
- **Invariant**: `MFE >= 0`
- **Rationale**: Maximum Favorable Excursion must be non-negative (profit peak)

### Rule 3: MAE Timestamp Exists
- **Invariant**: If `MAE != 0`, then `mae_timestamp` must exist
- **Severity**: WARNING

### Rule 4: MFE Timestamp Exists
- **Invariant**: If `MFE != 0`, then `mfe_timestamp` must exist
- **Severity**: WARNING

### Rule 5: Opened Before Closed
- **Invariant**: `opened_at < closed_at`
- **Rationale**: Position must be opened before it can be closed

### Rule 6: Hold Time Positive
- **Invariant**: `closed_at - opened_at > 0`
- **Rationale**: Position must have positive hold duration

### Rule 7: Profit Capture Ratio Bounds
- **Invariant**: `0 <= PCR <= 1`
- **Special Case**: If `MFE == 0`, then `PCR` must be `NULL` or `0` (no division by zero)
- **Rationale**: Cannot capture more than 100% of available profit

### Rule 8: Trailing Consistency
- **Invariant**: If `trailing_stop_activated == 1`, then `sl_move_count >= 1`
- **Rationale**: Activated trailing stop must have moved stop loss at least once

### Rule 9: Break-Even Consistency
- **Invariant**: If `break_even_triggered == 1`, then `sl_move_count >= 1`
- **Severity**: WARNING
- **Rationale**: Break-even trigger implies stop loss modification

### Rule 10: Execution Classification Valid
- **Invariant**: Classification must be one of:
  - `MODEL_CORRECT_EXECUTION_CORRECT`
  - `MODEL_CORRECT_EXECUTION_WEAK`
  - `MODEL_WEAK_EXECUTION_CORRECT`
  - `MODEL_WEAK_EXECUTION_WEAK`
  - `UNKNOWN`

### Rule 11: Exit Reason Valid
- **Invariant**: Exit reason must be one of: `TP_HIT`, `SL_HIT`, `EXPIRED`, `MANUAL_CLOSE`

### Rule 12: No Impossible Values
- **Confidence**: `0 <= confidence <= 100`, no NaN/inf
- **Probabilities**: Each probability finite, sum ≈ 1.0
- **Realized PnL**: No NaN/inf

## Usage

### Validate All Positions

```bash
python -m ml_service.validation
```

### Verbose Mode

```bash
python -m ml_service.validation --verbose
```

### Fail-Fast Mode

Stop on first ERROR-level failure:

```bash
python -m ml_service.validation --fail-fast
```

### JSON Output

```bash
python -m ml_service.validation --json
```

### Validate Single Position

```bash
python -m ml_service.validation --position-id 123
```

### Combine Options

```bash
python -m ml_service.validation --verbose --fail-fast --json > report.json
```

## Expected Output

### Console Format

```
================================================================================
EXECUTION VALIDATION REPORT
================================================================================
Passed:       47
Failed:       3
Warnings:     2
Success Rate: 94.00%
================================================================================

FAILURES:
--------------------------------------------------------------------------------

ERRORS (3):

  Position ID: 42
  Rule:        MAE_NON_POSITIVE
  Expected:    MAE <= 0
  Actual:      MAE = 0.05

  Position ID: 51
  Rule:        PCR_OUT_OF_BOUNDS
  Expected:    0 <= PCR <= 1
  Actual:      PCR = 1.5

  Position ID: 67
  Rule:        TRAILING_INCONSISTENCY
  Expected:    sl_move_count >= 1 when trailing_stop_activated = 1
  Actual:      sl_move_count = 0

WARNINGS (2):

  Position ID: 89
  Rule:        MAE_TIMESTAMP_MISSING
  Expected:    mae_timestamp exists when MAE changed
  Actual:      mae_timestamp is NULL

  Position ID: 91
  Rule:        PROBABILITY_SUM_INVALID
  Expected:    sum(probabilities) ≈ 1.0
  Actual:      sum = 1.15

================================================================================
```

### JSON Format

```json
{
  "passed": 47,
  "failed": 3,
  "warnings": 2,
  "success_rate": 94.00,
  "failures": [
    {
      "position_id": 42,
      "rule_violated": "MAE_NON_POSITIVE",
      "expected": "MAE <= 0",
      "actual": "MAE = 0.05",
      "severity": "ERROR"
    }
  ]
}
```

## Programmatic Usage

```python
from ml_service.validation import validate_all_positions, validate_position

# Validate all positions
report = validate_all_positions(verbose=True, fail_fast=False)
print(f"Success rate: {report.success_rate:.2f}%")

# Validate single position
position = {
    "id": 1,
    "mae": -0.05,
    "mfe": 0.10,
    "profit_capture_ratio": 0.8,
    # ... other fields
}
failures = validate_position(position)
if not failures:
    print("Position passed all validation rules")
```

## Integration Points

### Pre-Analytics Validation

Run validation before computing analytics to ensure data quality:

```python
from ml_service.validation import validate_all_positions
from ml_service.services.paper_analytics_service import compute_execution_analytics

# Validate first
report = validate_all_positions()
if report.failed > 0:
    raise ValueError(f"Validation failed: {report.failed} errors detected")

# Safe to compute analytics
analytics = compute_execution_analytics()
```

### CI/CD Integration

Add to CI pipeline to catch data quality issues early:

```bash
python -m ml_service.validation --fail-fast || exit 1
```

### Scheduled Validation

Run periodic validation checks:

```bash
# Daily validation report
0 9 * * * cd /path/to/ml_service && python -m validation --json > /var/log/validation_$(date +\%Y\%m\%d).json
```

## Extension Points

### Adding New Rules

1. Define rule function in `execution_rules.py`:

```python
def rule_your_new_rule(position: Dict[str, Any]) -> Optional[ValidationFailure]:
    """Rule N: Your invariant description."""
    if condition_violated:
        return ValidationFailure(
            position_id=position["id"],
            rule_violated="YOUR_RULE_NAME",
            expected="Expected condition",
            actual="Actual value",
            severity="ERROR",  # or "WARNING"
        )
    return None
```

2. Add to `ALL_RULES` list in `execution_rules.py`

3. Add unit tests in `tests/test_execution_validation.py`

### Custom Severity Levels

Modify `ValidationReport` in `execution_report.py` to add custom severity handling.

### Database Integration

Current implementation uses SQLite. To support other databases:

1. Modify `_get_connection()` in `execution_validator.py`
2. Adjust SQL queries if needed

## Testing

Run test suite:

```bash
python3 -m unittest tests.test_execution_validation -v
```

All rules have comprehensive unit tests covering:
- Valid cases
- Invalid cases
- Edge cases (NULL values, boundary conditions)
- Integration scenarios

## Performance

- Validation runs in O(n×r) where n = positions, r = rules (12)
- Typical performance: ~10,000 positions/second
- Memory footprint: Minimal (streaming validation)

## Future Enhancements

1. **Batch Validation**: Validate specific date ranges
2. **Alert Integration**: Send notifications on validation failures
3. **Trend Analysis**: Track validation failure rates over time
4. **Auto-Repair**: Suggest fixes for common validation errors
5. **Web Interface**: Dashboard for validation results
6. **Schema Validation**: Validate database schema compliance
