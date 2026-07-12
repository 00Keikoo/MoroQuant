# AGENT.md

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.

# ============================================
# ENGINEERING EXECUTION MODES
# ============================================

The project has four execution modes.

## MODE A — Frontend Prototype

Purpose:
Implement frontend workspaces using mock data.

Rules:

- Do NOT inspect backend.
- Do NOT inspect repositories.
- Do NOT inspect services.
- Do NOT inspect API contracts.
- Do NOT inspect ADRs unless explicitly requested.
- Reuse the nearest existing workspace.
- Copy existing MQDS patterns.
- Replace only:
  - title
  - filters
  - table
  - inspector
  - mock data
- Run npm run build.
- Commit locally.
- Stop.

Implementation speed is preferred over repository exploration.


## MODE B — Frontend Integration

Purpose:
Connect an existing frontend workspace to the backend.

Rules:

- Inspect ONLY the API endpoints required by the current page.
- Do NOT inspect unrelated backend modules.
- Do NOT inspect unrelated repositories.
- Do NOT inspect unrelated services.
- Keep the UI unchanged.
- Replace mock data with API calls.
- Run npm run build.
- Commit locally.
- Stop.


## MODE C — Backend Feature Development

Purpose:
Implement backend features.

Rules:

- Inspect ONLY the backend modules directly related to the requested feature.
- Avoid repository-wide exploration.
- Do not redesign architecture.
- Preserve Repository → Service → API layering.
- Build.
- Commit.
- Stop.


## MODE D — Architecture & Research

Purpose:
Architecture, ADRs, documentation, audits, governance.

Rules:

- Design only.
- No runtime implementation.
- No production code.
- No frontend implementation.
- Documentation first.


=========================================================
Frontend Workspace Rules
=========================================================

If the user requests:

"Implement Workspace"

Always assume MODE A unless explicitly told otherwise.

Never spend more than 20 seconds exploring the repository.

Never inspect documentation unless explicitly requested.

Never perform repository-wide analysis.

Never perform implementation planning.

Never summarize architecture.

Immediately implement the requested workspace.

When finished:

- npm run build
- commit
- stop

Never git push.
