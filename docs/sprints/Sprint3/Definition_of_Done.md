# Sprint 3 Definition of Done (DoD)

This document establishes the quality criteria that every feature must meet before it can be marked as "Done" and merged into the main branch.

---

## 1. Code Quality & Standards

### Python (Backend)
- Code must pass formatting checks (`black` or `ruff`).
- No linting warnings or errors from `flake8` or `ruff`.
- Unused imports, variables, and commented-out code blocks must be removed.

### TypeScript / React (Frontend)
- Build must complete successfully with zero TypeScript compilation errors.
- ESLint checks must pass without warnings (`npm run lint`).
- Component file structures must strictly adhere to Next.js App Router rules.

---

## 2. Test Coverage & Validation

- **Unit Test Coverage:** All new services, utility functions, or API routes must have at least **80% code coverage** verified via `pytest-cov`.
- **Database Safety:** Any database additions or migrations must be verified for safe rollbacks and idempotency.
- **Error Handling:** Negative paths (e.g. 404s, internal server errors, WebSocket timeouts) must be explicitly tested.

---

## 3. Documentation Requirements

- All newly added files must have clear docstrings (for Python functions/classes) or comments (for complex TypeScript components).
- Update the relevant `docs/` files to reference the new endpoints or frontend views.
- If there are new configuration parameters, they must be documented in `ml_service/config.example.yaml`.

---

## 4. Peer Review & Verification

- Every Pull Request requires at least one peer approval.
- Code must be locally run and manually verified.
- The logs must be verified to ensure no API keys or tokens are printed.
