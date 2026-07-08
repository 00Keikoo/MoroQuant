# Architecture Decision Records (ADR) — Sprint 3.x

## ADR-010: Dynamic Repository Column Extraction

### Context
In Sprint 3.x, the introduction of calibration metrics, probabilities, and regime classifications added several new columns to the `signals` table. The existing repository implementation selected a hardcoded subset of 8 fields. Replay engine runs collapsed to default values since probabilities were lost during loading.

### Decision
Update `SignalRepository` to dynamically inspect the SQLite schema using `PRAGMA table_info` when querying. We dynamically fetch available columns and map them to optional properties of the `Signal` dataclass.

### Status
Accepted

### Consequences
- Retains full backward compatibility with test/mock database schemas (which only define basic tables).
- Eliminates field loss from database query mappings.

---

## ADR-011: Unified Decision Truth Layer

### Context
To prevent diverging heuristics between production systems, replay engines, and backtest experiments, we need a single source of truth for trading logic.

### Decision
Extract decision logic out of the replay engine and place it inside a unified `DecisionEngine` module. All engines (Replay, Experiment, Evaluation) must import this module and use `DecisionEngine.decide(context)`.

### Status
Accepted

### Consequences
- Eliminates decision divergence due to custom heuristics in backtests.
- Forces confidence threshold evaluations to be identical to production.
