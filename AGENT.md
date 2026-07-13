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


# ======================================================
# STITCH FOUNDATION
# ======================================================

Google Stitch is the official UI source of truth.

Before implementing any screen, the project must have a single approved UI Foundation.

The UI Foundation consists ONLY of:

- app/layout.tsx
- app/globals.css

Foundation may contain ONLY:

- Font loading
- Material Symbols loading
- Global CSS variables
- Color tokens
- Typography tokens
- Spacing tokens
- Utility classes
- Global animation utilities

The UI Foundation is implemented ONCE.

After CTO approval the Foundation becomes LOCKED.

Future implementation tasks are NOT allowed to modify:

- app/layout.tsx
- app/globals.css

unless explicit CTO approval is given.


# ======================================================
# SCREEN IMPLEMENTATION MODE
# ======================================================

Frontend implementation is performed ONE SCREEN at a time.

Never implement an entire workspace.

Workflow:

Read Stitch

↓

Read implementation package

↓

Implement ONE screen

↓

Build

↓

Visual Review

↓

CTO Approval

↓

Next screen


# ======================================================
# PIXEL PERFECT RULE
# ======================================================

Google Stitch is NOT inspiration.

Google Stitch is NOT guidance.

Google Stitch is the implementation target.

Frontend engineers must COPY the Stitch layout.

Do NOT:

- redesign
- simplify
- reorganize
- improve
- reinterpret
- optimize layout

Pixel Perfect means visual reproduction.


# ======================================================
# FILE MODIFICATION LOCK
# ======================================================

Every implementation task has a modification boundary.

Claude may modify ONLY files directly required for the current screen.

Example:

Trading Dashboard

Allowed:

- app/dashboard/**
- components/dashboard/**
- lib/mock-data/dashboard*

Forbidden:

- app/layout.tsx
- app/globals.css
- MQDS
- Research pages
- Operations pages
- unrelated shared components

If a forbidden file appears necessary:

STOP.

Explain why.

Wait for CTO approval.


# ======================================================
# VISUAL REVIEW
# ======================================================

A screen is NOT finished when:

- TypeScript passes
- Build passes

A screen is finished ONLY when:

Implementation

≈

Stitch screenshot

If visual differences remain,

continue fixing.

Do NOT continue to another screen.


# ======================================================
# GIT POLICY
# ======================================================

Claude Code NEVER executes:

- git add
- git commit
- git push
- git merge
- git rebase
- git stash
- git checkout
- git switch
- git tag
- git status
- git diff

Git ownership belongs exclusively to the CTO.

Claude only reports:

- Files modified
- Files created
- Build status
- Remaining issues


# ======================================================
# COMPLETION RULE
# ======================================================

After every task output ONLY:

Screen Completed

Files Modified

Files Created

Build Result

Visual Differences Remaining

Ready for CTO Review

STOP.

Never continue to another screen automatically.


# ======================================================
# STITCH HTML IS CANONICAL
# ======================================================

When a Google Stitch design contains a generated HTML file
(code.html),

that HTML becomes the canonical implementation specification.

The frontend engineer MUST treat the HTML as the source of truth.

The screenshot (screen.png) is used ONLY for visual verification.

Priority:

1. code.html
2. screen.png

Never reverse the priority.


# ======================================================
# HTML → REACT CONVERSION MODE
# ======================================================

Frontend implementation is a conversion process.

NOT a redesign process.

Workflow:

Google Stitch

↓

code.html

↓

React Components

↓

Visual Review

↓

CTO Approval

The engineer should think like an HTML compiler,
not a UI designer.


# ======================================================
# STRUCTURE PRESERVATION
# ======================================================

When converting HTML into React:

Preserve exactly:

- DOM hierarchy
- nesting
- ordering
- spacing containers
- wrapper elements
- layout containers
- grid structure
- flex structure

Do NOT:

- merge sections
- move panels
- simplify hierarchy
- remove wrappers
- invent new containers
- reorganize layout

Componentization happens ONLY AFTER
the original hierarchy has been preserved.


# ======================================================
# COMPONENTIZATION POLICY
# ======================================================

Convert HTML into React first.

Verify visual parity.

Only after visual parity has been achieved
may the implementation be split into reusable components.

Never redesign HTML merely to create reusable components.

Correct order:

HTML

↓

React

↓

Visual Match

↓

Component Extraction

Wrong order:

HTML

↓

Architecture

↓

Redesign

↓

React


# ======================================================
# SCREEN RECOVERY MODE
# ======================================================

When recovering an existing screen:

Step 1

Read:

code.html

Step 2

Read:

screen.png

Step 3

Convert HTML into React.

Step 4

Build.

Step 5

Compare against screenshot.

Step 6

Repeat until visually matching.

Do NOT continue to another screen.


# ======================================================
# VISUAL PARITY
# ======================================================

Passing TypeScript

≠

Passing Build

Passing Build

≠

Pixel Perfect

The implementation is complete ONLY IF:

The React implementation visually matches
the official Stitch screenshot.


# ======================================================
# THINKING MODE
# ======================================================

When implementing frontend,
the engineer should think:

"I am converting an existing UI
from HTML into React."

NOT

"I am designing a dashboard."

The engineer is NOT responsible for UI decisions.

The UI decisions have already been made
inside Google Stitch.


# ======================================================
# HTML SECTION MODE
# ======================================================

When a Stitch HTML file is large,

the implementation MUST be divided into sections.

Examples:

Section 1

- Sidebar
- Top Bar

Section 2

- KPI Cards

Section 3

- Chart Area

Section 4

- Data Table

Section 5

- Inspector

Each section must be completed independently.

Each section must compile.

Each section must be visually reviewed.

Only after approval may the engineer continue
to the next HTML section.

Never convert an entire HTML page
in a single implementation task.
