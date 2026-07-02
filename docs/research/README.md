# MoroQuant Research Knowledge Base

This directory contains the canonical research specifications for MoroQuant.

**CRITICAL:** Research documents are the ONLY source of truth for implementation.

---

## Index

### Execution Audit Framework

**Document:** [execution_audit_framework.md](execution_audit_framework.md)

**Purpose:**  
Design a mathematically rigorous, deterministic execution audit framework to identify the precise drivers of alpha degradation by analyzing the interaction between model signals, market regimes, and execution policies (SL, TP, trailing stop, break-even rules).

**Implementation Status:**  
Not implemented. Implementation planned for ml_service/audit/ module.

**Related Modules:**
- `ml_service/audit/` (planned)
- `ml_service/services/paper_analytics_service.py` (execution data source)
- `ml_service/storage/database.py` (trade data access)

**Key Metrics Defined:**
- Average MAE (Maximum Adverse Excursion)
- Average MFE (Maximum Favorable Excursion)
- Profit Capture Ratio (PCR)
- Profit Leakage (PL)
- Execution Quality Score (EQS)
- Execution Efficiency (EE)
- Holding Time Distribution
- Drawdown Distribution
- Risk-to-Reward Distribution
- Model/Execution Classification Matrix (MC/EC, MC/EW, MW/EC, MW/EW)
- Expected Value Decomposition

**Pattern Detectors Defined:**
1. Trailing Too Early
2. Trailing Too Late
3. Stop-Loss (SL) Too Tight
4. Stop-Loss (SL) Too Wide
5. Take-Profit (TP) Too Close
6. Take-Profit (TP) Too Far
7. Severe Profit Leakage
8. Fat-Tail Losses
9. Regime Failure
10. Confidence Failure
11. Execution Drift

**Recommendation Rules:**
- Optimize Trailing Stop Distance
- Adjust Take-Profit Target
- Calibrate Stop-Loss Limits
- Address Execution Slippage
- Apply Dynamic Sizing based on Confidence

**Dependencies:**
- Closed trade history with path-dependent data (MAE, MFE, entry/exit prices, timestamps)
- Regime classification
- Confidence scores
- Execution metadata (exit reason, stop/target levels)

**Cross-References:**
- Implementation: (pending)
- Audits: (none yet)
- Architecture: (none yet)

---

## Research Workflow

**Standard Engineering Process:**

```
Research
    ↓
Research Specification (.md)
    ↓
Version Control (Git)
    ↓
Implementation
    ↓
Architecture Review
    ↓
Production
```

Every feature must follow this workflow.

---

## Research Document Requirements

Every research specification MUST contain the following sections:

### 1. Objective
Clear statement of the research goal and what problem it solves.

### 2. Statistical Justification
Why this approach is necessary and what existing approaches fail to capture.

### 3. Mathematical Definitions
Formal notation for all variables, parameters, and data structures.

### 4. Formal Formulae
Exact mathematical expressions for all metrics, with no ambiguity.

### 5. Thresholds
Explicit numeric thresholds for classification and pattern detection.

### 6. Deterministic Rules
Rule-based logic for all detectors, recommendations, and classifications.

### 7. Inputs
Complete specification of required data sources and their schemas.

### 8. Outputs
Expected format and structure of all results.

### 9. Assumptions
Explicit statements of preconditions, data quality requirements, and limitations.

### 10. References
Related research, architecture documents, or external sources.

### 11. Related Modules
Python modules that interact with or implement this specification.

---

## Implementation Protocol

**Before implementing ANY research specification:**

1. **Verify Completeness**  
   Confirm that the research document contains all required sections listed above.

2. **No Assumptions**  
   If any section is missing or ambiguous, STOP and request clarification from the research team.

3. **Exact Implementation**  
   Implement every formula, threshold, and rule exactly as written. Do not:
   - Simplify metrics
   - Adjust thresholds
   - Redesign formulas
   - Invent missing parameters
   - Substitute heuristics for deterministic rules

4. **No Chat History**  
   Implementation must depend ONLY on the versioned research document, not on conversation context or chat history.

5. **Verification**  
   After implementation, the architecture review must verify that the code matches the research specification exactly.

---

## Adding New Research

When adding a new research specification to this directory:

1. **Create the document** following the naming convention: `{topic}_framework.md` or `{topic}_specification.md`

2. **Update this index** with:
   - Document link
   - Purpose (1-2 sentences)
   - Implementation status
   - Related modules
   - Key metrics/algorithms defined
   - Dependencies
   - Cross-references

3. **Commit to version control** immediately so implementation can reference a stable, versioned specification

4. **Notify the team** that a new research specification is available for implementation

---

## Research Philosophy

### Research is Immutable
Once a research document is used for implementation, it becomes the source of truth. If requirements change, create a new version or addendum rather than editing the original.

### Implementation Follows Research
Code implements research specifications. Research does not document existing code. The direction is always: research → implementation.

### No Improvisation
If a research specification is incomplete, implementation must stop and request clarification. Guessing thresholds, simplifying metrics, or inventing formulas creates technical debt and invalidates the research foundation.

### Version Control is Truth
The research specification in git is authoritative. Chat conversations, meeting notes, and external documents are not sources of truth for implementation.

---

## Contact

For questions about research specifications:
- Check the research document first
- Review related audit reports in `docs/audits/`
- Consult with the MoroQuant research team

For implementation issues:
- Verify your implementation matches the research specification exactly
- Check if the research document has all required sections
- Request clarification if the specification is ambiguous
