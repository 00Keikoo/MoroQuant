# ADR-003: Read-Only Trade Explorer Implementation

## Status
Accepted

## Context
The UI dashboard must expose completed trades, backtesting histories, and active positions for analysis. Allowing modification or deletion of this data through general explorer panels risks database corruption, audit trail breakage, and visual inconsistency.

## Decision
We will establish that the Trade Explorer views are strictly **Read-Only** from the front-end dashboard perspective. Any request to initiate or close trades must route through the dedicated Execution Engine or Risk Manager APIs rather than direct state modifications via UI tables or general database administration endpoints.

## Consequences
- **Audit Consistency**: Guarantees trading history remains immutable and auditable.
- **Safety**: Minimizes risks of manual intervention or accidental deletion of historical trade metrics.
- **Simplicity**: Front-end state handling is simplified as it does not need to manage update states, local optimistic UI updates, or rollback handlers for history tables.

## Alternatives Considered
- **Editable Trade Grid**: Permitting inline modifications to trades to correct discrepancies. Rejected due to security risks and the danger of mismatching with broker/exchange logs.
- **Separate Read and Write Panels**: Implementing write capability locked behind administrator flags. Rejected at this stage to keep the explorer focus entirely on visualization and analysis.

## Related Documents
- [07-audit-standard.md](file:///home/zafka/trade-dashboard/docs/book/07-audit-standard.md)
- [ADR-002-Repository-Pattern.md](file:///home/zafka/trade-dashboard/docs/adr/ADR-002-Repository-Pattern.md)

## Future Impact
Ensures that compliance reports generated from the database can be treated as reliable records, as UI modifications to logs are fundamentally impossible.
