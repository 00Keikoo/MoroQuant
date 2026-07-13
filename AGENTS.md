<!-- BEGIN:nextjs-agent-rules -->
# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` before writing any code. Heed deprecation notices.
<!-- END:nextjs-agent-rules -->

# AI Collaboration & Responsibilities

This repository defines strict, non-overlapping roles for AI agents (Claude Code and Antigravity) to maintain structural consistency and code quality.

For a full description, see the [AI Collaboration Standard](file:///home/zafka/trade-dashboard/docs/book/02-ai-collaboration.md).

## Division of Responsibilities

### 💻 Claude Code (Implementation & Build)
*   Implementation
*   Refactoring
*   Components
*   Frontend
*   Backend
*   Testing
*   Build Verification
*   Production implementation (features, services, APIs)
*   Bug fixing and hotfix implementation
*   SQL database migrations
*   Writing and executing test suites
*   Runtime integration and package wiring
*   Performance optimization

> [!CAUTION]
> Claude Code should **not** generate architectural audits, reviews, ADRs, RFCs, sprint reports, design specifications, or repository governance documentation unless explicitly requested.

### 🛸 Antigravity (Governance, Audits & Design)
*   Architecture
*   ADR
*   Documentation
*   Audits
*   Design
*   Governance
*   Research
*   Architecture decisions and ADR management
*   Technical design reviews and RFCs
*   Data, schema, and logic audits
*   Repository classification and directory organization
*   Sprint reporting and retrospective compilation
*   Root cause analysis (RCA)
*   Writing development guides, indices, and collaboration standards

> [!NOTE]
> The architecture phase is complete. The frontend implementation phase should prioritize execution over rediscovery.

## UI Source of Truth

Official UI lives in

design/stitch/current/

Never redesign UI during implementation.

Implement pixel-perfect.

If UI conflicts with code,

the design wins.

If architecture conflicts with design,

architecture wins.

If design changes,

update Stitch first.

Then implement.

# Frontend Engineering Rules

## Pattern-Driven Development

The MoroQuant frontend has entered the implementation phase.

Architecture, ADRs, MQDS, UI specifications and Visual Design are considered frozen after Sprint 5.

Claude Code must NOT redesign existing interfaces.

Every new workspace must reuse the nearest existing implementation pattern.

**Examples**

Experiment Workspace → Dataset Workspace

Dataset Workspace → Feature Workspace

Feature Workspace → Validation Center

Validation Center → Calibration Center

Calibration Center → Model Registry

Model Registry → Promotion Center

Research Command Center → Research Timeline

Experiment Workspace → Trade Forensics

## Implementation Rules

1. Never redesign layouts that already exist.

2. Reuse MQDS components whenever possible.

3. Reuse existing page structure.

4. Only replace domain-specific content.

5. Do not reread ADRs or documentation unless explicitly requested.

6. Treat previous workspaces as implementation templates.

7. Every workspace must pass `npm run build` before completion.

8. Each workspace is an independent Git checkpoint.

**Recommended workflow**

Workspace → Build → Commit → Push → Next Workspace

Never accumulate multiple unfinished workspaces.

9. Frontend implementation follows Pattern-Driven Development. The objective is consistency, maintainability, and implementation speed rather than creating new layouts.

## Workspace Inheritance Rule

Before implementing a new workspace:

1. Find the closest completed workspace.
2. Reuse its layout and interaction pattern.
3. Replace only domain-specific content.
4. Preserve MQDS consistency.
5. Do not introduce new UI paradigms without an ADR.

Workspace inheritance is preferred over redesign.
