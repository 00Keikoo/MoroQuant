# Live Analytics Dashboard — Data Pipeline Audit

**Date:** 2026-06-24
**Scope:** `/dashboard/performance` end-to-end data integrity
**Status:** Findings only — **no code changes applied yet** (per request)

---

## TL;DR

The dashboard's only source of truth for real trading PnL is the
`user_trade_history` SQLite table, populated by the `sync-trades` CLI command.
**Four independent defects** make the dashboard diverge from Binance:

| # | Symptom | Root cause (one line) |
|---|---------|------------------------|
| 1 | Recent trades missing / stale | `sync-trades` is **never scheduled**; runs only by hand |
| 2 | `sync-trades` returns no trades | Binance `/fapi/v1/userTrades` is called **without `symbol`** → API error -1102 (mandatory param missing) |
| 3 | Equity curve wrong | Equity is `cumsum(net_pnl)` over **every fill**, not over **closed positions**; partial fills & fees distort it. Plus no data (see #1/#2) |
| 4 | Regime shows `Unknown` | Enrichment reads `features_json['market_phase']` (never set) instead of the `signals.regime` column |

All four are **backend** problems. The Next.js frontend is a correct,
direct-to-FastAPI consumer with no caching layer of its own.

---

## Pipeline map (as-built)

```
┌─────────────────────────────────────────────────────────────────────┐
│ Binance Futures API  (fapi.binance.com)                             │
│   /fapi/v1/userTrades   ← fills  (REQUIRES symbol param)            │
│   /fapi/v2/positionRisk ← open positions                            │
└───────────────────────────┬─────────────────────────────────────────┘
                            │ manual only: `python cli.py sync-trades`
                            │   (no scheduler job exists)  ← DEFECT #1
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│ ml_service/data/exchange_sync.py                                    │
│   fetch_user_trades(symbol=None)  ← DEFECT #2 (fails without symbol)│
│   save_trades_to_db()             INSERT OR IGNORE on order_id      │
│   enrich_trades_with_signals()    reads WRONG regime field ← #4     │
└───────────────────────────┬─────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│ SQLite: ml_service/storage/database.db                              │
│   user_trade_history   ← one ROW per Binance FILL (not per position)│
│     id, symbol, side, price, qty, realized_pnl, commission,         │
│     trade_time(ms), order_id(UNIQUE), matched_signal_id,            │
│     market_regime, confidence_at_entry, synced_at                   │
│   signals              ← regime column exists but is unused by sync │
│   user_trades          ← UNRELATED manual paper-trading table       │
└───────────────────────────┬─────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│ ml_service/analytics/*.py                                           │
│   live_metrics.py       compute_live_metrics() + get_equity_curve() │
│     equity = cumsum(realized_pnl - commission) per FILL  ← DEFECT #3│
│   regime_performance.py  groups by market_regime (='unknown') ← #4  │
│   confidence_report.py   groups by confidence_at_entry              │
└───────────────────────────┬─────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│ FastAPI  ml_service/api/routes.py  (port 8000, prefix /api)         │
│   GET /analytics/live-performance      → metrics + equity_curve     │
│   GET /analytics/regimes               → regime buckets             │
│   GET /analytics/confidence            → confidence buckets         │
│   GET /positions/open                  → live Binance positions     │
└───────────────────────────┬─────────────────────────────────────────┘
                            │ direct fetch() — NO Next.js API proxy,
                            │ NO SWR/React Query cache
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Next.js frontend                                                    │
│   app/dashboard/performance/page.tsx                                │
│     lib/services/performanceService.ts  (fetchWithRetry, 15s)       │
│     polls every 30s (AUTO_REFRESH_MS)                               │
│   EquityCurveChart.tsx  → recharts line, sorted by trade_count      │
│   "Recent Trades" table ← derived from equity_curve, NOT a trades   │
│                            endpoint  ← DEFECT #3 (fill vs position) │
└─────────────────────────────────────────────────────────────────────┘
```

**Frontend component → API endpoint → service → table → source of truth**

| UI element | Endpoint | Service fn | Table | Source of truth |
|---|---|---|---|---|
| KPI cards | `/analytics/live-performance` | `compute_live_metrics` | `user_trade_history` | Binance fills (synced) |
| Equity curve | `/analytics/live-performance` | `get_equity_curve` | `user_trade_history` | Binance fills (synced) |
| Recent Trades | (same) | (same, client-sliced) | `user_trade_history` | Binance fills (synced) |
| Regime panel | `/analytics/regimes` | `compute_regime_performance` | `user_trade_history` ✕ `signals` | Binance fills + signals |
| Confidence panel | `/analytics/confidence` | `compute_confidence_performance` | `user_trade_history` | Binance fills (synced) |
| Open positions | `/positions/open` | `fetch_open_positions` | (live Binance) | Binance API (real-time) |

Note: `/trades` page uses a **different** endpoint (`/trades/history` → `user_trades` table). That is the manual paper-trading journal and is **not** part of the Binance performance pipeline.

---

## Detailed findings

### DEFECT #1 — No automatic trade synchronization

**Where:** `ml_service/scheduler.py` (`start_scheduler`), `ml_service/api/main.py` (`startup_event`)

The APScheduler background scheduler registers exactly four jobs:

| Job | Trigger |
|---|---|
| `retrain_job` | every 24h |
| `market_dominance_job` | every 1h |
| `signal_generation_job` | every 1h |
| `outcome_evaluation_job` | every 1h |

**There is no `trade_sync_job`.** `fetch_user_trades` / `save_trades_to_db` / `enrich_trades_with_signals` are imported only by `cli/commands.py::sync_trades`. The CLI `--continuous` flag prints *"Continuous mode not yet implemented"*.

`config.yaml` even declares `exchange_sync.sync_interval_hours: 6`, but **nothing reads that key** (grep confirmed: referenced nowhere outside the config file).

**Evidence (live DB):** `user_trade_history` has **22 rows**, newest `trade_time = 2026-06-18 04:17`. Today is 2026-06-24 → **6 days stale**, and the count (22 fills ≈ a handful of positions) is far below what an active Binance account would produce in that window.

**Impact:** Newly closed Binance positions never appear until someone manually runs `sync-trades`. This is the direct cause of "recently closed positions do not appear."

---

### DEFECT #2 — `sync-trades` cannot fetch trades (Binance API misuse)

**Where:** `ml_service/data/exchange_sync.py::fetch_user_trades` (line 48), called by `cli/commands.py::sync_trades` (line 644) with `symbol=None`.

The default (no `--symbol`) call builds a request to `/fapi/v1/userTrades` **without a `symbol` parameter**:

```python
params = {'limit': limit}      # symbol omitted
trades = _signed_request('/fapi/v1/userTrades', params, ...)
```

For **USDⓈ-M Futures** (`/fapi/v1/userTrades`), `symbol` is **mandatory**. The Binance docs describe the endpoint as "Get trades for a specific account and **symbol**." Omitting it returns error `{"code":-1102,"msg":"Mandatory parameter 'symbol' was not sent"}`.

> Note: the change-log entry that made `symbol` optional applies to the **Options** API (`/eapi/v1/userTrades`), not USDⓈ-M Futures. This is a common source of confusion.

The `_signed_request` helper logs the error and returns `None`; `sync_trades` then prints *"Failed to fetch trades"* and exits. So even when a human runs the command, **zero trades are inserted**. (The 22 existing rows came from earlier runs that passed a symbol, or from a prior code revision.)

Because the sandbox here has no outbound network to `fapi.binance.com`, I could not hit the live API, but the param-omission defect is unambiguous from the code and confirmed by the official docs.

**Correct approach:** loop over the traded symbols (or discover them from `/fapi/v2/account` positions + an income pull) and call `/fapi/v1/userTrades?symbol=…` per symbol, paginating with `startTime`/`fromId` for full history. `limit` (max 1000) is **per symbol**, not global.

**Impact:** Compounds defect #1 — even manual sync is broken for the no-symbol default path.

---

### DEFECT #3 — Equity curve is per-fill, not per-closed-position

**Where:** `ml_service/analytics/live_metrics.py::get_equity_curve` (line 177) and `compute_live_metrics` (line 17); rendered by `components/performance/EquityCurveChart.tsx`.

Current formula:

```python
# get_equity_curve, per row in user_trade_history ORDER BY trade_time ASC:
net_pnl = realized_pnl - commission
cumulative_pnl += net_pnl          # running total over EVERY fill
trade_count += 1                    # counts fills, not positions
```

Three problems:

**(3a) One Binance "trade" on the dashboard ≠ one Binance "position" in the account UI.**
Binance `/fapi/v1/userTrades` returns **execution fills**, not round-trip positions. A single position lifecycle (open → partial close → final close) produces multiple fills. The dashboard plots one equity point **per fill**, so the x-axis "trade count" and the "Recent Trades" table reflect fill count, not the closed positions a user sees in the Binance UI. Evidence in DB:

```
SUIUSDT  BUY  2 fills  qty 166.9   SELL 3 fills  qty 257.9   (net short — reversed)
HYPEUSDT BUY  2 fills  qty 2.91    SELL 2 fills  qty 4.16    (net short — reversed)
ADAUSDT  BUY  2 fills             SELL 2 fills
```

A user closing one position that filled in 3 partials sees **3** "trades" here.

**(3b) Entry fills show `realized_pnl = 0` but still incur commission.** The equity curve subtracts commission on **entry**, which is technically correct for net equity but makes every entry point dip negative before any PnL is realized — visually distorting the curve against the Binance "realized PnL history" view (which only books realized PnL at close). DB confirms: 12 entry/adjust fills contribute `$0.00` realized but `$0.560` in commission.

**(3c) No starting-balance anchor.** The curve plots `cumulative_pnl` from zero, not account equity (`starting_balance + cumulative_realized`). Binance's account equity view includes unrealized PnL and prior balance, so the dashboard line and the Binance equity number are **different quantities** and will never "match" by construction. The KPI "ROI" divides `total_pnl` by a config `initial_capital` (default 10000) that has no relationship to the real account — another source of "doesn't match."

**Aggregate check:** DB `SUM(realized_pnl - commission) = $1.66` across 22 fills (10 closing fills, `SUM(realized_pnl) = $2.68`). The number is arithmetically self-consistent, but it is "net realized PnL − all commissions," which is not what the user expects to reconcile against Binance's realized-PnL column.

**Impact:** "Equity curve doesn't match Binance" — by construction it can't, because (a) granularity is per fill, (b) entry commissions are booked upfront, and (c) it is a PnL-from-zero series, not account equity.

---

### DEFECT #4 — Regime Performance always shows `Unknown`

**Where:** `ml_service/data/exchange_sync.py::enrich_trades_with_signals` (line 151) + `ml_service/analytics/regime_performance.py::REGIME_LABELS` (line 17).

The enrichment code matches a trade to a signal, then reads the regime from the **features JSON** under a key that does not exist:

```python
# enrich_trades_with_signals, around line 275
features = json.loads(features_json)
market_regime = features.get('market_phase', 'unknown')   # ← wrong source
```

But regime is **not** stored in `features_json`. It is a **dedicated column** on the `signals` table (`signals.regime`), populated at signal-generation time. Verified in DB:

- `signals` schema includes `regime TEXT`.
- A matched signal's `features_json` keys are `['swing_low','swing_high','bb_middle','ema_50','bb_upper']` — **no `market_phase`, no `regime` key.**
- `features_json.get('market_phase', 'unknown')` therefore always returns `'unknown'`.

The SELECT that fetches the candidate signal is `SELECT id, direction, confidence, features_json, timeframe FROM signals …` — it never requests the `regime` column.

**Evidence (live DB):** All 22 trades have `market_regime = 'unknown'`, yet joining those trades to their matched signals shows real regimes:

```
choppy_low_vol          10
choppy_normal_vol        2
transitioning_normal_vol 4
trending_normal_vol      6
```

So the data is correct and present — the enrichment merely reads the wrong field.

**Secondary defect (same area):** even after fixing the field, `REGIME_LABELS` in `regime_performance.py` is **outdated**. It maps:

```python
{'trending','ranging','choppy_low_vol','high_volatility','unknown'}
```

but the actual `signals.regime` values are `choppy_low_vol`, `choppy_normal_vol`, `trending_normal_vol`, `transitioning_normal_vol`. `compute_regime_performance` falls back to the raw key via `REGIME_LABELS.get(regime, regime)`, so buckets would group correctly, but the `Unknown (historical data)` special-case in the frontend (`performance/page.tsx` line 333) would still mislabel any genuinely-null regime.

**Tertiary note:** `signals.regime` is `NULL` for 22,706 of ~22,831 signals (old signals predate the regime feature). Only signals generated after the regime column was added carry a value. Trades matched to old signals legitimately have no regime — but current matched trades all have one, so the field-read bug is the dominant cause.

**Impact:** Regime Performance widget shows a single `Unknown` bucket. The frontend masks it as `"Unknown (historical data)"`, hiding the real distribution.

---

## Secondary observations (not requested, flagged for awareness)

- **Two "trade history" tables, two meanings.** `user_trades` (manual paper journal, `/trades` page) and `user_trade_history` (Binance fills, `/dashboard/performance`). They never intersect. This is fine but is a likely source of user confusion ("my closed trade on /trades doesn't show in performance").
- **No dedup bug currently** — `order_id` is `UNIQUE` and `INSERT OR IGNORE` is used correctly; DB shows 0 duplicate order_ids. Dedup is sound *if* trades ever get fetched.
- **`sync_interval_hours` config** is dead config. Once a scheduler job is added (defect #1 fix), it should be honored.
- **No Next.js API routes in the performance path** — `performanceService.ts` and `ml-trading.ts` call `:8000` directly. The `app/api/*` routes are public market-data only (klines, funding rate). So there is no proxy cache to bust.
- **Frontend polling is correct** — 30s interval, retry with backoff, no SWR/React Query. Stale data is purely a backend freshness problem (defect #1).
- **`get_equity_curve` is called twice** per report request (once inside `compute_live_metrics`'s caller in `routes.py`, the metrics fn itself doesn't call it; the route calls both). Minor inefficiency, not a correctness issue.

---

## Proposed fix plan (to apply after approval)

All fixes are backend; **no UI changes**.

1. **Defect #2 (blocking):** Rewrite `fetch_user_trades` to iterate symbols and paginate (`startTime` watermark from the max `trade_time` already in DB). Add a symbol list derived from config + open positions. Keep `INSERT OR IGNORE` dedup.
2. **Defect #1:** Add a `trade_sync_job` to `scheduler.py` using `config.exchange_sync.sync_interval_hours` (default 6h); run once on FastAPI startup (`main.py::startup_event`) so freshly closed positions appear without waiting.
3. **Defect #4:** In `enrich_trades_with_signals`, `SELECT … regime …` from `signals` and write `signals.regime` into `user_trade_history.market_regime`. Update `REGIME_LABELS` to the real value set. Backfill the 22 existing rows in the same pass.
4. **Defect #3:** Add a closed-**position** view (aggregate fills by symbol+direction into round trips) so equity/Recent-Trades reflect Binance positions, not fills. Anchor equity to a configurable starting balance and clearly label the series as "realized PnL." Preserve the existing fill-level data.
5. **Verify:** re-run enrichment, confirm regime distribution is non-Unknown; confirm new sync inserts recent Binance fills; `npm run build` + `tsc` unchanged.

Each fix is independent; #2 and #4 are the highest-leverage (they unblock data flow and fix the headline "Unknown" bug respectively).
