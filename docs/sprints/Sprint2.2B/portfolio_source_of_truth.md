# Portfolio Source of Truth Audit

**Sprint 2.2B — Backend Portfolio Normalization**  
**Date:** 2026-07-16  
**Objective:** Map all portfolio calculation sources to identify duplication and establish single source of truth

---

## Executive Summary

**Critical Finding:** Portfolio calculations are split between frontend and backend, with different implementations for PAPER and LIVE modes. The frontend currently computes margin ratio, account health, and total return percentage client-side.

**Goal:** Move ALL portfolio calculations into backend. Frontend becomes presentation-only layer.

---

## 1. Source of Truth Matrix

### 1.1 Equity

| Mode | Current Source | Location | Formula |
|------|---------------|----------|---------|
| **PAPER** | Backend | `ml_service/trading/paper_broker.py:158-193` | `equity = balance + unrealized_pnl` |
| **PAPER (Live)** | Backend | `ml_service/services/market_state_service.py:110-141` | `equity = balance + live_unrealized_pnl` |
| **LIVE** | Binance API | `ml_service/data/exchange_sync.py:716-795` | `margin_balance` from `/fapi/v2/account` |

**Status:** ✅ Backend owns this  
**Issue:** None — backend already authoritative

---

### 1.2 Wallet Balance

| Mode | Current Source | Location | Formula |
|------|---------------|----------|---------|
| **PAPER** | Database | `paper_account.balance` | Persisted, updated on position close |
| **LIVE** | Binance API | `exchange_sync.py:781` | `totalWalletBalance` from Binance |

**Status:** ✅ Backend owns this  
**Issue:** None — backend already authoritative

---

### 1.3 Initial Balance

| Mode | Current Source | Location | Value |
|------|---------------|----------|-------|
| **PAPER** | Hardcoded | `paper_broker.py:38` | `STARTING_BALANCE = 10000.0` |
| **PAPER (Fallback)** | Hardcoded | `market_state_service.py:120` | `10000.0` |
| **LIVE** | Config/Env | `live_metrics.py:31-75` | Resolved from config.yaml or env |

**Status:** ⚠️ Multiple hardcoded values  
**Issue:** 
- Paper broker uses hardcoded `10000.0`
- No stored initial_balance in database
- LIVE mode reads from config, but PAPER does not
- Frontend assumptions: `PortfolioOverview.tsx:24` uses `balance` as denominator for return %

**Gap:** No single source of truth for starting capital

---

### 1.4 Margin Used

| Mode | Current Source | Location | Formula |
|------|---------------|----------|---------|
| **PAPER** | Not exposed | — | Backend doesn't return this field |
| **LIVE** | Binance API | `exchange_sync.py` | Not explicitly fetched |
| **Frontend** | **COMPUTED** | `terminalService.ts:100` | `equity - available_balance` |

**Status:** ❌ Frontend calculates  
**Issue:** Backend doesn't return `margin_used`. Frontend computes as `equity - available_balance`

---

### 1.5 Margin Ratio

| Mode | Current Source | Location | Formula |
|------|---------------|----------|---------|
| **ALL** | **FRONTEND** | `PortfolioOverview.tsx:22` | `(marginUsed / equity) * 100` |

**Status:** ❌ Frontend calculates  
**Issue:** Backend doesn't provide this metric. Frontend computes it client-side.

---

### 1.6 Account Health

| Mode | Current Source | Location | Formula |
|------|---------------|----------|---------|
| **ALL** | **FRONTEND** | `PortfolioOverview.tsx:23` | `Math.min(100, (freeMargin / equity) * 100)` |

**Status:** ❌ Frontend calculates  
**Issue:** Backend doesn't provide this metric. Frontend computes it client-side.

---

### 1.7 Total Return %

| Mode | Current Source | Location | Formula |
|------|---------------|----------|---------|
| **ALL** | **FRONTEND** | `PortfolioOverview.tsx:24` | `((equity - balance) / balance) * 100` |

**Status:** ❌ Frontend calculates  
**Issue:** 
- Backend doesn't provide this metric
- Assumes `balance` = initial balance (incorrect for PAPER after realized PnL)
- Should use `initial_balance` not current `balance`

---

### 1.8 Risk Reward

| Mode | Current Source | Location | Formula |
|------|---------------|----------|---------|
| **PAPER** | Not exposed | — | Not calculated |
| **LIVE** | Not exposed | — | Not calculated |
| **Audit** | Backend | `execution_metrics.py:154` | `compute_intended_risk_reward()` exists but not used in API |

**Status:** ⚠️ Function exists but not exposed  
**Issue:** Backend has risk/reward calculation in audit module, but positions API doesn't include it

---

## 2. API Endpoint Analysis

### 2.1 PAPER Mode Endpoints

#### GET `/api/paper/account/live`
**Source:** `ml_service/services/market_state_service.py:110`

**Returns:**
```python
{
    "balance": float,           # ✅ Authoritative
    "equity": float,            # ✅ Authoritative (balance + unrealized)
    "unrealized_pnl": float,    # ✅ Authoritative
    "available_balance": float  # ✅ Authoritative (= balance)
}
```

**Missing:**
- `margin_used`
- `margin_ratio`
- `account_health`
- `total_return_pct`
- `initial_balance`

---

#### GET `/api/paper/account`
**Source:** `ml_service/trading/paper_broker.py:976`

**Returns:**
```python
{
    "balance": float,
    "equity": float,
    "unrealized_pnl": float,
    "updated_at": timestamp
}
```

**Missing:** Same as above

---

### 2.2 LIVE Mode Endpoints

#### GET `/api/account/equity`
**Source:** `ml_service/data/exchange_sync.py:716`

**Returns:**
```python
{
    "wallet_balance": float,     # ✅ From Binance
    "unrealized_pnl": float,     # ✅ From Binance
    "margin_balance": float,     # ✅ From Binance (= equity)
    "available_balance": float,  # ✅ From Binance
    "source": "binance"
}
```

**Missing:**
- `margin_used`
- `margin_ratio`
- `account_health`
- `total_return_pct`
- `initial_balance`

---

#### GET `/api/positions/open`
**Source:** `ml_service/api/routes.py:382`

**Returns:**
```python
{
    "positions": [...],
    "total_unrealized_pnl": float,
    "count": int
}
```

**Position fields:**
- `symbol`, `side`, `position_amt`, `entry_price`, `mark_price`, `unrealized_pnl`
- `take_profit`, `stop_loss`, `leverage`

**Missing per position:**
- `risk_reward`
- `margin` (position margin)

---

## 3. Frontend Calculation Locations

### 3.1 PortfolioOverview.tsx

**File:** `components/terminal/PortfolioOverview.tsx`

**Lines 22-24:**
```typescript
const marginRatio = equity > 0 ? (marginUsed / equity) * 100 : 0;
const accountHealth = equity > 0 ? Math.min(100, (freeMargin / equity) * 100) : 0;
const totalReturn = balance > 0 && equity > 0 ? ((equity - balance) / balance) * 100 : 0;
```

**Issue:**
- Frontend computes three financial metrics client-side
- `totalReturn` incorrectly uses `balance` as denominator (should be `initial_balance`)

---

### 3.2 terminalService.ts

**File:** `lib/services/terminalService.ts`

**Lines 100-101:**
```typescript
const margin_used = equity > 0 ? equity - available_balance : 0;
const free_margin = available_balance;
```

**Issue:**
- Normalizer computes `margin_used` because backend doesn't provide it
- This is the translation layer — acceptable IF backend provides the data
- Currently backend doesn't provide `margin_used`, so this is a workaround

---

## 4. Missing Backend Data

### 4.1 Account-Level Metrics

**Not provided by any backend endpoint:**

1. **initial_balance** — Starting capital for return % calculation
2. **margin_used** — Current margin in use
3. **margin_ratio** — `(margin_used / equity) * 100`
4. **account_health** — Free margin percentage
5. **total_return_pct** — `((equity - initial_balance) / initial_balance) * 100`
6. **realized_pnl** — Total realized PnL (PAPER has it, LIVE doesn't expose it)
7. **daily_pnl** — Change in equity since start of day

---

### 4.2 Position-Level Metrics

**Not provided by position endpoints:**

1. **risk_reward** — Reward/Risk ratio per position
2. **margin** — Margin allocated to this position (LIVE has it, PAPER doesn't)
3. **duration_hours** — How long position has been open (PAPER has it for live endpoint)

---

## 5. Data Consistency Issues

### 5.1 Initial Balance Problem

**PAPER Mode:**
- Starts with `STARTING_BALANCE = 10000.0`
- After first winning trade: `balance = 10050.0`
- Frontend calculates return as: `((equity - balance) / balance) * 100`
- This gives return relative to CURRENT balance, not STARTING balance
- **Incorrect:** Should use `initial_balance = 10000.0` as denominator

**LIVE Mode:**
- `live_metrics.py` has `get_starting_balance()` that resolves from config
- But this is only used for analytics, not exposed in account endpoint

---

### 5.2 Margin Calculation Inconsistency

**PAPER Mode:**
- `available_balance = balance` (simplified, no margin system)
- Frontend computes `margin_used = equity - available_balance = equity - balance = unrealized_pnl`
- **This is WRONG for paper trading** — paper doesn't use margin

**LIVE Mode:**
- Binance provides `availableBalance` directly
- `margin_used = margin_balance - available_balance` would be correct
- But backend doesn't expose `margin_balance` as `equity` in normalized form

---

### 5.3 Equity Naming Confusion

**PAPER endpoints return:**
- `equity` (balance + unrealized)
- `balance` (realized wallet)

**LIVE endpoint returns:**
- `margin_balance` (wallet + unrealized) ← This IS equity
- `wallet_balance` (realized wallet) ← This IS balance

**Frontend normalizer:**
```typescript
const equity = Number(backend.equity || backend.account?.equity) || 0;
const balance = Number(backend.balance || backend.account?.balance) || 0;
```

Works, but the LIVE endpoint should rename `margin_balance` → `equity` for consistency.

---

## 6. Risk Reward Implementation Gap

**Backend has the function:**
- `ml_service/audit/execution_metrics.py:154` — `compute_intended_risk_reward()`
- Computes `reward`, `risk`, `risk_reward_ratio`

**But:**
- Not exposed in position API responses
- Not computed for open positions
- Only used in audit/analytics context

**Should be:**
- Computed per open position
- Returned in `/api/positions/open` and `/api/paper/positions/live`
- Calculated from `entry_price`, `take_profit`, `stop_loss`

---

## 7. Equity Calculation — Source of Truth

### 7.1 PAPER Mode

**Primary:** `paper_broker.py:158` — `calculate_equity()`

```python
def calculate_equity() -> Dict:
    balance = account["balance"]
    
    # Sum unrealized PnL from open positions
    unrealized = sum(
        qty * entry_price * ((price - entry_price) / entry_price)
        for position in open_positions
    )
    
    equity = balance + unrealized
    return {"balance": balance, "equity": equity, "unrealized_pnl": unrealized}
```

**Live variant:** `market_state_service.py:110` — `get_live_account_equity()`

Uses live mark prices instead of cached `current_price`.

---

### 7.2 LIVE Mode

**Primary:** Binance API `/fapi/v2/account`

```python
# exchange_sync.py:716
wallet_balance = account.get('totalWalletBalance')      # Realized
unrealized_pnl = account.get('totalUnrealizedProfit')   # Unrealized
margin_balance = account.get('totalMarginBalance')      # Wallet + Unrealized
```

`margin_balance` is the equity.

---

## 8. Recommended Normalization

### 8.1 Single Normalized Account Schema

**Backend should return (all modes):**

```python
{
    # Core balances
    "initial_balance": float,      # Starting capital
    "wallet_balance": float,       # Current realized balance
    "equity": float,               # Wallet + unrealized
    "available_balance": float,    # Free to use
    "margin_used": float,          # Currently in positions
    
    # PnL metrics
    "unrealized_pnl": float,       # Open positions
    "realized_pnl": float,         # Closed positions total
    "daily_pnl": float,            # Today's change
    
    # Derived metrics
    "margin_ratio": float,         # (margin_used / equity) * 100
    "account_health": float,       # (free_margin / equity) * 100
    "total_return_pct": float,     # ((equity - initial) / initial) * 100
    
    # Metadata
    "exposure": float,             # Total position value
    "last_updated": str
}
```

---

### 8.2 Single Normalized Position Schema

**Backend should return (all modes):**

```python
{
    "symbol": str,
    "side": str,                   # LONG | SHORT
    "entry_price": float,
    "mark_price": float,
    "quantity": float,
    "margin": float,               # Margin for this position
    
    # PnL
    "unrealized_pnl": float,
    "realized_pnl": float,
    
    # Risk management
    "stop_loss": float | None,
    "take_profit": float | None,
    "risk": float,                 # Distance to SL in $
    "reward": float,               # Distance to TP in $
    "risk_reward": float,          # Reward / Risk ratio
    
    # Metadata
    "confidence": int | None,
    "regime": str | None,
    "duration_hours": float,
    "opened_at": str
}
```

---

## 9. Gaps Summary

### Missing from Backend:

1. **initial_balance** — No API returns this (needed for accurate return %)
2. **margin_used** — Backend doesn't compute/return (LIVE could derive from Binance)
3. **margin_ratio** — Not computed server-side
4. **account_health** — Not computed server-side
5. **total_return_pct** — Not computed server-side
6. **realized_pnl** — LIVE mode doesn't expose total realized PnL in account endpoint
7. **daily_pnl** — Not tracked/exposed
8. **risk_reward** — Exists in audit code but not exposed in position API

### Incorrectly Computed in Frontend:

1. **margin_ratio** — `PortfolioOverview.tsx:22`
2. **account_health** — `PortfolioOverview.tsx:23`
3. **total_return_pct** — `PortfolioOverview.tsx:24` (also uses wrong denominator)
4. **margin_used** — `terminalService.ts:100` (workaround for missing backend data)

---

## 10. Action Items for Sprint 2.2B

### Task 2: Normalize Portfolio Service

1. Create/update service layer to compute all metrics
2. Store `initial_balance` in database (new column in `paper_account`)
3. Compute derived metrics server-side
4. Return normalized account object

### Task 3: Normalize Risk/Return Calculations

1. Expose `risk_reward` calculation in position API
2. Compute `margin_ratio`, `account_health`, `total_return_pct` server-side
3. Return these in account endpoint

### Task 4: Normalize Initial Balance

1. Add `initial_balance` column to `paper_account` table
2. Populate on first run with `STARTING_BALANCE`
3. For LIVE mode, resolve from config and store in database or config service
4. Expose in API response

### Task 5: Normalize Equity Calculation

1. Document equity formula per mode (already correct)
2. Ensure consistency between `calculate_equity()` and `get_live_account_equity()`
3. Map LIVE `margin_balance` → `equity` in API response

### Task 6: Normalize Risk Reward Calculation

1. Import `compute_intended_risk_reward()` into position endpoints
2. Compute for each open position
3. Add `risk`, `reward`, `risk_reward` to position response schema

### Task 7: Normalize Account Health Calculation

1. Add account health computation to service layer
2. Formula: `(available_balance / equity) * 100`
3. Return in account endpoint

### Task 8: Update API Contracts

1. Update `/api/paper/account/live` response schema
2. Update `/api/account/equity` response schema (LIVE)
3. Update `/api/positions/open` to include risk/reward per position
4. Ensure backward compatibility or version API

### Task 9: Clean up Frontend Calculations

1. Remove lines 22-24 from `PortfolioOverview.tsx`
2. Update `terminalService.ts` normalizer to pass through backend values
3. Remove margin_used calculation workaround
4. Frontend should only render, not compute

### Task 10: Validation

1. Verify PAPER mode: metrics match between old and new
2. Verify LIVE mode: metrics match Binance values
3. Test OFF mode: returns zeros gracefully
4. Build passes
5. Run backend tests

---

## 11. Technical Debt

1. **Hardcoded initial balance** — Should come from config or database
2. **No margin system in PAPER mode** — Simplification means `margin_used` doesn't apply
3. **LIVE mode missing aggregated realized PnL** — Must query `user_trade_history` separately
4. **Equity snapshots vs live equity** — Two different systems (history vs current)
5. **Risk/reward only in audit code** — Should be core position attribute

---

## Conclusion

**Current State:**
- Backend provides raw data (equity, balance, unrealized PnL)
- Frontend computes derived metrics (margin ratio, account health, return %)
- Risk/reward calculations exist but aren't exposed
- Initial balance is hardcoded, not stored

**Target State:**
- Backend computes ALL financial metrics
- Frontend receives complete, normalized account + position objects
- ONE authoritative formula per metric
- Initial balance stored and tracked properly

**Blocker for Normalization:**
- Need to add `initial_balance` to database schema
- Need to create service layer for derived metric computation
- Need to expose risk/reward in position API

**No breaking changes required for existing endpoints — can extend response schemas.**
