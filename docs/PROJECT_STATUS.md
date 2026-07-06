# MoroQuant Project Status

## Current Status

- **Version:** [v0.3.0](file:///home/zafka/trade-dashboard/VERSION.md)
- **Current Phase:** Engineering Foundation (Sprint 2.5)
- **Current Sprint:** [Sprint 2.5 — Engineering Foundation](file:///home/zafka/trade-dashboard/docs/sprints/Sprint3/README.md) (transitioning to Sprint 3)
- **Project Health:** 🟢 Healthy

---

## Roadmap & Sprints

For a detailed view of future development, see the [Product Roadmap](file:///home/zafka/trade-dashboard/docs/roadmap/ROADMAP.md).

### Sprint Progress

- **Sprint 0 — Research**
  - Status: ✅ Completed
  - Deliverables: Market regimes research, model prototyping, database design.
- **Sprint 1 — Production ML**
  - Status: ✅ Completed
  - Deliverables: Feature engineering pipeline, XGBoost/LightGBM model training with walk-forward validation, Optuna hyperparameter tuning.
- **Sprint 2 — Autonomous Paper Trading**
  - Status: ✅ Completed
  - Deliverables: Paper trading lifecycle engine, Binance Futures synchronization, performance summary layer (`model_performance_summary`).
- **Sprint 2.5 — Engineering Foundation**
  - Status: 🚧 In Progress (Current)
  - Deliverables: System documentation hierarchy, engineering principles, Sprint 3 specifications.
- **Sprint 3 — Observability & Explainability**
  - Status: ⬜ Not Started (Up Next)
  - Deliverables: Trade Explorer dashboard, feature importance visibility, real-time alerting system. See [Sprint 3 Overview](file:///home/zafka/trade-dashboard/docs/sprints/Sprint3/README.md).
- **Sprint 4 — Risk Engine**
  - Status: ⬜ Planned
- **Sprint 5 — Portfolio Optimization**
  - Status: ⬜ Planned
- **Sprint 6 — Autonomous Live Trading**
  - Status: ⬜ Planned

---

## Active Daemons & Production Services

The paper trading infrastructure is currently running in simulated production:

| Service / Daemon | Status | Health / Metrics |
|------------------|--------|------------------|
| **Binance WebSockets** | 🟢 Running | Real-time prices ingestion active |
| **Signal Generator** | 🟢 Running | Generates signals on 1h and 4h intervals |
| **Paper Lifecycle Engine** | 🟢 Running | Monitors and resolves entry, TP, SL, and timeouts |
| **Adaptive Retraining** | 🟢 Running | Models scheduled to retrain daily |
| **Performance Tracker** | 🟢 Running | Live updating of `model_performance_summary` |

---

## Next Milestone

**Sprint 3: Trade Explorer**
- Establish a frontend analytics panel detailing current positions, historical performance, confidence metrics, and regime breakdowns.
- Implement explainability features (e.g., displaying feature importances on the dashboard).
