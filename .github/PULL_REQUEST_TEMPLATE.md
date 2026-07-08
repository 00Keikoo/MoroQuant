# Pull Request Template

## Description
[Describe the changes, problem solved, and implementation logic.]

## Ticket / Issue Link
Closes #[Issue number] / [Link to tracking ticket]

## Branch & Workflow Compliance
- **Target Branch**: [e.g., main / release]
- **Branch Prefix Compliance**: (Check one)
  - [ ] `feat/` (New feature)
  - [ ] `fix/` (Bug fix)
  - [ ] `docs/` (Documentation only)
  - [ ] `test/` (Testing adjustments)
  - [ ] `chore/` (Maintenance / configs)

---

## Developer PR Checklist

### 1. Implementation
- [ ] Code compiles locally with no warnings or type errors.
- [ ] No placeholder or partial implementation code remains.
- [ ] Business logic is separated from presentation logic.

### 2. Testing
- [ ] Unit tests cover new code paths (both success and failure paths).
- [ ] Integration tests run against mock APIs, not live endpoints.
- [ ] Local verification confirms all acceptance criteria are met.

### 3. Documentation
- [ ] Code is commented where necessary, with clear explanations of complex logic.
- [ ] Related guides, READMEs, or system docs are updated.
- [ ] If architectural changes were introduced, an ADR was submitted.

---

## Definition of Done (DoD) Verification
- [ ] Standard formatting and lint rules pass green.
- [ ] No hardcoded secrets, private keys, or credentials.
- [ ] Unit test coverage meets project thresholds.
- [ ] PR Title follows Conventional Commits format (e.g. `feat(core): add order validation`).

---

## Reviewer Checklist
*(To be completed by peer reviewer(s))*
- [ ] Code meets style, modularity, and maintainability requirements.
- [ ] Edge cases (null bounds, connection drops, API timeouts) are handled.
- [ ] Performance impacts (SQL queries, loop structures) analyzed.
- [ ] Secrets and configs are properly externalized.
