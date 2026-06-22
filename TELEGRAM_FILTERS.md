# Telegram Signal Quality Filtering

To reduce notification noise, MoroQuant only forwards **high-quality,
actionable** signals to Telegram. A quality filter runs between signal
generation and the notification dispatch.

> Filter design principle: **reject by default**. When in doubt (missing
> fields, parse errors), no message is sent. The scheduler is never
> interrupted — a rejected signal is simply logged and skipped.

---

## 1. Where the filter sits

```
predictor.generate_signal()
        │
        ▼
scheduler.signal_generation_job()
        │
        ├─ signal persisted to DB (already happened inside generate_signal)
        │
        ├─ should_send_telegram_alert(signal)   ◄── THIS filter
        │       │
        │       ├─ (True,  "passed") ─► send_signal_alert(signal) ─► Telegram
        │       └─ (False, reason) ───► logger.info("...skipped (reason=...)")
        │
        └─ try/except wraps everything; never throws back to the loop
```

The DB write happens **before** the filter, so every generated signal is
still stored regardless of whether it triggers a Telegram message. Filtering
only affects notifications, never signal persistence or analytics.

---

## 2. Filtering logic

A signal is sent to Telegram **only if ALL** of these conditions are met:

| # | Rule | Default | Configurable via |
|---|------|---------|------------------|
| 1 | `direction != "neutral"` | enforced | `telegram.allow_neutral` |
| 2 | `mtf_alignment == "AGREE"` | enforced | `telegram.require_mtf_agreement` |
| 3 | `confidence >= 70` | enforced | `telegram.min_confidence` |

### Evaluation order

Rules are checked cheapest-first:

1. **neutral direction** → `reason="neutral_signal"`
2. **MTF alignment** → `reason="mtf_disagree"`
3. **confidence threshold** → `reason="low_confidence"`

If all pass → `(True, "passed")`.

### Return contract

```python
should_send_telegram_alert(signal: dict) -> tuple[bool, str]
```

- On accept: `(True, "passed")`
- On reject: `(False, reason)` where `reason ∈ {"neutral_signal", "mtf_disagree", "low_confidence"}`
- The function **never raises**. A malformed signal or an internal error
  yields `(False, "neutral_signal")` (safe default = do not send).

---

## 3. Configuration

Add an optional `telegram` section to `ml_service/config.yaml`:

```yaml
telegram:
  min_confidence: 70            # alert only when confidence >= this value
  require_mtf_agreement: true   # require 1h/4h multi-timeframe agreement
  allow_neutral: false          # if false, neutral signals are suppressed
```

### Defaults (used when the section is missing)

| Key | Default | Meaning |
|-----|---------|---------|
| `min_confidence` | `70` | Minimum confidence percentage to alert |
| `require_mtf_agreement` | `true` | Require `mtf_alignment == "AGREE"` |
| `allow_neutral` | `false` | Allow `direction == "neutral"` to be alerted |

### Backward compatibility

- The `telegram:` section is **entirely optional**. If it is absent, the
  defaults above are applied and the system behaves exactly as specified.
- Bad types in the YAML are ignored per-key (the default for that key is
  used); the rest of the section still loads.
- A missing or unreadable `config.yaml` is also handled — defaults are used
  and a `DEBUG` log line is emitted. The scheduler is never interrupted.

---

## 4. Examples: sent vs skipped

### ✅ Sent

```
ETHUSDT 1h
direction = long
confidence = 86
mtf_alignment = AGREE
```
→ `(True, "passed")` → **Telegram message delivered**

```
BTCUSDT 4h
direction = short
confidence = 70        # exactly the threshold (>= comparison)
mtf_alignment = AGREE
```
→ `(True, "passed")` → **Telegram message delivered**

### ❌ Skipped

```
BTCUSDT 1h
direction = long
confidence = 49
mtf_alignment = DISAGREE
```
→ `(False, "mtf_disagree")` → **no message**

```
SOLUSDT 1h
direction = long
confidence = 55
mtf_alignment = AGREE
```
→ `(False, "low_confidence")` → **no message**

```
BNBUSDT 1h
direction = neutral
confidence = 92
mtf_alignment = AGREE
```
→ `(False, "neutral_signal")` → **no message** (with default config)

```
{ }   # empty / malformed signal
```
→ `(False, "neutral_signal")` → **no message** (safe default)

---

## 5. Logging

### On send (success path)

```
INFO  | Telegram alert sent: ETHUSDT 1h long
```

### On skip (filter reject)

```
INFO  | Telegram alert skipped: BTCUSDT 1h (reason=mtf_disagree)
INFO  | Telegram alert skipped: SOLUSDT 1h (reason=low_confidence)
INFO  | Telegram alert skipped: BNBUSDT 1h (reason=neutral_signal)
```

### On internal failure

```
ERROR | should_send_telegram_alert failed unexpectedly: <detail>
```

The error is logged and `(False, "neutral_signal")` is returned — the
scheduler loop continues to the next symbol/timeframe.

---

## 6. Tuning the filter

| Goal | Change |
|------|--------|
| Fewer, higher-conviction alerts | Raise `min_confidence` (e.g. `75`) |
| More alerts (loosen) | Lower `min_confidence`, or set `require_mtf_agreement: false` |
| Include neutral signals | Set `allow_neutral: true` |
| Disable MTF requirement | Set `require_mtf_agreement: false` |

After editing `config.yaml`, the change takes effect on the next
`signal_generation_job` run (no restart needed — config is re-read per
signal).

---

## 7. Testing

Unit tests live in `ml_service/tests/test_telegram_filter.py`. Run them
from the `ml_service` directory:

```bash
cd ml_service
python -m pytest tests/test_telegram_filter.py -v
# or, without pytest:
python -m unittest tests.test_telegram_filter -v
```

They cover:

- low confidence (incl. inclusive `>=` boundary at exactly 70)
- MTF DISAGREE / NEUTRAL
- neutral direction
- valid long and short signals
- multiple simultaneous failures (correct reason precedence)
- missing `confidence` / `mtf_alignment` / `direction`
- empty dict, `None`, wrong type, bad confidence type
- config overrides (`allow_neutral`, `require_mtf_agreement`, custom threshold)
- defensive: the filter never raises even if its config loader throws

All filter tests pin the config to documented defaults via mocking, so they
are deterministic and independent of the operator's `config.yaml`.
