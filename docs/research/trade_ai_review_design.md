# Trade AI Review Design Specification

**Sprint**: 4.9A  
**Status**: DESIGN COMPLETE  
**Auditor**: Antigravity

---

## 1. Post-Trade Forensic Review Schema

The AI Review module provides an automated post-trade diagnostic summary based on model metrics and market execution.

```json
{
  "ai_review_id": "rev_ai_99182f",
  "trade_id": 981,
  "metrics": {
    "decision_quality": "EXCELLENT",
    "execution_quality": "OPTIMAL",
    "risk_score": 12.5
  },
  "diagnostics": {
    "market_context": "The trade entered at the bottom of a range before a breakout. Volume was 1.4x the 24h average.",
    "model_confidence_evaluation": "Model was highly confident (85%) due to alignment between 1h and 4h trend vectors.",
    "potential_improvements": "Exit was executed at TP. However, trailing stop could have captured an additional 0.45% before trend reversal.",
    "lessons_learned": "High confidence trend-following setups perform well when volume support exists."
  },
  "research_notes": "Added bookmark. This trade represents a classic model success case under trending regimes."
}
```
