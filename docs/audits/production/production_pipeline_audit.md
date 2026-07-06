# Production Signal Pipeline Audit

**Date:** 2026-06-16  
**Status:** AUDIT COMPLETED  
**Auditor:** MoroQuant

---

## Executive Summary

**Current State:** Production dashboard menggunakan Fixed Horizon labeling tanpa confidence filtering.

**Research Winner:** Triple Barrier TP=3.0 SL=1.5 dengan confidence filter ≥60% menghasilkan Sharpe 10.33 pada BTCUSDT 1h.

**Gap:** Pipeline production belum menggunakan konfigurasi research winner.

**Risk Level:** MEDIUM - Model production mungkin underperform dibanding research results.

---

## 1. Current Production Pipeline Architecture

### 1.1 Signal Generation Flow

```
User Request (Dashboard)
    ↓
api/routes.py:get_signal() [Line 37-93]
    ↓
models/predictor.py:generate_signal() [Line 99-278]
    ↓
    ├─ load_latest_model() [Line 23-70]
    │   └─ Load model dari storage/models/*.pkl
    │
    ├─ prepare_features() [Line 155]
    │   └─ trainer.py feature engineering
    │
    ├─ Model Prediction [Line 166-178]
    │   ├─ Ensemble (XGB + LGB) atau single model
    │   └─ Raw probabilities
    │
    ├─ Calibration (Optional) [Line 180-188]
    │   ├─ Load calibration artifact jika ada
    │   └─ Apply calibrator ke raw probabilities
    │
    ├─ TP/SL Calculation [Line 204-219]
    │   ├─ Check optimized params (tp_sl_optimizer)
    │   └─ Fallback: TP=3.0, SL=1.5 (sudah correct!)
    │
    └─ Multi-Timeframe Confidence Adjustment [Line 252-266]
        ├─ 1h signal → check 4h signal
        ├─ If agree: confidence * 1.15
        └─ If conflict: confidence * 0.80
```

### 1.2 Model Training Flow

```
cli.py train --symbol BTCUSDT --timeframe 1h
    ↓
cli/commands.py:train() [Line 94+]
    ↓
models/trainer.py:train_model()
    ↓
Read config.yaml
    └─ labeling_method: "fixed_horizon" ← CURRENT
    └─ tp_atr_mult: 3.0
    └─ sl_atr_mult: 1.5
    ↓
create_target_variable() [Line 24-59]
    └─ Fixed horizon labeling
    └─ Threshold-based: ±0.5% returns
    ↓
walk_forward_validation()
    ↓
train_final_model()
    ↓
Save to storage/models/{symbol}_{timeframe}_{model_type}_{timestamp}.pkl
```

---

## 2. Audit Findings

### 2.1 Configuration Analysis

**File:** `ml_service/config.yaml:64`

```yaml
labeling_method: "fixed_horizon"  # ❌ NOT using research winner
tp_atr_mult: 3.0  # ✅ Correct
sl_atr_mult: 1.5  # ✅ Correct
```

**Issue:** Config still uses fixed_horizon, not triple_barrier.

**Impact:** All models trained after June 10, 2026 use fixed horizon labeling.

---

### 2.2 Trained Models Analysis

**Latest Model:** `BTCUSDT_1h_xgboost_20260616_014211.pkl` (trained 16 Jun 2026 01:42)

**Training Method:** Fixed Horizon (based on config.yaml at training time)

**Evidence:**
- Model trained before research comparison completed (June 16, 12:54)
- Config still shows fixed_horizon
- No triple_barrier models in storage/models/

**Verification Needed:**
```bash
# Check model metadata
python -c "
import pickle
with open('ml_service/storage/models/BTCUSDT_1h_xgboost_20260616_014211.pkl', 'rb') as f:
    model = pickle.load(f)
    print('Training metadata:', model.get('metadata', {}))
"
```

---

### 2.3 Prediction Pipeline Analysis

**File:** `ml_service/models/predictor.py`

#### ✅ GOOD: TP/SL Already Using Research Values

```python
# Line 212-215
tp_multiplier = 3.0  # ✅ Correct
sl_multiplier = 1.5  # ✅ Correct
```

#### ❌ MISSING: Confidence Filtering

```python
# Line 190-195
prediction = int(np.argmax(prediction_proba))
direction = direction_map[prediction]
confidence = int(prediction_proba[prediction] * 100)
```

**Issue:** No confidence threshold applied. Signal returned regardless of confidence level.

**Expected:**
```python
if confidence < 60:
    direction = 'neutral'  # Filter low confidence
```

---

#### ❌ MISSING: Labeling Method Metadata

```python
# Line 229-250: Signal response
signal = {
    'symbol': symbol,
    'direction': direction,
    'confidence': confidence,
    'model_type': metadata['model_type'],  # xgboost/lightgbm
    'calibration_method': calibration_method,
    # ❌ MISSING: 'labeling_method': 'fixed_horizon' or 'triple_barrier'
    # ❌ MISSING: 'trained_at': timestamp
    # ❌ MISSING: 'model_version': hash or version
}
```

---

#### ⚠️ CAUTION: Calibration Applied

```python
# Line 180-188
if cal_artifact:
    chosen = cal_artifact['chosen_method']
    cal = cal_artifact['calibrators'][chosen]
    prediction_proba = cal_mod.apply_calibrator(cal, raw_proba.reshape(1, -1))[0]
```

**Issue:** Based on calibration audit (docs/audits/ml/calibration_audit.md), applying calibration can cause distribution mismatch.

**Research Used:** Raw probabilities (no calibration).

**Risk:** Production using calibrated probabilities may have different behavior than research.

---

### 2.4 API Routes Analysis

**File:** `ml_service/api/routes.py`

#### ✅ GOOD: Fresh Price Fetching

```python
# Line 54-77
fresh_price = crypto_service.get_price(symbol)
signal['price'] = fresh_price
signal['price_live'] = True/False
```

#### ❌ MISSING: Confidence Filter Endpoint

No parameter for `confidence_threshold` in `/signals` endpoint.

**Expected:**
```python
@router.get("/signals")
async def get_signal(
    symbol: str,
    timeframe: str,
    confidence_threshold: float = 0.60  # ← Add this
):
```

---

## 3. Gap Analysis

| Component | Current | Research Winner | Status |
|-----------|---------|----------------|--------|
| Labeling Method | Fixed Horizon | Triple Barrier | ❌ GAP |
| TP Multiplier | 3.0 | 3.0 | ✅ OK |
| SL Multiplier | 1.5 | 1.5 | ✅ OK |
| Confidence Filter | None | ≥60% | ❌ GAP |
| Calibration | Applied | Raw probabilities | ⚠️ RISK |
| Model Metadata | Partial | Full | ❌ GAP |
| Diagnostics | None | Full | ❌ GAP |

---

## 4. Risk Assessment

### 4.1 Performance Risk

**Severity:** HIGH

**Issue:** Models trained with Fixed Horizon may underperform research winner by significant margin.

**Evidence:**
- Research shows Triple TP=3.0/SL=1.5 + 60% conf: Sharpe 10.33
- Fixed Horizon with 60% conf: Sharpe -2.87 (negative!)

**Mitigation:** Retrain all production models with triple_barrier labeling.

---

### 4.2 Calibration Mismatch Risk

**Severity:** MEDIUM

**Issue:** Production applies calibration, research uses raw probabilities.

**Impact:** Confidence distributions may differ, filtering behavior unpredictable.

**Mitigation:** Disable calibration or use fold-specific calibration.

---

### 4.3 No Confidence Filtering Risk

**Severity:** MEDIUM

**Issue:** Production serves all signals regardless of confidence.

**Impact:** User may trade on low-confidence (< 40%) signals with poor expected value.

**Mitigation:** Add configurable confidence threshold to API.

---

### 4.4 Model Version Tracking Risk

**Severity:** LOW

**Issue:** No clear metadata about which labeling method was used to train model.

**Impact:** Can't verify if model matches research configuration.

**Mitigation:** Add labeling_method to model metadata.

---

## 5. Migration Plan

### Phase 1: Configuration Update (5 min)

**Action:** Update config.yaml to use triple_barrier

```yaml
# ml_service/config.yaml:64
labeling_method: "triple_barrier"  # Change from fixed_horizon
```

**Risk:** Low - only affects future training

---

### Phase 2: Model Retraining (2-4 hours)

**Action:** Retrain models with triple_barrier

```bash
# Retrain critical symbols
python cli.py train --symbol BTCUSDT --timeframe 1h --retrain
python cli.py train --symbol ETHUSDT --timeframe 1h --retrain
python cli.py train --symbol BNBUSDT --timeframe 1h --retrain
```

**Duration:** ~30-40 minutes per symbol

**Verification:**
- Check model metadata contains labeling_method
- Verify prediction distributions match research

**Risk:** Medium - models may have different behavior

---

### Phase 3: Add Confidence Filtering (30-60 min)

**Action:** Add confidence threshold to predictor and API

**Files to modify:**
1. `ml_service/models/predictor.py`
2. `ml_service/api/routes.py`

**Risk:** Low - backwards compatible (default threshold = 0)

---

### Phase 4: Enhanced Metadata & Diagnostics (1-2 hours)

**Action:** Add model metadata and prediction diagnostics

**Features:**
- labeling_method in model metadata
- trained_at timestamp
- prediction distribution logging
- confidence distribution logging

**Risk:** Low - additive changes only

---

### Phase 5: Disable Calibration (15 min)

**Action:** Use raw probabilities instead of calibrated

**Rationale:** Research winner uses raw probabilities

**Risk:** Low - simplifies pipeline

---

### Phase 6: Testing & Validation (2-4 hours)

**Action:** Verify production matches research

**Tests:**
1. Generate signals for same timestamps as research
2. Compare prediction distributions
3. Verify confidence filtering works
4. Check TP/SL calculations

**Risk:** Low - validation only

---

### Phase 7: Deployment (30 min)

**Action:** Deploy to production via PM2

**Steps:**
1. Stop PM2 service
2. Update code
3. Restart PM2
4. Monitor logs for 1 hour

**Risk:** Medium - production downtime ~2 minutes

---

## 6. Implementation Priority

### Critical (Do First)
1. ✅ Update config.yaml to triple_barrier
2. ✅ Retrain BTCUSDT 1h model (highest volume)
3. ✅ Add confidence filtering to API

### High (Do Soon)
4. Add model metadata (labeling_method, trained_at)
5. Disable calibration in production
6. Retrain remaining models

### Medium (Can Wait)
7. Add prediction diagnostics
8. Add confidence distribution logging
9. Create model version endpoint

---

## 7. Rollback Plan

**If production performance degrades:**

1. **Immediate:** Revert config.yaml to fixed_horizon
2. **Load old models:** Rename old .pkl files to restore
3. **Restart API:** PM2 restart ml-service
4. **Investigate:** Check logs for prediction anomalies

**Rollback Time:** < 5 minutes

---

## 8. Success Criteria

**Deployment successful if:**

1. ✅ Models load without errors
2. ✅ Signals generate with confidence scores
3. ✅ Low confidence signals filtered to neutral
4. ✅ TP/SL calculations match research (3.0x / 1.5x)
5. ✅ No API errors in first 1 hour
6. ✅ Prediction distributions match research ranges

**Monitor for 24 hours:**
- API response times (< 500ms)
- Error rates (< 0.1%)
- Signal distribution (not all neutral)
- Confidence distribution (mean 0.6-0.7)

---

## 9. Monitoring Requirements

**Add to production monitoring:**

```python
# Log every signal generated
{
    "timestamp": "2026-06-16T14:35:00",
    "symbol": "BTCUSDT",
    "direction": "long",
    "confidence": 67,
    "filtered": false,  # Was it filtered by threshold?
    "labeling_method": "triple_barrier",
    "model_version": "20260616_143500"
}
```

**Alerts:**
- Mean confidence < 0.50 for 1 hour
- All signals neutral for 2 hours
- API errors > 5/hour
- Prediction distribution shifts > 20%

---

## 10. Next Steps

1. **Immediate:** Update config.yaml and retrain BTCUSDT 1h
2. **Today:** Implement confidence filtering in API
3. **This week:** Retrain all production models
4. **Next week:** Add comprehensive diagnostics

**Owner:** MoroQuant  
**Target Completion:** June 18, 2026
