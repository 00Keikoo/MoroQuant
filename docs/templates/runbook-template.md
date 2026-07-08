# Runbook: [Operational Procedure Name]

## 1. Overview
- **Objective**: [Goal of this runbook, e.g. database restore, instance recovery.]
- **Impact Severity**: [High / Medium / Low]
- **Target Systems**: [e.g. Next.js App, ML Server, Database Storage]

## 2. Prerequisites
- [List CLI tools, permission scopes, access keys, or env configurations required.]

## 3. Step-by-Step Instructions

> [!CAUTION]
> [Highlight any steps that have permanent side-effects, such as data destruction.]

1. **Step 1: Check Current Status**
   - Command: `[Insert command]`
   - Expected Output: `[Expected return state]`
2. **Step 2: Execute Mitigation/Operation**
   - Command: `[Insert command]`
3. **Step 3: Verification**
   - Command: `[Insert command]`
   - Verify: Check logs at `[Path to logfile]` to confirm standard status codes.

## 4. Troubleshooting
- **Symptom**: [What goes wrong at a step?]
  - **Resolution**: [How to recover or bypass.]

## 5. Rollback Plan
[Detailed steps to revert system back to original state if this execution fails midway.]
