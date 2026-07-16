# Frontend-Backend Contract Audit Report

**Date:** 2026-07-16  
**Auditor:** Antigravity (Governance, Audits & Design)  
**Target:** MoroQuant Institutional Terminal Dashboard Frontend vs FastAPI Backend  

---

## 1. Overview & Executive Summary

This audit compares the frontend MoroQuant Institutional Terminal components against the active FastAPI endpoints in the backend service layer (`ml_service/api/routes.py`). 

Out of **10 monitored dashboard actions/endpoints**:
- **7 endpoints** exist and match the schema perfectly.
- **3 endpoints** exist but have schema mismatches (nested vs. flat discrepancies and missing fields).
- **0 endpoints** are entirely missing.

The terminal UI currently shows default/empty state values (like `-` or `$0.00`) for account equity, balance, unrealized PnL, and model execution quality due to these schema contract mismatches. No UI code implementation changes are made in this phase, as per MoroQuant Governance policies.

---

## 2. API Endpoint Audit Matrix

| Component | API Function | Target Endpoint | Status | Issues Identified |
| :--- | :--- | :--- | :---: | :--- |
| **TradingModeSwitch** | `getTradingMode` <br> `setTradingMode` | `GET /api/trading/mode` <br> `POST /api/trading/mode` | ✅ Exists | None. |
| **EmergencyStopButton** | `emergencyStop` | `POST /api/trading/emergency-stop` | ✅ Exists | None. |
| **InstitutionalHeader** | `getLivePaperAccount` | `GET /api/paper/account/live` | ⚠️ Wrong Schema | Nested vs. Flat mismatch & missing field. |
| **PortfolioOverview** | `getLivePaperAccount` | `GET /api/paper/account/live` | ⚠️ Wrong Schema | Nested vs. Flat mismatch & missing field. |
| **OpenPositionsTable** | `getLivePaperPositions` | `GET /api/paper/positions/live` | ✅ Exists | None. |
| **RecentTradesPanel** | `getPaperClosedPositions` | `GET /api/paper/positions/closed` | ✅ Exists | None. |
| **EquityCurve** | `getPaperEquityHistory` | `GET /api/paper/equity-history` | ✅ Exists | None. |
| **ModelIntelligence** | `getExecutionAnalytics` <br> `getPaperResearchSummary` | `GET /api/paper/analytics/execution` <br> `GET /api/paper/analytics/summary` | ⚠️ Wrong Schema <br> ✅ Exists | Nested vs. Flat mismatch on execution analytics. |
| **PerformanceStats** | `getPaperAnalytics` | `GET /api/paper/analytics` | ✅ Exists | None. |
| **StatusBar** | `getTradingMode` | `GET /api/trading/mode` | ✅ Exists | None. |

---

## 3. Detailed Mismatch Analysis

### 3.1. Endpoint: `GET /api/paper/account/live`
Used by: `InstitutionalHeader` and `PortfolioOverview`

#### A. Backend Response Structure (Actual)
The backend returns a flat dictionary with account fields directly at the root, along with metadata:
```json
{
  "balance": 10000.0,
  "equity": 10000.0,
  "unrealized_pnl": 0.0,
  "available_balance": 10000.0,
  "status": "success",
  "timestamp": "2026-07-16T13:23:42.123456"
}
```

#### B. Frontend Expectation (Expected)
The frontend components read fields nested under `.account`, and expect a `daily_pnl` field:
```typescript
// In InstitutionalHeader.tsx & PortfolioOverview.tsx
const account = accountData?.account; 
const dailyPnL = accountData?.daily_pnl || 0; // Read directly from root
```
Expected typescript schema representation:
```typescript
interface LivePaperAccountResponse {
  account: {
    balance: number;
    equity: number;
    unrealized_pnl: number;
    available_balance: number;
  };
  daily_pnl: number; // Mismatch: completely missing in backend response
}
```

#### C. Contract Gap
1. **Nested vs. Flat:** Backend returns balance/equity at the root level; frontend expects them under an `account` object key.
2. **Missing Field:** `daily_pnl` is required by the UI to show daily gains/losses, but is absent from the backend service response.

---

### 3.2. Endpoint: `GET /api/paper/analytics/execution`
Used by: `ModelIntelligence`

#### A. Backend Response Structure (Actual)
The backend wraps execution analytics data in a nested `"execution"` key:
```json
{
  "status": "success",
  "execution": {
    "total_trades": 12,
    "avg_eqs": 0.85,
    "avg_mae": 0.015,
    "avg_mfe": 0.045,
    "avg_lost_opportunity": 0.01,
    "avg_profit_capture": 0.65,
    "avg_hold_hours": 4.5,
    "trailing_activated": 2,
    "break_even_saves": 1,
    "avg_sl_moves": 1.2,
    "additional_profit_saved": 150.0,
    "exit_reasons": {
      "TP_HIT": 8,
      "SL_HIT": 4
    }
  },
  "timestamp": "2026-07-16T13:23:42.123456"
}
```

#### B. Frontend Expectation (Expected)
The frontend component expects the fields of `ExecutionAnalytics` to be flat at the root of the query response:
```typescript
// In ModelIntelligence.tsx
const eqs = executionData?.avg_eqs || 0;
```
Expected typescript schema:
```typescript
interface ExecutionAnalytics {
  total_trades: number;
  avg_eqs: number;
  avg_mae: number;
  avg_mfe: number;
  avg_lost_opportunity: number;
  avg_profit_capture: number;
  avg_hold_hours: number;
  trailing_activated: number;
  break_even_saves: number;
  avg_sl_moves: number;
  additional_profit_saved: number;
  exit_reasons: Record<string, number>;
}
```

#### C. Contract Gap
1. **Nested vs. Flat:** Backend nests the stats under the `"execution"` object key, whereas the frontend reads them directly from the root response. This leads to `avg_eqs` resolving to `undefined` (resulting in a 0% Execution Quality display).

---

## 4. Recommendations & Fix Action Plans

To align the API contracts without modifying presentation layers:

1. **Option A (Backend Fix):** Modify `ml_service/api/routes.py`:
   - Adjust `GET /api/paper/account/live` to return `{"account": account_dict, "daily_pnl": daily_pnl_value}`.
   - Adjust `GET /api/paper/analytics/execution` to return the fields of `ExecutionAnalytics` at the root level, or map the service function accordingly.
2. **Option B (Frontend Fix):** Update the UI components or the service/client layer:
   - Adjust components `InstitutionalHeader.tsx` and `PortfolioOverview.tsx` to handle flat root-level parameters.
   - Adjust component `ModelIntelligence.tsx` to read `executionData?.execution?.avg_eqs`.
