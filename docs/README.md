# MoroQuant Documentation

Documentation for the MoroQuant algorithmic trading system.

---

## Folder Structure

### `research/`

Mathematical specifications, statistical frameworks, and quantitative research.

**Content:**
- Metric definitions and formulas
- Statistical validation methodologies
- Algorithm specifications
- Research-backed execution frameworks

**Ownership:** MoroQuant

**When to add here:**
- Mathematical derivations
- Statistical justifications
- Research specifications with formal definitions
- Algorithm design documents with proofs

### `audits/`

Production verification reports and system health checks.

**Content:**
- Production pipeline audits
- Schema verification reports
- Model loading audits
- Calibration investigations
- Performance analysis reports

**Ownership:** MoroQuant

**When to add here:**
- System verification reports
- Production health checks
- Investigation results
- Root cause analyses
- Performance diagnostics

### `architecture/`

System design, implementation plans, and strategic roadmaps.

**Content:**
- Implementation plans
- Readiness assessments
- Architecture decisions
- Feature specifications
- Strategic roadmaps

**Ownership:** MoroQuant

**When to add here:**
- System design documents
- Feature implementation plans
- Architecture decision records (ADRs)
- Readiness assessments
- Roadmap documents

### `migrations/`

Historical database changes and migration summaries.

**Content:**
- Migration summaries
- Schema change logs
- Production deployment records
- Configuration updates

**Ownership:** MoroQuant

**When to add here:**
- Database migration summaries
- Production deployment logs
- Major configuration changes
- System migration records

### `images/`

Diagrams, charts, and visual assets referenced in documentation.

**Content:**
- Architecture diagrams
- Flow charts
- Performance graphs
- Screenshots

**When to add here:**
- Any visual assets referenced in markdown documents
- Diagrams exported from tools
- Charts and graphs

---

## Research Knowledge Base

**[→ View Research Index](research/README.md)**

Research specifications are the **ONLY** source of truth for all implementation work in MoroQuant.

### Research-Driven Engineering Workflow

```
Research
    ↓
Research Specification (.md)
    ↓
Version Control (Git)
    ↓
Implementation
    ↓
Architecture Review
    ↓
Production
```

**Critical Principles:**

1. **Research documents are authoritative**  
   Implementation must follow research specifications exactly. No simplification, no improvisation, no assumptions.

2. **Implementation follows research**  
   Code implements specifications. Research does not document existing code. The direction is always: research → implementation.

3. **Architecture reviews verify compliance**  
   Reviews confirm that implementation matches the research specification exactly.

4. **Chat conversations are not authoritative**  
   Conversations are temporary context. Implementation must depend only on versioned research documents in git.

5. **Stop if specifications are incomplete**  
   If a research document is missing required sections (formulas, thresholds, deterministic rules), implementation must stop and request clarification rather than guessing.

See [research/README.md](research/README.md) for the complete research index, implementation protocol, and document requirements.

---

## Documentation Philosophy

1. **Single Source of Truth**: Each document has one canonical location. No duplicates.

2. **Immutable Research**: Documents in `research/` define specifications. Implementation follows research, not the reverse.

3. **Audits Record Reality**: Audit documents capture system state at a point in time. They are historical records, not living documents.

4. **Architecture Evolves**: Implementation plans and roadmaps in `architecture/` are living documents that reflect current direction.

5. **Migrations Are Append-Only**: Migration records are never modified after deployment. New migrations reference previous ones.

---

## Naming Conventions

### Research Documents
- Format: `{topic}_specification.md` or `{topic}_framework.md`
- Example: `execution_audit_framework.md`
- Use descriptive, permanent names

### Audit Reports
- Format: `{system_component}_audit.md` or `{investigation_topic}_analysis.md`
- Example: `production_pipeline_audit.md`, `sharpe-pipeline-analysis.md`
- Include scope in filename

### Architecture Documents
- Format: `{feature_name}_plan.md` or `{assessment_type}_readiness.md`
- Example: `live_trading_analytics_plan.md`, `paper_trading_readiness.md`
- Use action-oriented names

### Migration Summaries
- Format: `{change_description}_migration_summary.md`
- Example: `production_migration_summary.md`
- Keep names brief but descriptive

---

## Cross-References

When referencing other documents, use relative paths:

```markdown
See [Execution Audit Framework](../research/execution_audit_framework.md) for metric definitions.
```

---

## Maintenance

- **Quarterly Review**: Archive obsolete audits, update roadmaps, verify cross-references
- **On Major Changes**: Update architecture documents to reflect new patterns
- **Before Deployment**: Create migration summary if schema/config changes
- **After Research**: Add specification to `research/` before implementation begins

---

## Quick Navigation

**Recent Research:**
- [Execution Audit Framework](research/execution_audit_framework.md)

**Latest Audits:**
- [Sharpe Pipeline Analysis](audits/sharpe-pipeline-analysis.md)
- [Production Pipeline Audit](audits/production_pipeline_audit.md)
- [Calibration Audit](audits/calibration_audit.md)

**Current Roadmap:**
- [Next Steps](architecture/next_steps.md)
- [Paper Trading Readiness](architecture/paper_trading_readiness.md)

**Recent Migrations:**
- [Production Migration Summary](migrations/production_migration_summary.md)
