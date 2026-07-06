# MoroQuant Documentation Index

Welcome to the MoroQuant algorithmic trading system documentation repository. This directory is organized using a domain-oriented structure.

---

## Directory Hierarchy

### [architecture/](file:///home/zafka/trade-dashboard/docs/architecture/)
System design, implementation plans, and strategic technical blueprints.
- **Example:** [performance_measurement_foundation.md](file:///home/zafka/trade-dashboard/docs/architecture/performance_measurement_foundation.md)

### [audits/](file:///home/zafka/trade-dashboard/docs/audits/)
System verification reports, reliability audits, and quality metrics divided by domain.
- **[ml/](file:///home/zafka/trade-dashboard/docs/audits/ml/)**: Machine learning models, prediction behavior, calibration, and signal quality (e.g., [confidence_pipeline_audit.md](file:///home/zafka/trade-dashboard/docs/audits/ml/confidence_pipeline_audit.md)).
- **[execution/](file:///home/zafka/trade-dashboard/docs/audits/execution/)**: Trading order placement, checkpoint evaluations, and edge measurement (e.g., [outcome_logic_audit.md](file:///home/zafka/trade-dashboard/docs/audits/execution/outcome_logic_audit.md)).
- **[runtime/](file:///home/zafka/trade-dashboard/docs/audits/runtime/)**: Active daemon processes, event loops, and scheduler execution logs.
- **[production/](file:///home/zafka/trade-dashboard/docs/audits/production/)**: Live environments, data pipeline integrity, and synchronization audits (e.g., [live_analytics_audit.md](file:///home/zafka/trade-dashboard/docs/audits/production/live_analytics_audit.md)).
- **[telegram/](file:///home/zafka/trade-dashboard/docs/audits/telegram/)**: Audits of the alert notifications system.

### [adr/](file:///home/zafka/trade-dashboard/docs/adr/)
Architecture Decision Records (ADRs) capturing key design decisions.
- **ADR-001:** [ADR-001-Documentation-Structure.md](file:///home/zafka/trade-dashboard/docs/adr/ADR-001-Documentation-Structure.md)

### [database/](file:///home/zafka/trade-dashboard/docs/database/)
Database schemas and configurations.
- **[migrations/](file:///home/zafka/trade-dashboard/docs/database/migrations/)**: Summaries of historical database migrations and validation reports (e.g., [triple_barrier_migration_report.md](file:///home/zafka/trade-dashboard/docs/database/migrations/triple_barrier_migration_report.md)).

### [reports/](file:///home/zafka/trade-dashboard/docs/reports/)
System health reports, performance reviews, and verification of repairs.
- **Example:** [live_performance_report.md](file:///home/zafka/trade-dashboard/docs/reports/live_performance_report.md), [outcome_engine_repair.md](file:///home/zafka/trade-dashboard/docs/reports/outcome_engine_repair.md).

### [guides/](file:///home/zafka/trade-dashboard/docs/guides/)
Step-by-step setup instructions and configuration procedures.
- **Example:** [telegram_setup.md](file:///home/zafka/trade-dashboard/docs/guides/telegram_setup.md)

### [references/](file:///home/zafka/trade-dashboard/docs/references/)
Policy documents, specifications, and signal criteria rules.
- **Example:** [telegram_filters.md](file:///home/zafka/trade-dashboard/docs/references/telegram_filters.md)

### Empty Structure for Future Documentation:
- **[roadmap/](file:///home/zafka/trade-dashboard/docs/roadmap/)**: Future milestones and feature roadmaps.
- **[sprints/](file:///home/zafka/trade-dashboard/docs/sprints/)**: Sprint goals and task tracking.
- **[testing/](file:///home/zafka/trade-dashboard/docs/testing/)**: Quality assurance test suites and coverage reports.
- **[runbooks/](file:///home/zafka/trade-dashboard/docs/runbooks/)**: Operational incident recovery runbooks.
- **[book/](file:///home/zafka/trade-dashboard/docs/book/)**: Consolidated user manuals and knowledge base.

---

## Documentation Philosophy

1. **Single Source of Truth**: Each document has one canonical location. No duplicates.
2. **Immutable Research**: Documents in `research/` define specifications. Code implements specification, not the reverse.
3. **Audits Record Reality**: Audits capture system state at a point in time. They are historical records.
