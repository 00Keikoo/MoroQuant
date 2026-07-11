# Timeline State Machine Specification

**Sprint**: 4.7A  
**Status**: DESIGN COMPLETE  
**Auditor**: Antigravity

---

## 1. Lifecycle State Definitions

An institutional-grade quantitative model progresses through the following sequential states:

1.  **`CREATED`**: Run metadata registered; parameters locked.
2.  **`TRAINING`**: Walk-forward validation model estimation in progress.
3.  **`VALIDATING`**: Out-of-sample performance evaluation (F1, Precision, Recall).
4.  **`CALIBRATING`**: Probability calibration and ECE checking.
5.  **`BACKTEST`**: Historical strategy performance simulation.
6.  **`PAPER`**: Active paper trading deployment.
7.  **`EXECUTION`**: Latency, slippage, and execution analytics checks.
8.  **`PROMOTION`**: Stage-gate review and approval signature collection.
9.  **`PRODUCTION`**: Active live exchange trading deployment.
10. **`ARCHIVED`**: Model superseded by newer iteration.
11. **`FAILED`**: Abandoned due to metric failure or processing error.

---

## 2. State Machine Diagram

```mermaid
stateDiagram-v2
    [*] --> CREATED
    CREATED --> TRAINING
    TRAINING --> VALIDATING
    VALIDATING --> CALIBRATING
    CALIBRATING --> BACKTEST
    BACKTEST --> PAPER
    PAPER --> EXECUTION
    EXECUTION --> PROMOTION
    PROMOTION --> PRODUCTION
    PRODUCTION --> ARCHIVED
    
    TRAINING --> FAILED
    VALIDATING --> FAILED
    CALIBRATING --> FAILED
    BACKTEST --> FAILED
    PAPER --> FAILED
    EXECUTION --> FAILED
    PROMOTION --> FAILED
    
    ARCHIVED --> [*]
    FAILED --> [*]
```

---

## 3. Promotion Verification Sequence

This diagram shows the sequence of checks executed before promoting a model candidate to production status.

```mermaid
sequenceDiagram
    participant MR as Model Registry
    participant VC as Validation Center
    participant CC as Calibration Center
    participant EB as Paper Broker
    participant PM as Promotion Manager

    MR->>PM: Initiate Promotion Request
    PM->>VC: Verify OOS F1 Score >= Threshold
    VC-->>PM: PASS (F1: 0.65)
    PM->>CC: Verify ECE <= 0.05
    CC-->>PM: PASS (ECE: 0.02)
    PM->>EB: Audit Paper Trade (Min 100 Fills)
    EB-->>PM: PASS (98% fill rate, <50ms latency)
    PM->>MR: Update Status: PRODUCTION
```
