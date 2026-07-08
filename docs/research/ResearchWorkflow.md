# Research Workflow Specification

## Introduction
The Research Workflow defines the standard operating lifecycle of a trading idea at MoroQuant. It governs how a quantitative hypothesis moves through feature engineering, model training, risk validation, paper trading, and eventual production deployment, enforcing gatekeeping protocols at each stage.

---

## The Workflow Pipeline

```
┌──────┐    ┌─────────┐    ┌──────────┐    ┌──────────┐    ┌────────────┐
│ Idea ├───►│ Dataset ├───►│ Features ├───►│ Training ├───►│ Validation │
└──────┘    └─────────┘    └──────────┘    └──────────┘    └─────┬──────┘
                                                                 │
┌────────────┐    ┌───────────────┐    ┌───────────┐    ┌────────▼───┐
│ Production │◄───┤ Promotion Gate │◄───┤ Paper Tr. │◄───┤  Backtest  │
└────────────┘    └───────────────┘    └───────────┘    └────────────┘
```

1. **Idea Phase**: Formulate a hypothesis (e.g., "Funding rate divergence indicates local bottoms during volatile regimes").
2. **Dataset Phase**: Identify targeted symbols, sample intervals, and temporal bounds.
3. **Features Phase**: Design and implement technical indicators or alternative data metrics in the Feature Store.
4. **Training Phase**: Fit candidate models (e.g., XGBoost, LightGBM) on the training portion of the dataset.
5. **Validation Phase**: Perform walk-forward, out-of-sample tests to check calibration and generalizability.
6. **Backtest Phase**: Run historical simulations using path-dependent stop-loss/take-profit parameters.
7. **Paper Trading Phase**: Deploy the model in a simulated forward-testing environment with live websocket data feeds.
8. **Promotion Gate Phase**: Assess model performance against live benchmarks and execute the promotion transaction.
9. **Production Phase**: Route actual capital signals to exchange APIs.

---

## Detailed Sequence Flows

### Sequence 1: Idea Validation, Feature Engineering, and Dataset Creation
This flow traces how raw ideas get translated into registered features and frozen datasets.

```mermaid
sequenceDiagram
    autonumber
    actor Quant as Quantitative Researcher
    participant FS as Feature Store
    participant DM as Dataset Manager
    participant DB as Metadata Database

    Quant->>Quant: Formulate trading hypothesis
    Quant->>FS: Register new feature definition (name, query, metadata)
    FS->>DB: Check name collisions & save metadata
    DB-->>FS: Definition registered
    FS-->>Quant: Return feature_id
    
    Quant->>DM: Request dataset (feature_ids, symbols, time_bounds)
    DM->>FS: Pull calculated features
    FS-->>DM: Return feature matrix
    DM->>DM: Perform data imputation & calculate fingerprint
    DM->>DB: Save dataset metadata & fingerprint
    DB-->>DM: Dataset version registered
    DM-->>Quant: Return dataset_version_id
```

### Sequence 2: Model Training, Backtesting, and Validation
This flow details how the dataset is used to train, evaluate, and backtest a model.

```mermaid
sequenceDiagram
    autonumber
    actor Quant as Quantitative Researcher
    participant MT as Model Training Engine
    participant ET as Experiment Tracker
    participant BT as Backtest Engine
    participant DB as Metadata Database

    Quant->>MT: Start training run (dataset_version_id, parameters)
    MT->>ET: Initialize run (experiment_id, dataset_version_id)
    ET->>DB: Log run initialization
    
    MT->>MT: Fit model & run validation fold
    MT->>ET: Log hyperparameters & validation scores
    
    MT->>BT: Run backtest on out-of-sample fold
    BT->>BT: Apply path-dependent TP/SL & execution rules
    BT-->>MT: Return Sharpe, Sortino, Drawdown metrics
    
    MT->>ET: Save model weights & final metrics
    ET->>DB: Complete run record
    DB-->>MT: Run finalized
    MT-->>Quant: Report run ID & scorecard
```

### Sequence 3: Paper Trading Deployment and Promotion to Production
This flow tracks live forward testing and the promotion to production.

```mermaid
sequenceDiagram
    autonumber
    actor Quant as Quantitative Researcher
    participant ET as Experiment Tracker
    participant PT as Paper Trading Service
    participant PE as Production Engine
    participant DB as Metadata Database

    Quant->>ET: Request run scorecard comparison
    ET->>DB: Query candidate runs
    DB-->>ET: Return candidate scorecards
    ET-->>Quant: Top ranked run ID
    
    Quant->>PT: Deploy run to paper trading environment
    PT->>DB: Update run status to PAPER_TESTING
    
    Note over PT: Model processes live WebSocket data feeds & logs paper trades
    
    Quant->>ET: Query paper trading metrics vs benchmarks (e.g. 30 days)
    ET->>DB: Query paper performance records
    DB-->>ET: Return paper metrics
    ET-->>Quant: Scorecard (Sharpe, win rate, drawdown)
    
    Quant->>PE: Promote model (trigger promotion gate transaction)
    PE->>DB: Verify signature & audit log (is_promoted=true, status=PRODUCTION)
    PE-->>Quant: Production trading signal generation active
```
