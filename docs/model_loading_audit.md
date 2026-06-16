# Production Model Loading Audit

**Date:** 2026-06-16 17:47 WIB  
**Auditor:** CybxAI  
**Status:** AUDIT COMPLETED

---

## Executive Summary

**Current Production Model:** `BTCUSDT_1h_xgboost_20260616_014211.pkl`

**Critical Finding:** Model metadata **MISSING** labeling_method, tp_atr_mult, sl_atr_mult fields.

**Training Method:** Unknown (metadata insufficient to determine)

**Risk Level:** HIGH - Cannot verify if production model matches research configuration.

---

## 1. Model Loading Path Trace

### API Request Flow

```
User/Dashboard
    ↓
GET /api/signals?symbol=BTCUSDT&timeframe=1h&confidence_threshold=0.60
    ↓
ml_service/api/routes.py:get_signal() [Line 37-42]
    ↓
ml_service/models/predictor.py:generate_signal() [Line 99+]
    ↓
ml_service/models/predictor.py:load_latest_model() [Line 23-70]
    ↓
    ├─ Check _model_cache [Line 35-37]
    ├─ models_dir = "ml_service/storage/models/" [Line 39]
    ├─ pattern = f"{symbol}_{timeframe}_*.pkl" [Line 45]
    ├─ model_files = glob(pattern) [Line 46]
    ├─ latest_model = max(model_files, key=st_mtime) [Line 52]  ← FILE SELECTION
    └─ pickle.load(latest_model) [Line 55-56]
    ↓
Model loaded into _model_cache
    ↓
generate_signal() uses model.predict_proba()
```

---

## 2. Model File Selection Logic

### Function: `load_latest_model()` (predictor.py:23-70)

**Selection Criteria:** File modification time (`st_mtime`)

```python
# Line 52
latest_model = max(model_files, key=lambda p: p.stat().st_mtime)
```

**Behavior:**
- ✅ Selects most recently modified .pkl file
- ✅ Caches model in memory (`_model_cache`)
- ✅ Loads calibration artifact if exists
- ❌ Does NOT validate model metadata
- ❌ Does NOT log which labeling method was used
- ❌ Does NOT verify model configuration matches research winner

---

## 3. Current Production Model

### File Information

**Path:** `ml_service/storage/models/BTCUSDT_1h_xgboost_20260616_014211.pkl`

**Modification Time:** 2026-06-16 01:42:11 (most recent)

**File Size:** 586 KB

**Calibration Artifact:** Yes (`BTCUSDT_1h_xgboost_20260616_014211_calibration.pkl`, 2.3 KB)

---

## 4. Model Metadata Analysis

### Available Metadata Fields

Based on inspection of model pickle structure:

```
metadata = {
    'model_type': 'xgboost',
    'feature_cols': [...],  # List of ~40 feature names
    'n_samples': <int>,
    'class_distribution': {0: X, 1: Y, 2: Z},
    'trained_at': '2026-06-16T01:42:11',
    'hyperparameters': {...}
}
```

### Missing Critical Fields

❌ **labeling_method** - NOT in metadata  
❌ **tp_atr_mult** - NOT in metadata  
❌ **sl_atr_mult** - NOT in metadata  
❌ **forward_periods** - NOT in metadata  
❌ **purge_size** - NOT in metadata  
❌ **confidence_threshold** - NOT in metadata (training-time value)

---

## 5. Training Method Verification

### Question: Was this model trained with Fixed Horizon or Triple Barrier?

**Answer:** **UNKNOWN** - Insufficient metadata to determine.

### Evidence Analysis

**Model trained:** 2026-06-16 01:42:11  
**Research comparison completed:** 2026-06-16 12:54:23  
**Config updated to triple_barrier:** 2026-06-16 17:47:00 (today)

**Timeline:**
```
01:42 - Model trained (what method?)
12:54 - Research identified triple_barrier as winner
17:47 - Config updated to triple_barrier (current)
```

**Conclusion:** Model was trained **before** research comparison completed and **before** config was updated to triple_barrier.

**Inference:** Model likely trained with **fixed_horizon** (config.yaml default at that time).

**Confidence:** Medium (based on timeline, not definitive metadata)

---

## 6. Metadata Validation Issues

### Problem 1: No Labeling Method Tracking

**Impact:** Cannot verify production model matches research configuration.

**Current Code:** trainer.py saves metadata but does NOT include labeling_method

```python
# trainer.py:461-468 (save_model metadata creation)
metadata = {
    'model_type': model_type,
    'feature_cols': feature_cols,
    'n_samples': len(X),
    'class_distribution': y.value_counts().to_dict(),
    'trained_at': datetime.now().isoformat(),
    'hyperparameters': params if custom_params else 'default',
}
# ❌ Missing: labeling_method, tp_atr_mult, sl_atr_mult
```

---

### Problem 2: No Metadata Validation at Load Time

**Current Code:** load_latest_model() loads without validation

```python
# predictor.py:55-56
with open(latest_model, 'rb') as f:
    model_package = pickle.load(f)
# ❌ No metadata validation
# ❌ No logging of labeling_method
# ❌ No warning if metadata incomplete
```

---

### Problem 3: Fallback Logic Missing

**Current Implementation:**

```python
# predictor.py (modified today)
labeling_method = metadata.get('labeling_method', 'unknown')
if labeling_method == 'unknown':
    config = get_config()
    labeling_method = config.model.labeling_method
```

**Issue:** Fallback reads current config (triple_barrier), not training-time config.

**Result:** API will report `labeling_method: "triple_barrier"` even if model was trained with fixed_horizon.

**Risk:** **Misleading metadata** - users will think model uses triple_barrier when it may not.

---

## 7. Model Selection Algorithm

### Current: Modification Time (st_mtime)

**Pros:**
- ✅ Simple
- ✅ Works for single-user sequential training
- ✅ No manual intervention needed

**Cons:**
- ❌ Can select wrong model if files copied/touched
- ❌ Doesn't consider model quality metrics
- ❌ Doesn't verify model configuration
- ❌ Ignores model versioning

**Alternatives:**

1. **Filename timestamp parsing** (current implicit method)
   ```python
   # Extract timestamp from: BTCUSDT_1h_xgboost_20260616_014211.pkl
   # Use timestamp in filename instead of st_mtime
   ```

2. **Model registry with metadata**
   ```python
   # models/registry.json
   {
     "BTCUSDT_1h": {
       "active": "BTCUSDT_1h_xgboost_20260616_014211.pkl",
       "labeling_method": "fixed_horizon",
       "sharpe_validation": 2.3,
       "trained_at": "2026-06-16T01:42:11"
     }
   }
   ```

3. **Explicit model versioning**
   ```python
   # BTCUSDT_1h_triple_barrier_v1.pkl
   # Parse labeling method from filename
   ```

---

## 8. Production vs Research Configuration Gap

### Research Winner Configuration

```
Labeling: Triple Barrier
TP: 3.0x ATR
SL: 1.5x ATR
Confidence: >= 60%
Sharpe: 10.33
```

### Current Production Model

```
Labeling: Unknown (likely fixed_horizon)
TP: Unknown (metadata missing)
SL: Unknown (metadata missing)
Confidence: Filter added today (60% default)
Sharpe: Unknown (not in metadata)
```

**Mismatch:** ❌ Production model likely NOT using research winner configuration.

---

## 9. Recommendations

### Immediate (Today)

1. **Add Metadata Validation to load_latest_model()**
   ```python
   def load_latest_model(symbol, timeframe):
       # ... existing code ...
       
       # Validate metadata
       required_fields = ['model_type', 'feature_cols', 'trained_at']
       missing = [f for f in required_fields if f not in metadata]
       if missing:
           logger.warning(f"Model metadata missing fields: {missing}")
       
       # Log critical info
       logger.info(f"Model labeling_method: {metadata.get('labeling_method', 'UNKNOWN')}")
       logger.info(f"Model trained_at: {metadata.get('trained_at', 'UNKNOWN')}")
   ```

2. **Fix Fallback Logic**
   ```python
   # Don't use current config as fallback - it's misleading
   labeling_method = metadata.get('labeling_method', 'unknown_fixed_horizon')
   ```

3. **Retrain BTCUSDT 1h with Triple Barrier**
   ```bash
   # After config.yaml updated to triple_barrier
   python cli.py train --symbol BTCUSDT --timeframe 1h --retrain
   ```

---

### Short-term (This Week)

4. **Update trainer.py to Save Complete Metadata**
   ```python
   # trainer.py:461-468 - Add missing fields
   metadata = {
       'model_type': model_type,
       'feature_cols': feature_cols,
       'n_samples': len(X),
       'class_distribution': y.value_counts().to_dict(),
       'trained_at': datetime.now().isoformat(),
       'hyperparameters': params if custom_params else 'default',
       # ✅ ADD THESE:
       'labeling_method': config.model.labeling_method,
       'tp_atr_mult': config.model.tp_atr_mult,
       'sl_atr_mult': config.model.sl_atr_mult,
       'forward_periods': forward_periods,
   }
   ```

5. **Add Model Metadata Endpoint**
   ```python
   @router.get("/model/info")
   async def get_model_info(symbol: str, timeframe: str):
       model_pkg = load_latest_model(symbol, timeframe)
       return {
           'model_path': model_pkg['model_path'],
           'metadata': model_pkg['metadata'],
           'calibration': model_pkg.get('calibration', {}).get('chosen_method'),
       }
   ```

---

### Medium-term (Next Sprint)

6. **Implement Model Registry**
   - Track active model per (symbol, timeframe)
   - Store validation metrics
   - Enable A/B testing
   - Support rollback

7. **Add Model Versioning**
   - Semantic versioning (v1.0.0, v1.1.0)
   - Include labeling method in filename
   - Automated model comparison before promotion

---

## 10. Verification Commands

### Check Current Model
```bash
ls -lht ml_service/storage/models/BTCUSDT_1h*.pkl | head -1
```

### Inspect Model Metadata
```bash
source ml_service/venv/bin/activate
python -c "
import pickle
with open('ml_service/storage/models/BTCUSDT_1h_xgboost_20260616_014211.pkl', 'rb') as f:
    m = pickle.load(f)
print('Labeling method:', m['metadata'].get('labeling_method', 'MISSING'))
print('Trained at:', m['metadata'].get('trained_at', 'MISSING'))
"
```

### Test API Response
```bash
curl -s "http://localhost:8000/api/signals?symbol=BTCUSDT&timeframe=1h" | \
  jq '.labeling_method, .trained_at, .model_type'
```

---

## 11. Risk Assessment

### Critical Risks

1. **Model Mismatch** (Severity: HIGH)
   - Production may use fixed_horizon instead of triple_barrier
   - Performance gap: Sharpe -2.87 (fixed) vs +10.33 (triple)
   - Mitigation: Retrain with triple_barrier immediately

2. **Misleading Metadata** (Severity: MEDIUM)
   - API reports labeling_method from config, not model
   - Users think they're using triple_barrier when model is fixed_horizon
   - Mitigation: Fix fallback logic, add validation

3. **No Audit Trail** (Severity: LOW)
   - Can't determine which models were trained with which config
   - Historical analysis impossible
   - Mitigation: Add comprehensive metadata to future models

---

## 12. Summary

**Current State:**
- ✅ Model loading uses st_mtime (works correctly)
- ✅ Latest model selected: BTCUSDT_1h_xgboost_20260616_014211.pkl
- ❌ Model metadata incomplete (missing labeling_method)
- ❌ Cannot verify production model matches research winner
- ❌ Likely using fixed_horizon (suboptimal)

**Action Required:**
1. Retrain BTCUSDT 1h with triple_barrier (config already updated)
2. Add metadata validation to load_latest_model()
3. Update trainer.py to save complete metadata

**Next Model Training:** Will automatically use triple_barrier (config updated today)

**Timeline to Research Winner in Production:** ~30 minutes (retrain + deploy)
