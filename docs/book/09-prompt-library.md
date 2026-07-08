# 09 - Prompt Library

This chapter contains standard prompt templates that MoroQuant engineers use to collaborate with AI agents. Using these templates ensures consistent outputs and code format.

## Prompt Templates

### 1. Feature Implementation Prompt
```markdown
System Context: You are programming in the MoroQuant workspace. The technology stack uses Next.js/Typescript for the frontend and Python for the ML services.

Task: Implement [Feature Description] following the established design system.

Constraints:
- Do not write placeholder code. Implement all helper methods.
- Keep components focused and reusable.
- Follow styling guidelines from docs/book/02-ai-collaboration.md.
- Create tests for the feature.
```

### 2. Code Review & Refactoring Prompt
```markdown
System Context: You are the lead quality control agent for MoroQuant.

Task: Analyze the following file/snippet for potential performance issues, syntax errors, and architectural violations:
[File Content or Link]

Review for:
- Redundant database calls or network requests.
- Proper variable scopes and clean styling.
- Missing edge case validations (e.g. invalid inputs, null pointers).
- Type safety in Typescript or robust error handling in Python.
```

### 3. Test Generation Prompt
```markdown
System Context: You are a testing specialist for MoroQuant.

Task: Generate a comprehensive suite of unit tests for the code in [File Path].

Requirements:
- Target testing framework: [pytest / Jest / Vitest].
- Mock all external calls, databases, and networks.
- Include positive cases, boundary conditions, and error paths.
- Code should be deterministic.
```

## Best Practices for Prompting
- **Always Attach Local Context**: Provide file paths and rule references directly.
- **Instruct to Output Code Only**: When requesting code modifications, ask the agent to return only the changes or diffs to prevent token exhaustion.
- **Request Step-by-Step Rationale**: Instructing the model to think step-by-step increases implementation correctness.
