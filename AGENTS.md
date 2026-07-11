<!-- BEGIN:nextjs-agent-rules -->
# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` before writing any code. Heed deprecation notices.
<!-- END:nextjs-agent-rules -->

# AI Collaboration & Responsibilities

This repository defines strict, non-overlapping roles for AI agents (Claude Code and Antigravity) to maintain structural consistency and code quality.

For a full description, see the [AI Collaboration Standard](file:///home/zafka/trade-dashboard/docs/book/02-ai-collaboration.md).

## Division of Responsibilities

### 💻 Claude Code (Implementation & Build)
*   Production implementation (features, services, APIs)
*   Refactoring and cleanups
*   Bug fixing and hotfix implementation
*   SQL database migrations
*   Writing and executing test suites
*   Runtime integration and package wiring
*   Performance optimization

> [!CAUTION]
> Claude Code should **not** generate architectural audits, reviews, ADRs, RFCs, sprint reports, design specifications, or repository governance documentation unless explicitly requested.

### 🛸 Antigravity (Governance, Audits & Design)
*   Architecture decisions and ADR management
*   Technical design reviews and RFCs
*   Data, schema, and logic audits
*   Repository classification and directory organization
*   Sprint reporting and retrospective compilation
*   Root cause analysis (RCA)
*   Writing development guides, indices, and collaboration standards
