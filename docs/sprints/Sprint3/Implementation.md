# Sprint 3 Implementation Guide — Observability & Explainability

This document provides developers with step-by-step instructions on where to modify code, add files, and configure settings.

---

## 1. Environment & Configuration Setup

Update `ml_service/config.example.yaml` and `config.yaml`:
```yaml
notifications:
  telegram:
    enabled: true
    bot_token: "YOUR_TELEGRAM_BOT_TOKEN"
    chat_id: "YOUR_TELEGRAM_CHAT_ID"
```

*Note: In production environments, ensure these are injected as environment variables (`TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`) to adhere to [Engineering Principles](file:///home/zafka/trade-dashboard/docs/ENGINEERING_PRINCIPLES.md).*

---

## 2. Backend Implementation Steps

### Step 2.1: Explainability Module
Create a new file `ml_service/analytics/explainability.py`:
- Import `xgboost` and `lightgbm` dynamically to prevent issues if one is missing.
- Parse the model's booster structure:
  - **XGBoost:** `model.get_booster().get_score(importance_type='gain')`
  - **LightGBM:** `model.booster_.feature_importance(importance_type='gain')`
- Normalize the raw values so the sum equals 1.0.

### Step 2.2: API Route Additions
In `ml_service/api/main.py` (or routing files):
- Define `GET /signals/{signal_id}/explain`.
- Fetch the signal details from SQLite database.
- Read the corresponding `.json`/`.bin` model file from `storage/models/`.
- Call `ExplainabilityService` to compute relative feature importances.
- Return HTTP 404 if either database record or model file is absent.

### Step 2.3: Telegram Notifier Daemon
Create `ml_service/analytics/telegram_notifier.py`:
- Use `httpx` or `urllib.request` to send asynchronous POST requests.
- Wrap requests in try-except blocks to prevent third-party API issues from blocking model predictions.

---

## 3. Frontend Implementation Steps

### Step 3.1: Explorer Page Component
Create a page component `app/trading/explorer/page.tsx`:
- Utilize Next.js `useEffect` to poll `GET /analytics/trade-history`.
- Render a data table using CSS grid layouts (styled matching the custom dashboard layout).
- Column headers: Time, Symbol, Timeframe, Direction, Confidence, Outcome, PnL (%).

### Step 3.2: Recharts Drawer
- Import `BarChart`, `Bar`, `XAxis`, `YAxis`, `Tooltip` from `recharts`.
- When an explorer table row is clicked, fetch the `/signals/{id}/explain` data.
- Open a right-hand drawer display with horizontal bars representing features, colored green for positive contribution and blue/red for others.
