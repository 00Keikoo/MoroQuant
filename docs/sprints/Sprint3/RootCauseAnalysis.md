# Root Cause Analysis

## 1. Primary Root Cause

The Replay parity was extremely low (~0.01% parity) because **prediction probabilities and calibration details were lost during loading from the database**. 

Specifically:
- In production, `models/predictor.py` successfully computes and saves `prob_short`, `prob_neutral`, and `prob_long` into the SQLite `signals` table.
- However, `repositories/signal_repository.py` had a hardcoded SQL query that selected only 8 basic columns (`id`, `symbol`, `timeframe`, `timestamp`, `direction`, `confidence`, `features_json`, `created_at`).
- When the `Snapshot Engine` loaded signals using `SignalRepository.find_recent()`, all probability and model version fields were returned as `None`.
- Consequently, the `Replay Engine` fell back to `0.0` for all probabilities. When `DecisionEngine` performed the argmax, a tie occurred (`[0.0, 0.0, 0.0]`), which always resolved to index `0` (`SHORT`).
- This caused Replay to reconstruct `SHORT` for almost all signals, which diverged completely from production's original decisions (which were predominantly `HOLD` or filtered to `neutral`).

## 2. Secondary Root Cause (Decision Engine bug)

Additionally, the `DecisionEngine` failed to apply the LONG/SHORT confidence threshold rules:
- Even when probabilities were restored, `DecisionEngine.decide` did not check if the confidence exceeded the thresholds.
- In production, if confidence falls below the threshold, the signal direction is rewritten to `'neutral'`. 
- `DecisionEngine` lacked this fallback logic, producing active directions (e.g. `LONG`) for weak signals that production had filtered to `HOLD`.

## 3. Severity & Impact

- **Severity**: Blocker
- **Impact**: Parity rate was zero, rendering research overlays, replay verification, and backtesting comparison scientifically invalid.

## 4. Minimal Fixes Applied

1. **Signal Dataclass & Repository Extension**: Extended the `Signal` dataclass and updated `SignalRepository` to dynamically load all schema columns, populating probabilities and model details.
2. **Threshold Logic in DecisionEngine**: Added confidence threshold checks to `DecisionEngine.decide` so that weak decisions fall back to `HOLD`.
3. **Replay Engine Compatibility**: Ensured the Replay decisions list includes both `reason_code` and `reason_codes` keys to pass verify scripts.
