# Sprint 3 Testing Plan — Observability & Explainability

This document details the test strategy, mock designs, and verification requirements for Sprint 3.

---

## 1. Unit Testing Strategy

All new backend scripts must be fully unit tested under `ml_service/tests/`.

### Test 1: Feature Extraction Normalization (`test_explainability.py`)
- **Objective:** Verify that the `ExplainabilityService` correctly reads booster importances.
- **Scenario:** Mock a model booster returning arbitrary gain scores `{feat_1: 15.0, feat_2: 35.0}`.
- **Verification:** Assert returned relative weights are `feat_1: 0.3` and `feat_2: 0.7` (sums to 1.0).

### Test 2: Telegram Notifier Payload (`test_telegram.py`)
- **Objective:** Verify that the notifier correctly handles requests without blocking threads.
- **Scenario:** Mock the API endpoint using `pytest-mock` or `unittest.mock`.
- **Verification:** Ensure calling `send_alert()` invokes `httpx.post` with the correct JSON payload format. Verify errors (such as HTTP 500 from Telegram API) are caught and logged without raising exceptions.

### Test 3: Explainability Endpoint (`test_api_explain.py`)
- **Objective:** Verify that `/signals/{id}/explain` returns the expected schema.
- **Scenario:** Populate a test SQLite DB with a dummy signal and mock the file reader for models.
- **Verification:** Query `/signals/1/explain` and assert a 200 OK status code, with matching keys in JSON.

---

## 2. Frontend & Integration Testing

### Jest and React Testing Library
- **File:** `__tests__/TradeExplorer.test.tsx`
- **Objective:** Verify the table displays rows and opens the explanation drawer.
- **Scenario:** Mock the backend JSON response. Render the `TradeExplorer` component.
- **Verification:**
  - Expect rows for BTCUSDT and ETHUSDT to be visible.
  - Fire a click event on the first row.
  - Assert the Recharts canvas or mock representation is rendered.

---

## 3. Pre-merge Verification (Manual Check)

Before pushing the PR:
1. Ensure the Telegram Bot token works on a test channel.
2. Verify that there are no leakages of token values in runtime log files.
3. Validate that the Next.js production build passes with `npm run build`.
