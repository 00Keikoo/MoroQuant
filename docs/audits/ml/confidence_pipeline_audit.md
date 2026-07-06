# Confidence Pipeline Audit

**Date:** 2026-06-22
**Scope:** Audit only. No code modified. No retraining.
**Subject:** MoroQuant ML Trading Platform — confidence generation, calibration, and persistence lifecycle.

---

## Executive Summary

The confidence pipeline is **structurally compromised at the application layer**, not the model layer. Three independent, verifiable defects combine to produce the ECE of 43–56% reported in `CONFIDENCE_RELIABILITY_AUDIT.md`:

1. **Calibration is computed but never applied.** The predictor explicitly loads the calibration artifact, logs `"Calibration applied: False (using raw probabilities)"`, and then uses the raw `predict_proba` output as the confidence value. The Platt calibrator chosen during training (holdout ECE = 0.039) is discarded at inference time.

2. **The confidence value is not a calibrated probability after MTF post-processing.** A non-probabilistic scalar multiplier (×1.15 on agreement, ×0.80 on conflict) is applied to the raw max-probability for 1h signals. This is fired ~5,927 times in production logs and breaks the `[0,1]` probability interpretation that ECE measurement assumes.

3. **The validation confidence distribution used for drift detection is absent from every active production model.** The trainer writes `confidence_distribution` to metadata (trainer.py:709-726), but all 10 active models predate that code path. There is therefore no baseline to measure drift against — and the calibration artifact itself exists for only 1 of 5 active 1h models.

The hypothesis "confidence pipeline may be fundamentally broken" is **supported by evidence**. The root cause is not the model's raw probabilities (which are reasonably calibrated on the holdout, ECE ≈ 0.11) but the production code path that bypasses calibration and then mutates the value.

---

## Part 1 — Confidence Generation Lifecycle Trace

The complete path, with exact code references:

### Stage A: `model.predict_proba()` → raw probabilities

`ml_service/models/predictor.py:196-208`

```python
if isinstance(model, dict) and 'xgb' in model and 'lgb' in model:
    xgb_proba = model['xgb'].predict_proba(X_latest)[0]
    lgb_proba = model['lgb'].predict_proba(X_latest)[0]
    raw_proba = (xgb_proba + lgb_proba) / 2        # ensemble: arithmetic mean
    ...
else:
    raw_proba = model.predict_proba(X_latest)[0]   # single model
```

- **Ensemble path:** raw probability = arithmetic mean of XGBoost and LightGBM `predict_proba` outputs. No renormalization is applied after averaging (the mean of two normalized vectors is still normalized by linearity, so this is sound).
- **Single-model path:** raw probability used directly.
- Both branches produce a 3-element vector `[P(short), P(neutral), P(long)]`.

### Stage B: Calibration artifact loaded but NOT applied

`ml_service/models/predictor.py:81-83` (load):

```python
cal_artifact = cal_mod.load_calibration_artifact(model_path)
if cal_artifact:
    model_package['calibration'] = cal_artifact
```

`ml_service/models/predictor.py:94-95` (explicit non-use):

```python
logger.info(f"  Calibration available: {cal_artifact is not None}")
logger.info(f"  Calibration applied: False (using raw probabilities)")
```

`ml_service/models/predictor.py:210-223` (confidence computation):

```python
# Use raw probabilities (research validated approach)
# Calibration artifacts loaded for diagnostics but NOT applied
cal_artifact = model_package.get('calibration')
calibration_available = cal_artifact is not None
if calibration_available:
    calibration_method = cal_artifact['chosen_method']
else:
    calibration_method = 'none'

# Always use raw probabilities (no calibration applied)
prediction_proba = raw_proba
prediction = int(np.argmax(prediction_proba))
confidence = float(prediction_proba[prediction])
confidence_pct = int(confidence * 100)
```

**The loaded calibrator is never passed to `cal_mod.apply_calibrator()`.** The variable `prediction_proba` is assigned `raw_proba` unconditionally. The comments `"research validated approach"` and `"Calibration artifacts loaded for diagnostics but NOT applied"` confirm this is intentional, not accidental.

### Stage C: Confidence formula

```python
confidence = float(prediction_proba[prediction])   # = max(proba) by construction
```

Because `prediction = argmax(proba)`, `prediction_proba[prediction] == max(proba)`. The confidence is therefore the **argmax-class raw probability**.

### Stage D: MTF post-processing (1h signals only)

`ml_service/models/predictor.py:324-345`

```python
if timeframe == '1h' and not skip_mtf:
    higher_tf_signal = generate_signal(symbol, '4h', ..., confidence_threshold=...)
    if higher_tf_signal['direction'] == signal['direction']:
        signal['confidence'] = min(100, int(signal['confidence'] * 1.15))
        signal['confidence_raw'] = min(1.0, signal['confidence_raw'] * 1.15)
    else:
        signal['confidence'] = max(0, int(signal['confidence'] * 0.80))
        signal['confidence_raw'] = max(0.0, signal['confidence_raw'] * 0.80)
        signal['mtf_conflict'] = True
```

This multiplies the integer confidence by **1.15** (agreement) or **0.80** (conflict). This is a heuristic scalar, not a probability operation.

### Stage E: Database persistence

`ml_service/models/predictor.py:408-454` (`save_signal_to_db`):

```python
cursor.execute("""
    INSERT INTO signals (
        symbol, timeframe, timestamp, direction, confidence, features_json,
        ..., prob_short, prob_neutral, prob_long
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", (..., signal['confidence'], ..., signal['prob_short'], signal['prob_neutral'], signal['prob_long']))
```

The persisted `confidence` column holds the **post-MTF, integer-truncated** value. The raw per-class probabilities (`prob_short/neutral/long`) are also persisted, but these too are the **raw** (uncalibrated) probabilities — MTF does not modify them, only the scalar `confidence`.

### Lifecycle summary

```
model.predict_proba()
   │  raw [P(short), P(neutral), P(long)]
   ▼
[calibration loaded but SKIPPED]            ← predictor.py:210-223
   │  raw proba unchanged
   ▼
confidence = max(raw_proba)                 ← predictor.py:222
   │
   ▼
MTF: ×1.15 or ×0.80 (1h only)              ← predictor.py:336-343
   │  confidence now a heuristic-scaled value, not a probability
   ▼
int(confidence * 100)                       ← predictor.py:223
   │
   ▼
INSERT INTO signals (confidence, ...)       ← predictor.py:408-454
```

---

## Part 2 — Calibration Audit

**Question:** Is model calibration actually being used in production?

**Answer:** **No.** With evidence.

### Evidence 2.1 — Code path never invokes the applier

A codebase-wide search for `apply_calibrator` (the only function that maps raw → calibrated probabilities) returns exactly three call sites:

| Location | Role | Production? |
|----------|------|-------------|
| `models/calibration.py:285` | inside `fit_and_score_all` (training-time self-evaluation) | No |
| `compare_backtest_methods.py:238` | offline research comparison script | No |
| `compare_backtest_methods.py.bak`, `.bak2` | backups of same | No |

**Zero call sites in `predictor.py` or any live inference path.**

### Evidence 2.2 — Predictor self-declares non-application

`ml_service/models/predictor.py:95`:
```
Calibration applied: False (using raw probabilities)
```

This is a hard-coded log string emitted on every model load, not a conditional. It is a statement of policy.

### Evidence 2.3 — Calibrator is chosen during training but discarded at load

`ml_service/storage/logs/ml_service.log` contains exactly one calibration-fit event (the most recent retrain, BTCUSDT 1h, 2026-06-18):

```
Calibration metrics (holdout=50):
  raw:      ECE=0.110  LL=1.043  Brier=0.644
  platt:    ECE=0.039  LL=0.800  Brier=0.459   ← chosen
  isotonic: ECE=0.051  LL=0.711  Brier=0.409
  → chosen: platt
```

So on the training holdout:
- raw ECE = **11.0%**
- platt ECE = **3.9%** (selected as best)
- isotonic ECE = 5.1%

The Platt calibrator reduces holdout ECE by roughly 2.8×. It is saved to `BTCUSDT_1h_xgboost_20260618_112740_calibration.pkl`. The predictor loads this file (predictor.py:81-83), reads `chosen_method` for logging, and then **assigns `prediction_proba = raw_proba`** without ever calling `apply_calibrator`.

### Evidence 2.4 — Fallback behavior

The fallback when no calibration artifact exists is implicit: because calibration is never applied *regardless* of artifact presence, the absence of an artifact has **no behavioral effect** — raw probabilities are used either way. The only observable difference is the `calibration_available` boolean included in the signal dict for diagnostics.

### Evidence 2.5 — Artifact coverage is incomplete anyway

Of the 5 active 1h models:

| Model | Calibration artifact present? |
|-------|------------------------------|
| BTCUSDT_1h_xgboost_20260618_112740 | YES |
| ETHUSDT_1h_xgboost_20260610_210848 | NO |
| SOLUSDT_1h_xgboost_20260611_091300 | NO |
| BNBUSDT_1h_xgboost_20260610_212026 | NO |
| HYPEUSDT_1h_xgboost_20260604_174446 | NO |

Only 1 of 5 has a calibrator. Even if the predictor applied calibration, 4 of 5 models would fall back to raw probabilities. The `_fit_and_save_calibration` function (trainer.py:764-801) skips fitting when the holdout has a single class or no holdout was captured — which explains the missing artifacts for older models.

**Conclusion of Part 2:** Calibration exists as infrastructure but is architecturally inert in the production inference path. The 11% holdout ECE never reaches production; production inherits the raw 11% (per-class) plus all downstream distortion.

---

## Part 3 — Confidence Formula Audit

**Question:** How is confidence calculated, and is the formula mathematically sound?

### Formula in use

`ml_service/models/predictor.py:221-223`:

```python
prediction = int(np.argmax(prediction_proba))
confidence = float(prediction_proba[prediction])
confidence_pct = int(confidence * 100)
```

**Formula:** `confidence = max(P(short), P(neutral), P(long))`

This is the **argmax-class probability** (a.k.a. "max-prob" or "winner-takes-all" confidence).

### Formula variants considered and rejected by the codebase

| Variant | Formula | Used? |
|---------|---------|-------|
| Max probability | `max(proba)` | **YES — this is the production formula** |
| Margin | `max(proba) − second_max(proba)` | No |
| Entropy | `1 − H(proba)/log(K)` | No |
| Softmax | n/a (inputs are already softmax outputs from XGB/LGB) | n/a |

The per-class probabilities (`prob_short`, `prob_neutral`, `prob_long`) are persisted to the DB (migration 005), so margin and entropy could be derived retroactively, but neither is computed or stored.

### Soundness analysis

**The max-probability formula is mathematically sound *as a confidence measure*, conditional on two premises:**

1. **The input probabilities are calibrated.** Max-prob is a valid confidence statistic only if the underlying `predict_proba` outputs are calibrated — i.e., P(predicted class) ≈ empirical accuracy at that probability level. ECE then measures the gap. **This premise is violated in production** (Part 2: calibration is bypassed), so the max-prob value is not interpretable as a true probability of correctness.

2. **No non-probabilistic transformation is applied downstream.** Max-prob ∈ [1/3, 1] for a 3-class problem. Any multiplicative scaling breaks the probability semantics. **This premise is also violated** (Part 1, Stage D: MTF multiplies the value by 1.15 or 0.80).

**Specific soundness defects:**

- **Floor violation.** For a 3-class softmax, `max(proba) ≥ 1/3 ≈ 0.333` always. After MTF conflict scaling (×0.80), the value can drop as low as `0.333 × 0.80 = 0.267`. A "confidence" of 26.7% is below the random-chance floor of 33.3% for 3 classes, which is not mathematically meaningful as a probability. The DB shows 495 signals in the 0–39% bucket, consistent with this floor break.
- **Integer truncation before storage.** `confidence_pct = int(confidence * 100)` truncates rather than rounds (predictor.py:223). A raw 0.7299 becomes 72, not 73. This introduces a small systematic downward bias of up to 0.99 percentage points per signal.
- **MTF re-derives confidence from an already-truncated integer.** Stage D multiplies `signal['confidence']` (the integer) by 1.15/0.80 and re-truncates. The compounded truncation error is up to ~1.5 pp for boosted signals.
- **The 1.15/0.80 multipliers are untuned heuristics.** No evidence in the codebase or logs that these constants were derived from data. They are hardcoded literals.

**Conclusion of Part 3:** The max-probability formula is a standard, defensible choice. Its soundness in this codebase is undermined not by the formula itself but by (a) feeding it uncalibrated inputs and (b) post-processing it with non-probabilistic scalars. The formula is the wrong thing to audit; the inputs and post-processing are the defects.

---

## Part 4 — Production vs. Validation Confidence Distribution

**Question:** Is there distribution drift between validation and live production confidence?

**Answer:** **The comparison cannot be performed for any active model, because the validation distribution baseline does not exist in production metadata.** This is itself a finding.

### Evidence 4.1 — Validation distribution is collected by the trainer but absent from production

`ml_service/models/trainer.py:709-726` collects `test_confidences` from every walk-forward fold and stores a `confidence_distribution` dict (mean, std, sampled values) in `metadata['validation']`:

```python
all_val_confidences = []
for r in fold_results:
    all_val_confidences.extend(r.get('test_confidences', []))
if all_val_confidences:
    ...
    validation_metrics['confidence_distribution'] = {
        'mean': float(np.mean(conf_arr)),
        'std': float(np.std(conf_arr)),
        'values': [float(x) for x in conf_sampled]
    }
```

A pickle-opcode disassembly of all 10 active production models (per `active_models.json`) shows:

```
BTCUSDT_1h  (20260618): validation key present, confidence_distribution: NO
BTCUSDT_4h  (20260610): validation key present, confidence_distribution: NO
ETHUSDT_1h  (20260610): validation key present, confidence_distribution: NO
ETHUSDT_4h  (20260610): validation key present, confidence_distribution: NO
SOLUSDT_1h  (20260611): validation key present, confidence_distribution: NO
SOLUSDT_4h  (20260610): validation key present, confidence_distribution: NO
BNBUSDT_1h  (20260610): validation key present, confidence_distribution: NO
BNBUSDT_4h  (20260610): validation key present, confidence_distribution: NO
HYPEUSDT_1h (20260604): validation key present, confidence_distribution: NO
HYPEUSDT_4h (20260603): validation key present, confidence_distribution: NO
```

**Every active model predates the `confidence_distribution` code path.** None carries the baseline. Drift cannot be measured against a baseline that was never recorded.

### Evidence 4.2 — The only available validation-side data point

The single calibration-fit log entry (BTCUSDT 1h, 2026-06-18) gives the **raw-probability** holdout ECE of 0.110. This implies the raw max-prob distribution on that fold was centered high enough to produce ~11% miscalibration — consistent with XGBoost's known tendency toward overconfident but roughly sigmoidal probability outputs.

### Evidence 4.3 — Live production confidence distribution (from DB)

Query against `signals` (direction ≠ neutral, confidence not null), N = 19,808:

| Bucket | Count | % of signals |
|--------|------:|-------------:|
| 80–100 | 8,571 | 43.3% |
| 60–79  | 7,444 | 37.6% |
| 40–59  | 3,298 | 16.6% |
| 0–39   |   495 |  2.5% |

- **Mean production confidence: 76.55%**
- **Range: 28–100%**

### Evidence 4.4 — The 0–39% bucket is anomalous

495 signals (2.5%) sit below the 3-class random-chance floor of 33.3%. These cannot exist from raw `max(proba)` alone — they are the product of MTF conflict scaling (×0.80) pushing sub-50% raw confidences below the floor. This is direct, live evidence that the MTF post-processing in Stage D is operating in production and distorting the distribution.

### Evidence 4.5 — Realized outcomes are nearly absent from the DB

Joining `signals` to `signal_outcomes`:

| Bucket | n | wins | losses | timeouts |
|--------|--:|-----:|-------:|---------:|
| 80–100 | 8,571 | 0 | 0 | 3 |
| 60–79  | 7,444 | 0 | 0 | 1 |
| 40–59  | 3,298 | 0 | 0 | 0 |
| 0–39   |   495 | 0 | 0 | 0 |

Only 4 resolved outcomes exist (all timeouts). This is the signature of the outcome-engine bug documented in `OUTCOME_LOGIC_AUDIT.md` / `OUTCOME_ENGINE_REPAIR.md`: signals were stuck in PENDING. The 22,752 signals and win rates in `CONFIDENCE_RELIABILITY_AUDIT.md` therefore come from **reconstructed** outcomes (`signal_reconstruction.py`), not actual ones. The ECE of 43–56% is measured against reconstruction, which uses ATR-derived synthetic TP/SL (2.0×/1.0× multipliers per `signal_reconstruction.py:46-48`) — different from the production 3.0×/1.5× triple-barrier labels. This is a measurement-layer confound, separate from the pipeline defects.

**Conclusion of Part 4:** Drift cannot be quantified (no validation baseline in production). Qualitatively, the production distribution is heavily right-skewed (81% of signals above 60%), consistent with uncalibrated tree-ensemble `predict_proba` combined with MTF inflation. The sub-floor bucket proves MTF distortion is live.

---

## Part 5 — Root Cause Analysis for ECE > 40%

Ranked by evidential strength. Each cause lists the evidence supporting it.

### 🔴 HIGH — Calibration bypass in the inference path

**Mechanism:** The Platt calibrator (holdout ECE = 0.039) is loaded but never applied. Production inherits raw probabilities (holdout ECE = 0.110) and then accumulates further distortion.

**Evidence:**
- predictor.py:95 hard-logs `"Calibration applied: False (using raw probabilities)"`.
- predictor.py:219-220: `prediction_proba = raw_proba` unconditionally.
- predictor.py:210-211 comment: `"Calibration artifacts loaded for diagnostics but NOT applied"`.
- Zero `apply_calibrator` call sites in any live code path (Part 2.1).
- Training log shows platt reduces ECE from 0.110 → 0.039 on the holdout (Part 2.3).

**Expected ECE contribution:** This alone accounts for the gap between ~11% (raw holdout) and the floor of what production *could* achieve. It is necessary but not sufficient for 43%.

### 🔴 HIGH — MTF non-probabilistic confidence mutation

**Mechanism:** The ×1.15/×0.80 MTF multipliers transform a probability into a heuristic score with no calibration guarantee. Inflation pushes mass into the 80–100% bucket; deflation pushes mass below the 33% random floor.

**Evidence:**
- predictor.py:336-343: literal multipliers applied to `signal['confidence']`.
- Production log: 5,927 MTF events (confirmation + conflict).
- Sample log lines show boost 50%→58% and reduce 66%→53%, i.e., values crossing bucket boundaries.
- DB: 495 signals in the 0–39% bucket (sub-floor), impossible without MTF conflict scaling.

**Expected ECE contribution:** Substantial. Bucket-level analysis in `CONFIDENCE_RELIABILITY_AUDIT.md` shows non-monotonic win rates (50–60% bucket outperforms 80%+), which is the exact signature of post-hoc inflation putting high-confidence labels on average-quality signals.

### 🟡 MEDIUM — Calibration artifact coverage is incomplete

**Mechanism:** Even if the bypass were fixed, 4 of 5 active 1h models have no calibrator artifact. They would fall back to raw probabilities regardless.

**Evidence:**
- Artifact presence check (Part 2.5): only BTCUSDT_1h has `_calibration.pkl`.
- trainer.py:764-801 skips calibration fit when the holdout is degenerate (single class) or absent — the condition that produced the missing artifacts.

**Expected ECE contribution:** Conditional. Becomes the binding constraint once the bypass is fixed. Today it is masked by the bypass.

### 🟡 MEDIUM — Reconstruction-based measurement layer confound

**Mechanism:** The 43–56% ECE figures in `CONFIDENCE_RELIABILITY_AUDIT.md` are computed against **reconstructed** outcomes (ATR-derived 2.0×/1.0× TP/SL), not actual outcomes. Production uses triple-barrier labels with 3.0×/1.5× multipliers. The label definitions differ, so win/loss attribution differs, inflating apparent miscalibration independently of the confidence pipeline.

**Evidence:**
- `signal_reconstruction.py:46-48`: `DEFAULT_TP_MULTIPLIER = 2.0`, `DEFAULT_SL_MULTIPLIER = 1.0`.
- config.yaml: production `tp_atr_mult: 3.0`, `sl_atr_mult: 1.5`.
- DB has 4 actual outcomes vs 22,752 reconstructed signals used for the audit.

**Expected ECE contribution:** Adds a measurement artifact on top of the real pipeline defects. The true pipeline-only ECE is not separable from this confound using current data.

### 🟢 LOW — Integer truncation bias

**Mechanism:** `int(confidence * 100)` truncates rather than rounds, then MTF re-truncates. Combined downward bias up to ~1.5 pp per signal.

**Evidence:**
- predictor.py:223 (`confidence_pct = int(confidence * 100)`).
- predictor.py:336-341 (MTF operates on the already-truncated integer).

**Expected ECE contribution:** Small and systematic. Cannot explain a 40+ pp gap but adds noise to bucket boundaries.

### 🟢 LOW — Small calibration holdout (n=50)

**Mechanism:** The calibrator is fit on a single walk-forward fold's 50-row holdout slice (trainer.py:364-370, `test_size: 50`). Platt sigmoid fit on n=50 is high-variance; the 0.039 holdout ECE may be optimistically biased.

**Evidence:**
- trainer.py:367: `test_size = 50`.
- Log: `Calibration metrics (holdout=50)`.

**Expected ECE contribution:** Uncertain direction. Would be resolved by fitting on pooled out-of-fold predictions instead of the last fold only.

---

## Part 6 — Methodology and Limitations

### What was audited
- Static code analysis of `predictor.py`, `trainer.py`, `models/calibration.py`, `governance.py`, `config.yaml`.
- Production artifact inspection: `active_models.json`, pickle-opcode disassembly of all 10 active model files, calibration artifact presence checks.
- Production log analysis: calibration-fit events, MTF events, inference events.
- Database queries against `signals` (N=19,808 directional) and `signal_outcomes`.

### What was NOT done (per scope)
- No code modified.
- No models retrained.
- No calibration applied or re-fit.
- No recommendations beyond what the evidence directly states; causes are ranked but no fix is proposed.

### Key limitations
1. **Validation baseline is missing** for all active models (Part 4.1), so drift is inferred qualitatively, not measured.
2. **Actual outcomes are nearly absent** (4 rows in `signal_outcomes`), so ECE cannot be recomputed against ground truth — only against reconstruction. The 43–56% figures inherit the reconstruction confound (Part 5, MEDIUM).
3. **sklearn/xgboost are not installed in the audit environment**, so model internals could not be unpickled; pickle-opcode disassembly was used instead to inspect stored metadata keys. This is sufficient for key presence/absence but not for reading nested float values reliably.
4. **Only one calibration-fit log entry exists**, so the holdout ECE figures (raw 0.110, platt 0.039) are a single data point for a single model and may not generalize.

---

## Evidence Index

| Claim | Source |
|-------|--------|
| Calibration loaded but not applied | predictor.py:81-83, 94-95, 210-223 |
| `apply_calibrator` never called in live path | grep across `ml_service/` (3 hits, all offline) |
| Confidence = max(raw_proba) | predictor.py:221-222 |
| MTF ×1.15 / ×0.80 multipliers | predictor.py:336-343 |
| MTF fired 5,927 times in production | `ml_service.log` grep |
| Calibration holdout ECE: raw 0.110 / platt 0.039 | `ml_service.log` 2026-06-18 |
| No active model carries `confidence_distribution` | pickle disassembly of 10 active models |
| Only 1 of 5 active 1h models has calibration artifact | filesystem check of `production/` |
| Live confidence mean 76.55%, 495 sub-floor signals | sqlite query on `signals` |
| Only 4 actual outcomes in DB | sqlite query on `signal_outcomes` |
| Reconstruction uses 2.0×/1.0× vs production 3.0×/1.5× | signal_reconstruction.py:46-48; config.yaml |
| Integer truncation | predictor.py:223 |
| Calibration holdout size = 50 | trainer.py:367 |
