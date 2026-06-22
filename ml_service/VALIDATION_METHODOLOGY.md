# Signal Reconstruction Validation Methodology

## Purpose

Quantify the accuracy of legacy signal reconstruction by comparing estimated performance against actual post-migration signal outcomes.

---

## Validation Approach

### Phase 1: Post-Migration Data Collection

Once the signal persistence system is fully operational, collect actual performance data for new signals that include:

- Stored `entry_price`, `take_profit`, `stop_loss` at generation time
- Real exit prices and outcomes from `signal_outcomes` table
- Matched trades from `user_trade_history`

### Phase 2: Reconstruction Error Analysis

For signals generated after migration (with actual prices stored), run the reconstruction algorithm as if they were legacy signals and compare:

#### Entry Price Error

```sql
SELECT 
    AVG(ABS(reconstructed_entry_price - entry_price) / entry_price * 100) as avg_entry_error_pct,
    MAX(ABS(reconstructed_entry_price - entry_price) / entry_price * 100) as max_entry_error_pct,
    STDDEV(ABS(reconstructed_entry_price - entry_price) / entry_price * 100) as stddev_entry_error
FROM signal_reconstruction sr
JOIN signals s ON sr.signal_id = s.id
WHERE s.entry_price IS NOT NULL;
```

#### TP/SL Estimation Error

```sql
SELECT 
    AVG(ABS(reconstructed_take_profit - take_profit) / take_profit * 100) as avg_tp_error_pct,
    AVG(ABS(reconstructed_stop_loss - stop_loss) / stop_loss * 100) as avg_sl_error_pct
FROM signal_reconstruction sr
JOIN signals s ON sr.signal_id = s.id
WHERE s.entry_price IS NOT NULL;
```

#### Outcome Classification Accuracy

```sql
SELECT 
    sr.reconstructed_outcome,
    so.outcome as actual_outcome,
    COUNT(*) as count,
    COUNT(*) * 100.0 / SUM(COUNT(*)) OVER () as percentage
FROM signal_reconstruction sr
JOIN signals s ON sr.signal_id = s.id
JOIN signal_outcomes so ON s.id = so.signal_id
WHERE s.entry_price IS NOT NULL
GROUP BY sr.reconstructed_outcome, so.outcome
ORDER BY count DESC;
```

### Phase 3: Win Rate Adjustment

Calculate correction factors to adjust estimated win rates:

```
actual_win_rate = estimated_win_rate × correction_factor
```

Where correction factor is derived from:

```
correction_factor = actual_win_rate_post_migration / estimated_win_rate_post_migration
```

Apply symbol-specific and timeframe-specific correction factors when sufficient samples exist.

---

## Expected Error Ranges

Based on the reconstruction methodology, expected error ranges are:

| Metric | Expected Error Range | Impact |
|--------|---------------------|---------|
| Entry Price | 0.1% - 2% | Low - entries are from candle close |
| TP/SL Levels | 5% - 15% | Medium - depends on ATR calculation accuracy |
| Outcome Classification | 15% - 30% mismatch | High - timing and execution assumptions |
| Win Rate | ±5-10 percentage points | High - accumulates all above errors |

### Known Sources of Error

1. **Timing Mismatch**: Signal timestamp may fall mid-candle, but reconstruction uses candle close
2. **ATR Calculation**: Historical ATR may differ from signal generation ATR due to data availability
3. **TP/SL Assumptions**: Used fixed 2:1 multipliers vs potentially optimized multipliers
4. **Execution Modeling**: Assumes exact TP/SL hits, ignores slippage and partial fills
5. **Timeout Window**: 7-day timeout is arbitrary and may not reflect actual hold periods

---

## Validation Sample Size

Minimum sample requirements for statistically significant validation:

- **Overall**: 500+ post-migration signals with known outcomes
- **Per Symbol**: 100+ signals for symbol-specific corrections
- **Per Timeframe**: 200+ signals for timeframe-specific corrections
- **Per Confidence Bucket**: 100+ signals per bucket

---

## Validation Report Template

```markdown
# Signal Reconstruction Validation Report

## Data Collection Period
- Start Date: [DATE]
- End Date: [DATE]
- Total Post-Migration Signals: [N]
- Signals with Outcomes: [N]

## Entry Price Accuracy
- Mean Absolute Error: X.X%
- Median Absolute Error: X.X%
- 95th Percentile Error: X.X%

## TP/SL Level Accuracy
- TP Mean Error: X.X%
- SL Mean Error: X.X%

## Outcome Classification Accuracy
| Estimated | Actual Win | Actual Loss | Actual Timeout | Total |
|-----------|------------|-------------|----------------|-------|
| Win       | X          | X           | X              | X     |
| Loss      | X          | X           | X              | X     |
| Timeout   | X          | X           | X              | X     |

**Overall Accuracy**: X.X%

## Win Rate Comparison
- Estimated Win Rate (Legacy): 20.4%
- Actual Win Rate (Post-Migration): X.X%
- **Correction Factor**: X.XX
- **Adjusted Legacy Win Rate**: X.X%

## Recommendations
[Based on validation results, recommend:]
- Whether to apply correction factors to legacy estimates
- Confidence intervals for reconstructed metrics
- Symbols/timeframes where reconstruction is reliable vs unreliable
```

---

## Continuous Validation

As more post-migration data accumulates:

1. **Monthly**: Re-run validation queries and update correction factors
2. **Quarterly**: Generate updated validation report
3. **Annual**: Archive estimated report and replace with actual performance data

---

## Implementation Timeline

1. **Week 1-2**: Collect 200+ post-migration signals with outcomes
2. **Week 3**: Run validation analysis and calculate initial correction factors
3. **Week 4**: Generate first validation report
4. **Month 2-3**: Accumulate 500+ signals for stable correction factors
5. **Month 4**: Generate final validation report with confidence intervals

---

**Last Updated**: 2026-06-20  
**Status**: Awaiting post-migration data collection
