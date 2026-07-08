# RFC-002: Real-time Risk Engine Design

## Status
Proposed

## Problem Statement
MoroQuant lacks a centralized risk gateway to intercept and validate orders. If an ML model goes haywire, there are no structural guardrails to prevent large size errors, excessive leverage, or repetitive order loops from executing directly on exchanges.

## Motivation
To protect capital, we need an independent, low-latency validation layer (the Risk Engine) that evaluates every trade request against predefined risk parameters before forwarding orders to execution channels.

## Current State
Orders are initiated directly by trading scripts and sent straight to execution mocks. No checking is performed at the system layer for leverage, trade size limits, or overall portfolio drawdown limits.

## Proposed Solution
Introduce a decoupled Risk Engine module operating as a gatekeeper:
1. Intercept all order requests.
2. Read current active parameters (e.g. max position size, max loss limit, allowed symbols).
3. Validate order parameters in memory under 1ms.
4. Return `APPROVED` or `REJECTED` with specific validation codes.

## Alternatives
- **In-Strategy Validation**: Embed risk checks directly inside each trading strategy file. *Pros*: Zero network latency. *Cons*: Susceptible to bypass if a strategy has a bug or is compromised.
- **Post-Trade Reconciliation**: Allow orders to execute, and run a cron job to close violating positions. *Pros*: Easiest. *Cons*: Potential for catastrophic capital loss before the cron executes.

## Open Questions
- Should the risk engine parameters be database-backed or loaded via hardcoded configuration files for speed?
- How should the risk engine handle communication failures with the account database? (Default to block all trades vs. allow bypass).

## Risks
- **Latency Bloat**: Introducing an extra validation layer could delay trade execution, increasing slippage.
- **State Mismatch**: If the risk engine's local cache of current positions gets out of sync with actual exchange positions, it may block valid trades or allow invalid ones.

## Decision Criteria
- Interception latency less than 2 milliseconds.
- Zero bypass capability for order routing modules.
- Strict isolation of risk parameters from general system controls.
