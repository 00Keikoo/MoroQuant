# Model Governance Guide

## Overview

The model governance system prevents worse models from entering production by implementing a safe promotion workflow with quality gates.

## Directory Structure

```
storage/models/
├── production/     # Active production models (used by predictor)
├── candidates/     # Newly trained models pending review
└── archive/        # Superseded production models (for rollback)
```

## Promotion Rules

A candidate model is promoted to production ONLY if:

1. **Improvement threshold met**: `candidate_f1 >= production_f1 * 1.03` (3% improvement required)
2. **Sufficient validation**: At least 3 folds in walk-forward validation
3. **No existing production model**: First model for symbol/timeframe is auto-promoted

## Workflow

### Scheduled Retrain (Every 24h)

1. Scheduler fetches latest data
2. `train_model()` trains and saves to `candidates/`
3. `governance.compare_and_promote()` evaluates candidate
4. If promoted: move to `production/`, archive old model
5. If rejected: stays in `candidates/`, production unchanged
6. Results logged to `storage/logs/retrain_log.csv`

### Manual Training

```bash
# Train and save to candidates
python cli.py train --symbol BTCUSDT --timeframe 1h

# Manually promote (if you override governance)
from ml_service.models.governance import promote_model
promote_model(candidate_path, "BTCUSDT", "1h")
```

## Rollback

If a promoted model causes issues:

```python
from ml_service.models.governance import rollback_model

result = rollback_model("BTCUSDT", "1h")
# Restores most recent archived model to production
```

**Manual rollback via filesystem**:
```bash
cd storage/models/archive
# Find archived model
ls -lt BTCUSDT_1h_*_archived_*.pkl | head -1

# Copy back to production with new name
cp <archived_file> ../production/BTCUSDT_1h_xgboost_recovered_$(date +%Y%m%d_%H%M%S).pkl

# Restart predictor to clear cache
# Predictor will load newest mtime from production/
```

## Monitoring

Check promotion status:
```bash
# View recent retrain results
tail -20 storage/logs/retrain_log.csv

# Check production models
ls -lth storage/models/production/*.pkl | head -20

# Check rejected candidates
ls -lth storage/models/candidates/*.pkl | head -20
```

## Configuration

**Improvement threshold** in `scheduler.py`:
```python
F1_THRESHOLD = 1.03  # Require 3% improvement
```

Lower values make promotion easier, higher values make it stricter.

## Safety Features

1. **Atomic promotion**: Old model archived before new model activated
2. **Calibration preserved**: `*_calibration.pkl` files moved together with models
3. **Fallback path**: Predictor falls back to `models/` if `production/` missing
4. **Metadata preservation**: All validation metrics stored in model files
5. **Audit trail**: Archive directory maintains rollback history

## Migration Notes

- Existing models migrated to `production/` on first run
- Old models remain in root `models/` directory (safe to archive after verification)
- Predictor maintains in-memory cache, restart required after manual changes

## Troubleshooting

**Predictor loads old model**:
- Clear cache: restart ML service
- Check production directory exists and has models
- Verify file mtime: `stat storage/models/production/BTCUSDT_1h_*.pkl`

**All models rejected**:
- Check F1_THRESHOLD (may be too strict)
- Verify validation metrics in candidate model metadata
- Check logs for rejection reasons

**Need to force-promote a model**:
```python
# Override governance (use with caution)
from ml_service.models.governance import promote_model
promote_model("/path/to/candidate.pkl", "BTCUSDT", "1h")
```
