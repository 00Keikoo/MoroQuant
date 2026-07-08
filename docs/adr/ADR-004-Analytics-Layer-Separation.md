# ADR-004: Analytics Layer Separation

## Status
Accepted

## Context
Computing portfolio metrics, backtest indicators, and ML feature derivations can be resource-intensive. Coupling these analytics calculations directly within the API gateway, web servers, or front-end components blocks threads, increases system latency, and complicates hardware scaling.

## Decision
We will decouple the raw trade execution logic from the **Analytics and Metrics Engine**. The core analytics computations (e.g., Sharpe, Sortino, drawdowns, risk attribution) will be handled as isolated operations. The front-end will fetch pre-calculated analytics metrics or query dedicated analytical worker services, rather than running on-the-fly calculations on transactional systems.

## Consequences
- **Scalability**: Allows resource-heavy analytical tasks to run on dedicated ML or high-compute servers.
- **Responsiveness**: Reduces response latency for user UI views.
- **Resource Management**: Ensures critical trading or execution engines are not starved of CPU/memory by long-running reporting requests.
- **Slight Overhead**: Requires maintaining distinct analytics repositories, event publishers, or cron jobs to pre-calculate and store analytical summaries.

## Alternatives Considered
- **On-Demand API Computing**: Calculating all metrics dynamically when the user requests the page. Rejected due to performance bottlenecks on large trading datasets.
- **Database View Calculations**: Using complex SQL views to calculate statistical indicators in database runtime. Rejected as it degrades database transactional performance.

## Related Documents
- [06-testing-standard.md](file:///home/zafka/trade-dashboard/docs/book/06-testing-standard.md)
- [07-audit-standard.md](file:///home/zafka/trade-dashboard/docs/book/07-audit-standard.md)

## Future Impact
Allows MoroQuant to transition to stream processing frameworks or asynchronous message brokers for real-time portfolio updates without changing execution rules.
