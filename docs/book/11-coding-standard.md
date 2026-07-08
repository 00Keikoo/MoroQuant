# 11 - Coding Standard

This document details the code-level stylistic rules and quality controls for MoroQuant's principal technologies: TypeScript/React and Python.

## Language Standards

### TypeScript (Frontend)
- **Strict Typing**: Never use `any`. Define interfaces/types for all properties, parameters, and API outputs.
- **Components**: Prefer functional components and custom hooks for business logic separation.
- **Imports**: Organize imports with absolute mappings where configured (e.g. `@/components/`).

### Python (ML Services)
- **Type Hinting**: All function parameters and return values must use type hints (`def process(data: dict) -> list:`).
- **Style Compliance**: Adhere strictly to PEP 8. Use standard auto-formatters (e.g., Black, Flake8).
- **Docstrings**: Document classes and public functions following Google Style Python Docstrings.

## Naming & Style Conventions

| Language | Entity | Pattern | Example |
|---|---|---|---|
| TS / JS | Classes | PascalCase | `PositionManager` |
| TS / JS | Functions / Variables | camelCase | `calculateSharpe` |
| Python | Classes | PascalCase | `BacktestEngine` |
| Python | Functions / Variables | snake_case | `get_risk_metrics` |
| SQL | Tables / Columns | snake_case | `trade_logs` |

## Code Construction Checklist
- [ ] No debugger statements or obsolete print/console statements left in code.
- [ ] Variable and function names are self-descriptive.
- [ ] Heavy calculations use memoization (e.g., `useMemo` in React) to prevent UI lag.
- [ ] Explicit error handling is used (no bare `except:` statements in Python).
