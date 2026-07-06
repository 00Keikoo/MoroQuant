# MoroQuant Engineering Principles

This document outlines the core technical and architectural principles guiding the development of the MoroQuant algorithmic trading intelligence platform.

---

## 1. Simplicity & Minimalism First
- **YAGNI (You Aren't Gonna Need It):** Implement only the minimum code required to satisfy the immediate requirements. Avoid speculative abstractions or writing features for future use.
- **Surgical Changes:** Make target-oriented, atomic changes. Do not refactor adjacent code that is unrelated to the immediate task or bug fix.
- **Readability Over Cleverness:** Write explicit, easy-to-follow code. If an optimization introduces significant complexity, it must be justified with benchmarks.

## 2. Integrity of the Machine Learning Pipeline
- **Strict Lookahead Bias Prevention:** In feature engineering, model training, and backtesting, absolutely no future information must be leaked. Always use causal filters and walk-forward validation (never simple train-test random splits).
- **Data-Driven Rules:** Prefer empirical, optimized thresholds (e.g., using Optuna for TP/SL levels based on historical Maximum Favorable Excursion and Maximum Adverse Excursion) over arbitrary heuristics.
- **Model Validation:** Never deploy a model without running cross-asset validation and regime robustness validation across all target pairs.

## 3. Reliability and Financial Safety
- **No Direct Live Capital Modifications Without Verification:** All code modifications affecting trade execution, position management, or order routing must be heavily simulated via dry-run and paper trading before interacting with live capital.
- **Robust Exception Handling:** Daemon event loops must fail-safe, catch exceptions gracefully, and trigger alerts rather than crashing silently.
- **State Reconciliation:** The system must treat the exchange API as the ultimate source of truth, periodically reconciling the local SQLite database state with actual exchange state.

## 4. Database & Schema Management
- **Immutable Migration History:** Never alter an existing database migration script. All schema updates must be done using a new, sequentially numbered migration script (e.g., `010_add_some_feature.sql`).
- **Idempotency:** Migrations and table initialization routines must be idempotent, allowing safe executions multiple times without data corruption or failures.

## 5. Security & Secret Management
- **Zero Secrets in Git:** API keys, database credentials, and Webhook URLs must never be hardcoded or checked into source control. Always use environment variables or `.env.local` files, with `config.yaml` containing reference configurations only.
- **Separation of Test/Production Environments:** Test databases, paper trading sandboxes, and production exchanges must be strictly isolated.

## 6. Testing Philosophy
- **Automated Verification:** Any new feature, utility, or database summary view must be backed by a corresponding automated test.
- **Mocking External APIs:** External services (such as the Binance API) must be mocked in unit tests to ensure test suite reliability, speed, and capability to run offline.
- **System Verification Audits:** Periodically audit prediction behavior, signal quality, and execution logic using historical records.
