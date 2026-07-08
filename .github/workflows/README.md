# GitHub Actions Workflow & Integration Foundation

This directory houses the automation workflow configurations for the MoroQuant repository.

> [!NOTE]
> CI/CD pipeline definitions are placeholder descriptions. Only document files and workflow definitions should be added at this stage. Do not deploy active runner pipelines yet.

## Branch Strategy

We enforce a feature branch workflow with target PR restrictions:

```
                  +--------------------------------+
                  |  feature/*, fix/*, docs/*      |
                  +--------------------------------+
                                  |
                                  | Create Pull Request
                                  v
                  +--------------------------------+
                  |  Continuous Integration (CI)   |
                  |  - Linting & Formatting Check   |
                  |  - Type-checking               |
                  |  - Unit & Integration Tests    |
                  +--------------------------------+
                                  |
                                  | Code Review Approval
                                  v
                  +--------------------------------+
                  |  main / master branch          |
                  +--------------------------------+
                                  |
                                  | Tagged Releases
                                  v
                  +--------------------------------+
                  |  release/v* branches           |
                  +--------------------------------+
```

## Scheduled & Event Workflows

| Workflow Name | Trigger Event | Primary Steps | Target Runner |
|---|---|---|---|
| `code-quality.yml` | `pull_request` on `main` | ESLint, pytest, tsc compilation checks | GitHub Ubuntu Runner |
| `security-audit.yml` | Weekly schedule | Dependency vulnerability scans | GitHub Ubuntu Runner |
| `release-deploy.yml` | Git tag push `v*` | Package builds, container deployment | Self-hosted runner |

## Local Prerequisites
Before submitting changes to the remote repository, ensure:
- Pre-commit hooks run locally to verify basic file patterns.
- Unit tests pass with `npm run test` or `pytest`.
