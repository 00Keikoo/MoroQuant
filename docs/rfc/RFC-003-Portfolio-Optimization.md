# RFC-003: Portfolio Optimization Module

## Status
Proposed

## Problem Statement
The dashboard and trading models execute on naive fixed weight distributions or simple rule-based position allocations. The system cannot perform mathematical optimizations (such as Mean-Variance or risk parity calculations) dynamically across multiple assets.

## Motivation
To maximize risk-adjusted returns (Sharpe ratio), the portfolio allocation must adapt dynamically to asset correlation shifts and historical volatilities. We need a flexible Optimization Module.

## Current State
Assets are allocated fixed capital percentages (e.g. 10% per ticker) or simple multiplier values configured in local files. No covariance matrices or optimization solvers are integrated.

## Proposed Solution
Create a pluggable Portfolio Optimization module inside the analytics/ML service:
1. Fetch historical price feeds for active assets.
2. Build daily/hourly covariance and expected return matrices.
3. Integrate mathematical solver libraries (e.g. SciPy optimize or CVXPY) to solve for target objectives (Max Sharpe, Min Variance, Equal Risk Contribution).
4. Output target weights to the execution or database layer.

## Alternatives
- **Third-Party API Integration**: Outsource optimization calculations to external quantitative platforms. *Pros*: No local math engine updates needed. *Cons*: Network dependency, data privacy concerns, and latency.
- **Rule-Based Approximations**: Use heuristic approximations (e.g. inverse volatility weighting without covariance). *Pros*: Simple, zero solver dependencies. *Cons*: Suboptimal allocations during high asset correlation phases.

## Open Questions
- How frequently should portfolio weights be recalculated? (e.g., daily close vs. real-time dynamic rebalancing).
- Do we need to handle transaction costs and slippage as constraints within the mathematical optimizer?

## Risks
- **Solver Divergence**: Optimizers can fail to converge or take excessive CPU time if constraints are poorly configured.
- **Overfitting**: Relying too heavily on historical covariance can result in unstable portfolios that perform poorly out-of-sample.

## Decision Criteria
- Calculation time for a 50-asset portfolio under 2 seconds.
- Pluggable optimization objective configurations.
- Modular code architecture separating data retrieval from mathematical solver logic.
