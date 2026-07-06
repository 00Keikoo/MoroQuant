# Sprint 3 Backlog — Observability & Explainability

This document details the prioritised tasks, user stories, and estimation breakdown for Sprint 3.

---

## Sprint Backlog Table

| Task ID | Component | Title | Priority | Estimate (Story Points) | Status |
|---------|-----------|-------|----------|-------------------------|--------|
| **S3-1** | Backend | Feature Importance Extraction Service | High | 3 | ⬜ Not Started |
| **S3-2** | Backend | Explainability Endpoint (`/signals/{id}/explain`) | High | 2 | ⬜ Not Started |
| **S3-3** | Backend | Telegram Alert Service | High | 3 | ⬜ Not Started |
| **S3-4** | Backend | Hook Alert Service into Predictor & Outcome Engine | Medium | 2 | ⬜ Not Started |
| **S3-5** | Frontend | Trade Explorer Page (`/trades/explorer`) | High | 5 | ⬜ Not Started |
| **S3-6** | Frontend | Feature Importance Bar Chart Component | Medium | 3 | ⬜ Not Started |

---

## Task Details

### S3-1: Feature Importance Extraction Service
- **Goal:** Extract split gain/weight variables from trained models (`.json` or `.bin`).
- **Acceptance Criteria:**
  - Able to load models of both types (XGBoost & LightGBM).
  - Normalizes values to sum to 1.0 (relative percentage importance).
  - Gracefully handles missing model files.

### S3-2: Explainability Endpoint
- **Goal:** Expose the relative feature weights for any historical or current signal.
- **Acceptance Criteria:**
  - Returns a list of key-value pairs sorted in descending order of weight.
  - Return HTTP 404 if the signal or corresponding model file is missing.

### S3-3: Telegram Alert Service
- **Goal:** Core integration code to dispatch HTTP POST requests to `https://api.telegram.org/bot<Token>/sendMessage`.
- **Acceptance Criteria:**
  - Loads chat ID and Bot token safely from configuration.
  - Throttles and buffers messages under heavy volume.
  - Non-blocking execution using `asyncio` or background threads.

### S3-4: Hook Alerts to Core Engine
- **Goal:** Fire notifications during critical lifecycle states.
- **Acceptance Criteria:**
  - Signal generated -> Telegram alert.
  - Position entered -> Telegram alert.
  - Position closed (TP / SL / Timeout) -> Telegram alert with final PnL.

### S3-5: Trade Explorer Page
- **Goal:** Build the Next.js explorer UI listing open and closed trades.
- **Acceptance Criteria:**
  - Integrates with Next.js App Router under `/trades`.
  - Filterable by Symbol, Timeframe, Status (Win, Loss, Timeout).
  - Responsive table layout styled with CSS variables (matching the theme).

### S3-6: Feature Importance Bar Chart
- **Goal:** Render a visual explanation of why a trade was taken.
- **Acceptance Criteria:**
  - Uses Recharts to show top 5 contributing indicators.
  - Opens in a sidebar drawer when a row in the Trade Explorer is clicked.
