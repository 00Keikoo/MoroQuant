# Research Overlay Architecture

This document describes the design, dependency structure, modules, and sequence lifecycles of the Research Overlay System.

## 1. System Architecture

```mermaid
graph TD
    subgraph Production Inference Pipeline
        MD[Market Data: OHLCV] --> FE[Feature Engineering]
        FE --> ML[ML Model Ensemble]
        ML --> PR[Prediction / Proba]
        PR --> CAL[Calibration Filter]
        CAL --> SIG[Signal Creation]
        SIG --> DB[(SQLite Database)]
        SIG --> PB[Paper Broker]
        PB --> POS[(Positions Database)]
    end

    subgraph Research Overlay System
        DB --> SNAP[Snapshot Engine]
        POS --> SNAP
        SNAP --> REP[Replay Engine]
        REP --> DT[Decision Truth Layer]
        REP --> EP[Execution Parity Checker]
        REP --> EXP[Experiment Engine]
        EXP --> REG[Experiment Registry]
        EXP --> EVAL[Evaluation Engine]
        EVAL --> STAT[Statistics Toolkit]
        EVAL --> COMP[Comparison Engine]
        EVAL --> VAL[Validation Engine]
        REP --> INT[Research Integrity Layer]
    end
```

## 2. Dependency Graph

```mermaid
graph TD
    validators[Research Integrity Layer] --> snapshot[Snapshot Engine]
    validators --> replay[Replay Engine]
    replay --> decision[Decision Truth Engine]
    replay --> parity[Execution Parity]
    experiment[Experiment Engine] --> replay
    experiment --> registry[Experiment Registry]
    evaluation[Evaluation Engine] --> experiment
    evaluation --> stats[Statistics Toolkit]
    evaluation --> comparison[Comparison Engine]
    evaluation --> validation[Validation Engine]
    snapshot --> repos[Signal & Trade Repositories]
```

## 3. Module Responsibilities

* **Snapshot Engine**: Captures a deterministic state of the database tables (signals, positions, account equity) at a specific point in time to create immutable JSON snapshots.
* **Replay Engine**: Re-runs past predictions against the captured snapshots to reconstruct trading decisions.
* **Decision Truth Engine**: Single source of truth for argmax and confidence-threshold decision logic.
* **Execution Parity**: Implements production-equivalent filters (cooldowns, conflict filters, exposure limits) in replay mode.
* **Experiment Engine**: Runs parameterized counterfactual strategy configurations over replay results.
* **Experiment Registry**: Stores and tracks strategy configurations and runs.
* **Evaluation Engine**: Computes performance metrics (returns, Sharpe, Sortino, drawdowns, and expectancy).
* **Research Integrity Layer**: Analyzes and alerts for survivorship bias, data leakage, and loss of determinism.
* **Statistics Toolkit**: Pure statistical helper for VaR, CVaR, sample sizing, distribution kurtosis/skewness.
* **Comparison Engine**: Performs paired bootstrapping and hypothesis testing to compare strategy results.
* **Validation Engine**: Performs walk-forward and out-of-sample splits to test generalization.

## 4. Sequence Diagrams

### 4.1 Replay & Experiment Lifecycle

```mermaid
sequenceDiagram
    participant researcher as Research Analyst
    participant snap as Snapshot Engine
    participant rep as Replay Engine
    participant dt as Decision Truth
    participant exp as Experiment Engine
    participant eval as Evaluation Engine
    participant val as Validation Engine

    researcher->>snap: Capture Snapshot
    snap->>rep: Run Replay(Snapshot)
    rep->>dt: decide(Context)
    dt-->>rep: Reconstructed Action (LONG/SHORT/HOLD)
    rep-->>researcher: ReplayResult (Parity Rate)
    researcher->>exp: Run Strategy Experiment(Config)
    exp->>eval: Evaluate(StrategyResult)
    eval->>val: Validate(Splits/Walk-Forward)
    val-->>researcher: ValidationReport & Final Score
```
