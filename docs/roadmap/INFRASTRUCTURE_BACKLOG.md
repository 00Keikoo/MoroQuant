# MoroQuant Infrastructure Backlog

This backlog tracks internal technical debt, database optimizations, deployment scripts, and performance-related engineering enhancements.

---

## 1. High Priority (Sprint 3 & 4 Target)

### INF-001: Centralized Structured Logging & Alerting
- **Description:** Replace standard standard-out prints in `ml_service` with a structured JSON logging system (e.g., using `loguru` or Python's standard `logging` config).
- **Technical Value:** Easier parsing of backtest logs, scheduler runs, and trade execution events.
- **Status:** Backlog (Sprint 3)
- **Estimates:** Small

### INF-002: Reconnection Resiliency for Binance WebSockets
- **Description:** Implement robust heartbeat monitoring and auto-reconnection with exponential backoff for the Binance WebSocket client.
- **Technical Value:** Prevents missing price updates due to network drops or temporary exchange disconnects.
- **Status:** Backlog (Sprint 3)
- **Estimates:** Medium

### INF-003: SQLite Migration to PostgreSQL (Optional but planned)
- **Description:** Abstract the database layer with SQLAlchemy or raw SQL parameters to easily switch between SQLite (development) and PostgreSQL (production).
- **Technical Value:** Better concurrency support for parallel model training and multiple real-time WebSocket listeners.
- **Status:** Backlog (Sprint 4)
- **Estimates:** Large

---

## 2. Medium Priority (Sprint 5 & 6 Target)

### INF-004: Dockerization of Services
- **Description:** Create a `docker-compose.yml` defining the Next.js frontend and Python FastAPI backend, including volume mounts for storage.
- **Technical Value:** Ensures identical development and production environments, simplifying deployment.
- **Status:** Planned
- **Estimates:** Small

### INF-005: Automated Walk-Forward Training Parallelization
- **Description:** Use multiprocessing in Python (`concurrent.futures` or joblib) to parallelize model training across symbols.
- **Technical Value:** Decreases walk-forward training time for all 11 pairs from ~30 minutes to under 5 minutes.
- **Status:** Planned
- **Estimates:** Medium

### INF-006: Sentry Exception Monitoring
- **Description:** Integrate Sentry SDK into FastAPI backend and Next.js frontend.
- **Technical Value:** Instant error notification on unhandled exceptions in daemon runtimes.
- **Status:** Planned
- **Estimates:** Small

---

## 3. Low Priority (Sprint 7+ Target)

### INF-007: Rust execution engine integration
- **Description:** Port the low-latency parts of trade tracking, tick aggregation, and limit order placement to a Rust module linked via PyO3.
- **Technical Value:** Drastically reduces order execution latency and event processing overhead.
- **Status:** Proposed
- **Estimates:** Extra Large
