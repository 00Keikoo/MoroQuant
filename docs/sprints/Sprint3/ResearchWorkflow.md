# Research Overlay Workflow Guide

This document describes the step-by-step workflow of the Research Overlay System, detailing data movement and evaluation paths from production to decision testing.

## Workflow Overview

```
Production Inference
       ↓
Snapshot Engine
       ↓
Replay Engine
       ↓
Experiment Engine
       ↓
Evaluation Engine
       ↓
Validation Engine
       ↓
Decision Truth
```

### 1. Production Inference
Market data (OHLCV) triggers predictions in the ML Pipeline. The model outputs prediction probabilities, which are calibrated and filtered. If signal confidence exceeds thresholds, it is recorded to the SQLite `signals` table. If executed, a position is created in the `paper_positions` table.

### 2. Snapshot Engine
The Snapshot Engine extracts data from `signals` and `paper_positions` (using `SignalRepository` and `TradeRepository`), packaging all records, account parameters, and execution constraints into an immutable, deterministic snapshot.

### 3. Replay Engine
The Replay Engine consumes the snapshot. It executes predictions through the `DecisionEngine` using saved probabilities, checking reconstructed decisions against actual historical executions via the `ExecutionParityChecker`.

### 4. Experiment Engine
Quant analysts define counterfactual Strategy Configurations (e.g. customized thresholds, regime blocklists). The Experiment Engine applies these configurations to the Replay results to test different execution rules on historical signals.

### 5. Evaluation Engine
Computes comparative metrics on strategies, including returns, win rate, expectancy, risk score, estimated Sortino, and estimated Profit Factor.

### 6. Validation Engine
Performs cross-validation: splits the snapshot chronologically (TimeSeriesSplit) and rolls it forward in windows (Walk-Forward) to estimate performance decay (overfitting score) and variance of returns across periods (stability score).

### 7. Decision Truth
The optimal configurations are verified using the single-source-of-truth Decision rules, preparing them for promotion to production settings.
