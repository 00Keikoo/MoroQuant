# MoroQuant Product Backlog

This backlog lists the user-facing features, trading intelligence capabilities, and analysis tools planned for MoroQuant, prioritized by value.

---

## 1. High Priority (Sprint 3 & 4 Target)

### PB-001: Trade Explorer Dashboard
- **Description:** A comprehensive frontend UI to track, filter, and inspect open and closed trades.
- **User Value:** Users can view the exact state of active paper/live trades, and see why they were opened (attributed signal, confidence, regime).
- **Status:** Backlog (Sprint 3)
- **Estimates:** Medium

### PB-002: Real-time Telegram Notifications
- **Description:** Push notifications to a Telegram channel for new signal generation, trade entries, and trade exits (TP/SL/Timeout).
- **User Value:** Allows real-time monitoring of the system's decisions without having to keep the dashboard web page open.
- **Status:** Backlog (Sprint 3)
- **Estimates:** Small

### PB-003: Model Explainability View (Feature Importance)
- **Description:** Expose the top 5 contributing features for every signal on the UI, displaying SHAP or XGBoost split-gain feature importances.
- **User Value:** Demystifies predictions, showing if the model entered a trade due to a volume profile spike, trend-following indicators, or market regime.
- **Status:** Backlog (Sprint 3)
- **Estimates:** Medium

### PB-004: Dynamic Risk Controls & Sizing UI
- **Description:** Dashboard controls to configure the Risk Engine, set maximum allowable drawdowns, and configure sizing algorithms.
- **User Value:** Ensures capital protection and provides interactive overrides for safety.
- **Status:** Backlog (Sprint 4)
- **Estimates:** Medium

---

## 2. Medium Priority (Sprint 5 & 6 Target)

### PB-005: Portfolio Optimization Panel
- **Description:** UI tool to view how capital is allocated among the 11 crypto assets (BTC, ETH, BNB, etc.) based on recent covariance and performance.
- **User Value:** Optimizes reward-to-risk ratio across the entire portfolio.
- **Status:** Planned
- **Estimates:** Large

### PB-006: Backtest Interactive Visualizer
- **Description:** Enhance the current static backtest summary with interactive chart zooming, drawdowns analysis, and comparison curves.
- **User Value:** Allows quant researchers to inspect backtest equity lines dynamically.
- **Status:** Planned
- **Estimates:** Medium

### PB-007: Sentiment Indicator Pipeline
- **Description:** Integrate CoinGecko, Twitter, or news APIs to compute a market sentiment indicator, adding it as a feature to the models.
- **User Value:** Enhances signal quality during news-driven trends.
- **Status:** Planned
- **Estimates:** Large

---

## 3. Low Priority (Future)

### PB-008: Multi-Exchange Execution Dashboard
- **Description:** UI to view and control order execution across multiple exchanges (e.g., Binance, Bybit, OKX).
- **User Value:** Spreads risk and handles liquidity constraints across platforms.
- **Status:** Proposed
- **Estimates:** Extra Large
