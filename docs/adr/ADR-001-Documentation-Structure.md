# ADR-001: Documentation Structure

## Status
Accepted

## Context
As the MoroQuant codebase grew through research, ML pipeline creation, and paper trading implementation, documentation was created in an ad-hoc manner. Engineers and quants struggled to find architectural decisions, system performance audits, production runbooks, or sprint plans. We need a standardized directory structure and organizational philosophy for all documentation under `docs/`.

## Decision
We adopt a domain-oriented directory hierarchy for all engineering, research, and operational documentation, organized as follows:
- **`architecture/`**: Strategic technical designs and system blueprints (e.g., performance measurement foundation, trade sync logic).
- **`audits/`**: Time-stamped system verification reports and metrics across domains (ML, execution, production, alerting).
- **`adr/`**: Architectural Decision Records detailing major design choices.
- **`database/`**: SQL schemas, migration notes, and verification scripts.
- **`reports/`**: Post-mortems, bug repairs, and execution summary reports.
- **`guides/`**: Setup procedures, configuration workflows, and operational readmes.
- **`references/`**: Specification rules, filters, and policies.
- **`roadmap/`**: Future product milestones, product backlogs, and infra backlogs.
- **`sprints/`**: Sprint targets, specs, tests, retrospectives, and definitions of done.
- **`testing/`**: Quality assurance protocols and automated code coverage reviews.
- **`runbooks/`**: Incident recovery procedures.
- **`book/`**: Consolidated user manuals and platform tutorials.

## Consequences
- **Positive:** Standardizes document placement; increases developer velocity in finding files; prevents duplication of notes; clarifies where historical audits belong versus living guides.
- **Negative:** Requires developers to adhere to the folder layout and maintain cross-references; requires periodic cleanup of empty folders.

## Alternatives Considered
1. **Flat Documentation Folder:** Rejected because files become too numerous and unmanageable.
2. **Wiki/External Platform:** Rejected because having documentation in the same repository as code ensures version control alignment.
