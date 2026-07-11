# Documentation Governance Report

**Date:** 2026-07-11  
**Sprint:** 4.7  
**Auditor:** Antigravity (Governance & Design Agent)  
**Status:** COMPLETE  

---

## 1. Executive Summary

This audit has been performed to resolve documentation clutter in the MoroQuant repository root, classify documentation into a structured hierarchy, create a dedicated domain area for MoroQuant Lab audits, and eliminate documentation drift. 

Additionally, the collaboration model between the system's development agents—**Claude Code** (Implementation) and **Antigravity** (Governance & Design)—has been formalized.

---

## 2. Current Documentation Structure (Before Audit)

Prior to Sprint 4.7, the repository root contained a mixture of code, configuration files, and loose markdown files representing historical reviews, audits, and specifications. The document hierarchy in `docs/` existed but was bypassed, resulting in clutter and duplication.

### Project Root Clutter:
1. `EXECUTION_ANALYTICS_DATA_AUDIT.md` (Loose Audit)
2. `EXECUTION_ANALYTICS_DESIGN_AUDIT.md` (Loose Audit)
3. `EXPERIMENT_REGISTRY_ARCHITECTURE_REVIEW.md` (Loose Review)
4. `EXPERIMENT_REGISTRY_FINAL_REVIEW.md` (Loose Review)
5. `EXPERIMENT_REGISTRY_IMPLEMENTATION_AUDIT.md` (Loose Audit)
6. `EXPERIMENT_REGISTRY_REMEDIATION_AUDIT.md` (Loose Audit)
7. `MARKET_DATA_SYNC_VERIFICATION.md` (Loose Verification Report)
8. `PRODUCTION_PIPELINE_AUDIT.md` (Loose Audit)
9. `dataset_contract.md` (Duplicate)
10. `dataset_manager_design.md` (Duplicate)
11. `model_registry_contract.md` (Duplicate)
12. `model_registry_design.md` (Duplicate)

---

## 3. Changes Made & Files Relocated

Every loose markdown file in the project root has been either moved to its designated domain folder under `docs/` or removed (in cases of exact duplicates).

### Relocation Table:
| File | Action | New Path | Domain Classification |
| :--- | :--- | :--- | :--- |
| `EXECUTION_ANALYTICS_DATA_AUDIT.md` | Relocated | `docs/audits/lab/execution_analytics_data_audit.md` | Lab Audit |
| `EXECUTION_ANALYTICS_DESIGN_AUDIT.md` | Relocated | `docs/audits/lab/execution_analytics_design_audit.md` | Lab Audit |
| `EXPERIMENT_REGISTRY_ARCHITECTURE_REVIEW.md` | Relocated | `docs/audits/lab/experiment_registry_architecture_review.md` | Lab Audit |
| `EXPERIMENT_REGISTRY_FINAL_REVIEW.md` | Relocated | `docs/audits/lab/experiment_registry_final_review.md` | Lab Audit |
| `EXPERIMENT_REGISTRY_IMPLEMENTATION_AUDIT.md` | Relocated | `docs/audits/lab/experiment_registry_implementation_audit.md` | Lab Audit |
| `EXPERIMENT_REGISTRY_REMEDIATION_AUDIT.md` | Relocated | `docs/audits/lab/experiment_registry_remediation_audit.md` | Lab Audit |
| `MARKET_DATA_SYNC_VERIFICATION.md` | Relocated | `docs/reports/market_data_sync_verification.md` | Reports / Verification |
| `PRODUCTION_PIPELINE_AUDIT.md` | Relocated & Renamed | `docs/audits/production/production_trading_pipeline_audit.md` | Production Audit |

---

## 4. Documentation Drift & Duplicates Removed

To prevent documentation drift, root design/contract files were audited against the files in `docs/research/`. The following files were found to be 100% identical duplicates and were removed from the project root:

1. `dataset_contract.md` (Identical copy exists at [dataset_contract.md](file:///home/zafka/trade-dashboard/docs/research/dataset_contract.md))
2. `dataset_manager_design.md` (Identical copy exists at [dataset_manager_design.md](file:///home/zafka/trade-dashboard/docs/research/dataset_manager_design.md))
3. `model_registry_contract.md` (Identical copy exists at [model_registry_contract.md](file:///home/zafka/trade-dashboard/docs/research/model_registry_contract.md))
4. `model_registry_design.md` (Identical copy exists at [model_registry_design.md](file:///home/zafka/trade-dashboard/docs/research/model_registry_design.md))

---

## 5. New Documentation Hierarchy

A dedicated `lab/` subdirectory has been created under `docs/audits/` to allow the MoroQuant Lab subsystem to own its own audit and review history:

```text
docs/
├── adr/             # Architecture Decision Records
├── api/             # API Documentation & Contracts
├── architecture/    # Overall System Architecture
├── audits/          # Verification & Reliability Audits
│   ├── execution/   # Order routing & edge audits
│   ├── lab/         # NEW: MoroQuant Lab (Registry & Analytics reviews)
│   ├── ml/          # Model calibration & loading audits
│   ├── production/  # Production environment & pipeline audits
│   ├── runtime/     # Background daemon logs and loop audits
│   └── telegram/    # Telegram alerts audit
├── database/        # Database schemas & migrations
├── guides/          # Setup tutorials & reference guides
├── reports/         # Repair verifications & health reports
├── research/        # Research designs and specifications
└── sprints/         # Sprint Master Plans & Retrospectives
```

---

## 6. Broken Links Fixed

Cross-references and index files were verified and updated to prevent broken links:
*   **ADR-016 Link Updated:** Fixed link inside [ADR-016-Execution-Analytics-Platform.md](file:///home/zafka/trade-dashboard/docs/adr/ADR-016-Execution-Analytics-Platform.md#L40) from `EXECUTION_ANALYTICS_DATA_AUDIT.md` in root to `docs/audits/lab/execution_analytics_data_audit.md`.
*   **Docs Index Updated:** Modified [docs/README.md](file:///home/zafka/trade-dashboard/docs/README.md) to register `docs/audits/lab/` and `docs/reports/market_data_sync_verification.md`.

---

## 7. AI Responsibilities & Collaboration Model

A formal division of responsibilities has been documented in [docs/book/02-ai-collaboration.md](file:///home/zafka/trade-dashboard/docs/book/02-ai-collaboration.md) and summarized in the root [AGENTS.md](file:///home/zafka/trade-dashboard/AGENTS.md):

### Claude Code Responsibilities:
*   Production implementations, refactoring, and bug patches.
*   Database schema migrations and SQL execution scripts.
*   Test suite writing, execution, and coverage analysis.
*   Runtime daemon integration and package level wiring.

### Antigravity Responsibilities:
*   High-level architecture design and ADR/RFC management.
*   System audit reports, design reviews, and root cause analysis.
*   Repository organization, classification, and governance.
*   Sprint reporting, retrospectives, and project tracking.

---

## 8. Recommendations

1. **Establish CI Lint Checks for Links:** Set up a pre-commit or CI check that verifies all markdown file links are intact (using a tool like `markdown-link-check`).
2. **Mandate Bounded Documentation for New Subsystems:** Any new subsystem added to MoroQuant (such as a Execution Engine update) must create its own subdirectory under `docs/audits/` or `docs/research/` instead of placing loose files in the root.

---

## 9. Final Verdict

### PASS

All loose markdown reviews, audits, and reports have been moved to appropriate directories or removed. Link structures have been verified and updated. The repository root is now clean and production-ready.
