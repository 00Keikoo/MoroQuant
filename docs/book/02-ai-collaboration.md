# 02 - AI Collaboration Standard

MoroQuant leverages autonomous AI agents to accelerate development. This document defines the rules of engagement between human engineers and AI agents to ensure codebase stability.

## Agent Collaboration Workflow

```mermaid
sequenceDiagram
    participant H as Human Engineer
    participant A as AI Agent
    participant Env as Environment / Sandbox
    
    H->>A: Prompt / Issue Description
    A->>Env: Read files & context
    A->>Env: Perform changes (with permission checks)
    A->>Env: Execute test suite & check linter
    Env-->>A: Feedback (errors / success)
    A-->>H: Report results / Request PR approval
```

## AI Collaboration Rules

### 1. Context and Permission Boundaries
- **No Wildcard Permissions**: AI agents must never request blanket read/write access (`*` or root-level directories).
- **Scope Limitation**: Agents must operate strictly within the target subdirectory of the project.
- **Rule Adherence**: Agents must look for instruction files (e.g., [AGENTS.md](file:///home/zafka/trade-dashboard/AGENTS.md) or specialized agent rule files) to respect system-level constraints.

### 2. Output and Interactivity Rules
- **No Placeholders**: AI agents must provide fully implemented features, not partial templates or `// TODO: implement later` comments.
- **No Direct-to-User Chat for Tasks**: Agents must use designated tools for filesystem operations and should not ask the user to execute steps the agent is capable of running itself.
- **Self-Correction**: Agents are expected to inspect error outputs, fix compile issues, and run unit tests before concluding their execution.

## AI Execution Checklist

- [ ] Has the agent verified the local context rules and system information?
- [ ] Are permissions scoped specifically to the directories containing the target files?
- [ ] Have all proposed code changes been locally compiled and verified?
- [ ] Does the agent explain changes using concise, descriptive reasoning?
- [ ] Have tests run successfully inside the workspace?
