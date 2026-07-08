# 04 - Documentation Standard

High-quality documentation is critical to the longevity of MoroQuant. This guide sets formatting, organization, and upkeep rules for all project documents.

## Directory Structure

All engineering documents reside in the `docs/` folder:

```
docs/
├── adr/             # Architecture Decision Records
├── architecture/    # System design, block diagrams, data flow
├── audits/          # Code quality, security, and performance audits
├── book/            # This playbook (Engineering standard docs)
├── database/        # Schema definition documentation
├── guides/          # Setup, onboarding, developer tutorials
├── reports/         # Analysis and simulation outputs
├── runbooks/        # Operational procedures (ops, recovery)
└── sprints/         # Sprint planning and retro notes
```

## Formats & Syntax

### Markdown Principles
- **Semantic HTML**: Use standard markdown equivalents where possible.
- **Relative File Links**: Use relative or clickable markdown file links to connect related docs.
- **Code Highlighting**: Always specify the language context in code blocks (e.g. ````js`, ````python`, ````bash`).

### Architecture Decision Records (ADR)
All major architectural pivots require an ADR in `docs/adr/`. Each ADR follows the format:
1. **Title**: Simple, numbered (e.g., `0003-use-nextjs-app-router.md`).
2. **Status**: `Draft` | `Proposed` | `Accepted` | `Deprecated` | `Superseded`.
3. **Context**: What problem are we trying to solve? What are the constraints?
4. **Decision**: What did we decide to do?
5. **Consequences**: What becomes easier/harder as a result of this decision?

## Documentation Lifecycle

```mermaid
graph LR
    A[New Design / Pivot] --> B[Write ADR]
    B --> C[Review & Approve]
    C --> D[Update Architecture Docs]
    D --> E[Implement Code]
    E --> F[Update Runbooks / Guides]
```

## Documentation Checklist
- [ ] Are all code terms and filenames formatted as clickable markdown links where applicable?
- [ ] Is there any stale documentation left behind by this PR?
- [ ] Have diagrams been updated if system data flows changed?
- [ ] Are all formatting rules, table schemas, and lists valid markdown?
