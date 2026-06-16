# Calibration Audit Report

**Date:** 2026-06-16  
**Status:** COMPLETED  
**Recommendation:** Remove calibration from walk-forward predictions

---

## Background

The ML trading system trains models to predict directional moves (short/neutral/long) and applies probability calibration to improve confidence estimates. During development, we discovered that applying calibration to walk-forward predictions caused severe prediction collapse.

## Issue Discovered

**Symptom:** Triple Barrier methods (TP=2.5/1.5 and TP=3.0/1.5) produced identical backtest results with all predictions collapsing to class 0.

**Root Cause:** Calibrator distribution mismatch
- Calibrator was fitted on probabilities from one initial model (trained on rows 0:1070)
- Walk-forward predictions came from different models trained on varying windows (0:1427, 0:1477, etc.)
- Each walk-forward model had different probability distributions
- Applying a calibrator fitted on one model's distribution to another model's predictions caused severe distortion

**Evidence:**
```
Before fix (with calibration):
  Triple 2.5/1.5: {0: 300} - collapsed to class 0
  Triple 3.0/1.5: {0: 300} - collapsed to class 0

After fix (raw probabilities):
  Triple 2.5/1.5: {0: 79, 1: 150, 2: 71} - balanced distribution
  Triple 3.0/1.5: {0: 45, 1: 194, 2: 61} - proper distribution
```

## Calibration Approaches Evaluated

### Option 1: Fold-Specific Calibration (Per Walk-Forward Model)

**Concept:** Fit a new calibrator for each walk-forward fold using that fold's predictions.

**Pros:**
- Calibrator matches the specific model's probability distribution
- No distribution mismatch

**Cons:**
- Requires holdout data from each fold for calibration (reduces test coverage)
- Small calibration sets per fold (~10-20 samples) → unstable isotonic regression
- Violates temporal ordering if using future folds for calibration
- Adds significant computational cost (N calibrators for N folds)
- **Critical flaw:** Cannot be done in production without future data

**Verdict:** ❌ Not viable for production deployment

---

### Option 2: Global Calibrator with Pooled Validation

**Concept:** Current architecture - fit one calibrator on pooled validation predictions, apply to all walk-forward models.

**Pros:**
- Adequate sample size (250+ samples for isotonic regression)
- Simple implementation
- Leak-free three-way split (train → calibrate → test)

**Cons:**
- **Distribution mismatch:** Calibrator trained on one model, applied to different models
- Causes prediction collapse when probability distributions shift
- Not robust to different labeling methods (each produces different distributions)

**Verdict:** ❌ Fails in practice due to distribution mismatch

---

### Option 3: Remove Calibration Entirely (Current Implementation)

**Concept:** Use raw probabilities from each walk-forward model without calibration.

**Pros:**
- No distribution mismatch - each model's probabilities used directly
- Simpler architecture, fewer moving parts
- Models already produce reasonable confidence estimates (mean 0.64-0.67)
- Confidence filtering still works with raw probabilities
- Production-ready: no calibration artifacts needed

**Cons:**
- Raw probabilities may not be perfectly calibrated (ECE ~0.08-0.19)
- Loses potential benefit of calibration on individual model probabilities

**Current Performance (BTCUSDT 1h):**
```
Fixed Horizon:
  Prediction dist: {0:44, 1:42, 2:214}
  Confidence: mean=0.649, range=[0.35, 0.98]

Triple TP=3.0 SL=1.5:
  Prediction dist: {0:45, 1:194, 2:61}
  Confidence: mean=0.638, range=[0.34, 0.98]
```

**Backtest Results:**
- Triple TP=3.0 SL=1.5 + Conf ≥60%: Sharpe 10.33, Return 10.27%
- Confidence filtering works effectively with raw probabilities
- No prediction collapse, proper class distributions

**Verdict:** ✅ **RECOMMENDED** - Works reliably, production-ready

---

## Alternative: Per-Model Calibration in Production

**Concept:** Calibrate each production model individually during training, apply only to its own predictions.

**Implementation:**
1. Train model on historical data
2. Generate predictions on a temporally separate holdout set
3. Fit calibrator on those holdout predictions
4. Save model + calibrator as a pair
5. In production, apply that specific calibrator only to that specific model

**Pros:**
- No distribution mismatch (calibrator matched to its model)
- Production-viable (calibrator fitted during training)
- Proper temporal separation maintained

**Cons:**
- Walk-forward backtesting becomes complex (need to store N model-calibrator pairs)
- Each model needs sufficient holdout data for calibration
- More artifacts to manage (model.pkl + calibration.pkl per pair)
- Marginal benefit over raw probabilities

**Verdict:** ⚠️ Possible but complex - not worth the overhead given raw probabilities work well

---

## Recommendation

**Remove calibration from walk-forward predictions** (already implemented in `compare_backtest_methods.py:246-311`).

**Rationale:**
1. Raw probabilities produce reliable results (Sharpe 10.33 on BTCUSDT 1h)
2. No distribution mismatch issues
3. Simpler architecture, easier to maintain
4. Production-ready without additional artifacts
5. Confidence filtering works effectively with raw probabilities

**Current Implementation:**
```python
# compare_backtest_methods.py:285-287
probas_raw = model.predict_proba(X_test[valid_rows])
preds = np.argmax(probas_raw, axis=1)  # No calibration applied
```

**Trade-offs Accepted:**
- Raw probabilities may have ECE of 0.08-0.19 (vs 0.06-0.10 with calibration)
- This is acceptable given:
  - Confidence thresholds still work (60%, 70%)
  - No prediction collapse risk
  - Consistent across all labeling methods

---

## If Calibration Is Needed in Future

If ECE degradation becomes problematic, consider **per-model calibration during training**:

1. Modify `train_model()` to include calibration holdout
2. Fit calibrator on model's own holdout predictions
3. Save model + calibrator as atomic pair
4. Apply calibrator only to its paired model in production
5. Never apply calibrator across different models

**Do not:**
- Apply one model's calibrator to another model's predictions
- Use global calibrators across walk-forward folds
- Sacrifice prediction reliability for marginal ECE improvements

---

## Conclusion

**Status:** Calibration issue resolved by using raw probabilities.

**Action:** No changes needed. Current implementation is correct and production-ready.

**Monitoring:** Track confidence distributions in production to ensure they remain reasonable (mean 0.6-0.7, no extreme skew).
