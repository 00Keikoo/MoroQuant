# Sprint 3 Architecture — Observability & Explainability

This document details the system design, API schemas, and component changes introduced in Sprint 3.

---

## System Diagram

```mermaid
graph TD
    subgraph Frontend (Next.js)
        UI[Trade Explorer Dashboard]
        FE_EXP[Feature Importance Component]
    end

    subgraph Backend (FastAPI)
        API[FastAPI Server]
        EXP_SVC[Explainability Service]
        NOTIF_SVC[Telegram Alert Service]
    end

    subgraph ML Pipeline
        MODEL[XGBoost / LightGBM Model]
        ENGINE[Outcome Engine]
    end

    subgraph Database
        DB[(SQLite database.db)]
    end

    subgraph External
        TG[Telegram Bot API]
    end

    UI -->|Queries trades & signals| API
    FE_EXP -->|Queries feature weights| API
    API -->|Reads data| DB
    API -->|Inspects model| EXP_SVC
    EXP_SVC -->|Extracts split weights/SHAP| MODEL
    ENGINE -->|Triggers trade state updates| NOTIF_SVC
    NOTIF_SVC -->|Posts alerts| TG
```

---

## 1. Explainability Service Design

### Mechanism
- XGBoost and LightGBM provide feature importance natively through tree split gain, cover, and weight metrics.
- The `ExplainabilityService` will load the trained model JSON/BST files and parse `booster.get_score(importance_type='gain')`.
- For any prediction generated, the top 5 features with the highest weights will be stored in the database next to the signal record, or computed on-the-fly when requesting details.

### API Endpoint Schema
`GET /signals/{signal_id}/explain`
- **Response:**
  ```json
  {
    "signal_id": 1042,
    "symbol": "BTCUSDT",
    "prediction": "LONG",
    "confidence": 0.78,
    "top_features": [
      { "name": "volume_profile_poc_distance", "importance": 0.284 },
      { "name": "rsi_14_1h", "importance": 0.192 },
      { "name": "funding_rate_change_24h", "importance": 0.155 },
      { "name": "ema_cross_9_21", "importance": 0.113 },
      { "name": "regime_adx_trend_strength", "importance": 0.082 }
    ]
  }
  ```

---

## 2. Telegram Alerting Service Design

### Mechanism
- A class `TelegramAlertService` (found in `ml_service/analytics/telegram_notifier.py`) will be instantiated on server start.
- Hooked directly into:
  - `Predictor.generate_signal()` -> Alert generated signals.
  - `OutcomeEngine.save_outcome()` -> Alert entry, target hit (TP), stop hit (SL), and timeouts.
- Run asynchronously in a background task to prevent slowing down the main execution flow or API response times.

### Payload Schema
```text
🔔 [MoroQuant Signal] LONG BTCUSDT
Timeframe: 1h
Confidence: 78%
Entry Zone: $56,430 - $56,600
Target (TP): $58,200 (ATR Multiplier: 3.0x)
Stop Loss (SL): $55,600 (ATR Multiplier: 1.5x)
Market Regime: Trending High Volatility
Top Feature: volume_profile_poc_distance (28.4% weight)
```

---

## 3. Trade Explorer UI Design

The Trade Explorer will be integrated under the `/trading` or `/trades` path in the Next.js app:
- **Filters:** Active trades, closed trades, symbol, timeframe, outcome (Win, Loss, Timeout).
- **Interactive Component:** Clicking on any row opens a drawer/modal showing the feature importance bar chart (using Recharts) and the multi-timeframe alignment scores.
