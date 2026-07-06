# MoroQuant Product Roadmap

This roadmap details the past sprints, current milestone, and future vision of the MoroQuant automated trading platform.

---

## Completed Milestones

- **Sprint 0 — Research & Prototyping**
  - ✅ Literature review of market regime models
  - ✅ Prototyped features calculations (EMA, ADX, Bollinger, Volume Profile)
  - ✅ Designed initial SQLite database schema for candles and signals

- **Sprint 1 — Production Machine Learning**
  - ✅ Implemented the `ml_service/features/` pipeline with 30+ technical indicators
  - ✅ Built walk-forward validation model trainer (`trainer.py`) supporting XGBoost and LightGBM
  - ✅ Integrated Bayesian hyperparameter optimization via Optuna (`tuner.py`)

- **Sprint 2 — Autonomous Paper Trading**
  - ✅ Built paper trading lifecycle engine tracking Entry, TP, SL, and timeouts
  - ✅ Implemented Binance Futures data and trade synchronization (`exchange_sync.py`)
  - ✅ Created a pre-computed model performance summary layer (`model_performance_summary`) with unit test coverage

- **Sprint 2.5 — Engineering Foundation (Current)**
  - 🚧 Established the documentation hierarchy, engineering principles, and Sprint 3 architectural blueprints.

---

## Upcoming Sprints

### Sprint 3 — Observability & Explainability (Up Next)
- **Goal:** Provide detailed insights into live performance and model decisions.
- **Key Features:**
  - Trade Explorer Dashboard frontend.
  - Model feature importance visibility.
  - Multi-timeframe confirmation analytics.
  - Real-time alert notifications (Telegram channel).

### Sprint 4 — Risk Engine
- **Goal:** Protect trading capital against extreme market regimes and anomalies.
- **Key Features:**
  - Maximum daily drawdown limits.
  - Dynamic position sizing (e.g., Kelly Criterion, volatility-adjusted sizing).
  - Multi-pair correlation checks to avoid overexposure.

### Sprint 5 — Portfolio Optimization
- **Goal:** Allocate capital dynamically across the 11 target cryptocurrency pairs.
- **Key Features:**
  - Mean-Variance or risk-parity optimization.
  - Dynamic leverage management.
  - Regime-based allocation adjustment.

### Sprint 6 — Autonomous Live Trading
- **Goal:** Enable live execution with real capital on Binance Futures.
- **Key Features:**
  - Live execution broker adapter.
  - Slippage and latency tracking.
  - Automatic order retry and error reconciliation.
  - Hard kill-switch configuration.
