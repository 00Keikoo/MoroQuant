"""Execution Audit Report Generator.

Generates comprehensive audit reports combining metrics, patterns, and recommendations.
"""

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Dict, List

from .execution_metrics import ExecutionMetrics
from .execution_patterns import PatternDetection
from .execution_recommendations import Recommendation


@dataclass
class ExecutionAuditReport:
    """Complete execution audit report."""

    generated_at: str
    total_trades: int
    metrics: ExecutionMetrics
    patterns: List[PatternDetection]
    recommendations: List[Recommendation]
    summary: str


def generate_summary(
    metrics: ExecutionMetrics,
    patterns: List[PatternDetection],
    recommendations: List[Recommendation],
) -> str:
    """Generate executive summary."""
    detected_patterns = [p for p in patterns if p.detected]
    critical_patterns = [p for p in detected_patterns if p.severity == "CRITICAL"]
    high_priority_recommendations = [r for r in recommendations if r.condition_met and r.priority in ("CRITICAL", "HIGH")]

    lines = []

    if metrics.total_trades == 0:
        return "Insufficient trade data for audit."

    lines.append(f"Analyzed {metrics.total_trades} closed trades.")

    if metrics.ev_total >= 0:
        lines.append(f"Expected Value: {metrics.ev_total:.4f} (positive edge detected).")
    else:
        lines.append(f"Expected Value: {metrics.ev_total:.4f} (negative edge, system degrading).")

    lines.append(f"Model/Execution Matrix: MC/EC={metrics.mc_ec_count}, MC/EW={metrics.mc_ew_count}, MW/EC={metrics.mw_ec_count}, MW/EW={metrics.mw_ew_count}.")

    if critical_patterns:
        lines.append(f"CRITICAL: {len(critical_patterns)} critical patterns detected: {', '.join(p.pattern_name for p in critical_patterns)}.")

    if detected_patterns:
        lines.append(f"Detected {len(detected_patterns)} execution issues.")

    if high_priority_recommendations:
        lines.append(f"{len(high_priority_recommendations)} high-priority recommendations generated.")
    else:
        lines.append("No critical recommendations at this time.")

    return " ".join(lines)


def format_report_text(report: ExecutionAuditReport) -> str:
    """Format report as human-readable text."""
    lines = []

    lines.append("=" * 80)
    lines.append("EXECUTION AUDIT REPORT")
    lines.append("=" * 80)
    lines.append(f"Generated: {report.generated_at}")
    lines.append(f"Total Trades: {report.total_trades}")
    lines.append("")

    lines.append("SUMMARY")
    lines.append("-" * 80)
    lines.append(report.summary)
    lines.append("")

    if report.total_trades == 0:
        lines.append("No trade data available for detailed metrics.")
        lines.append("=" * 80)
        return "\n".join(lines)

    lines.append("METRICS")
    lines.append("-" * 80)
    m = report.metrics
    lines.append(f"Average MAE: {m.avg_mae:.4f}")
    lines.append(f"Average MFE: {m.avg_mfe:.4f}")
    lines.append(f"Average PCR: {m.avg_pcr:.4f}")
    lines.append(f"Average Profit Leakage: {m.avg_pl:.4f}")
    lines.append(f"Average EQS: {m.avg_eqs:.4f}")
    lines.append(f"Average EE: {m.avg_ee:.4f}")
    lines.append(f"Median Hold Time: {m.median_hold_time_hours:.2f} hours")
    lines.append(f"Max Drawdown: {m.max_drawdown:.4f}")
    lines.append("")

    lines.append("MODEL/EXECUTION CLASSIFICATION")
    lines.append("-" * 80)
    lines.append(f"MC/EC (Model Correct, Execution Correct): {m.mc_ec_count} ({m.mc_ec_count/m.total_trades*100:.1f}%)")
    lines.append(f"MC/EW (Model Correct, Execution Weak): {m.mc_ew_count} ({m.mc_ew_count/m.total_trades*100:.1f}%)")
    lines.append(f"MW/EC (Model Weak, Execution Correct): {m.mw_ec_count} ({m.mw_ec_count/m.total_trades*100:.1f}%)")
    lines.append(f"MW/EW (Model Weak, Execution Weak): {m.mw_ew_count} ({m.mw_ew_count/m.total_trades*100:.1f}%)")
    lines.append("")

    lines.append("EXPECTED VALUE DECOMPOSITION")
    lines.append("-" * 80)
    lines.append(f"EV(MC/EC): {m.ev_mc_ec:.6f}")
    lines.append(f"EV(MC/EW): {m.ev_mc_ew:.6f}")
    lines.append(f"EV(MW/EC): {m.ev_mw_ec:.6f}")
    lines.append(f"EV(MW/EW): {m.ev_mw_ew:.6f}")
    lines.append(f"Total EV: {m.ev_total:.6f}")
    lines.append("")

    detected_patterns = [p for p in report.patterns if p.detected]
    if detected_patterns:
        lines.append("DETECTED PATTERNS")
        lines.append("-" * 80)
        for pattern in detected_patterns:
            lines.append(f"[{pattern.severity}] {pattern.pattern_name}")
            lines.append(f"  {pattern.description}")
            lines.append(f"  Affected trades: {pattern.count}")
            lines.append("")
    else:
        lines.append("DETECTED PATTERNS")
        lines.append("-" * 80)
        lines.append("No execution patterns detected.")
        lines.append("")

    active_recommendations = [r for r in report.recommendations if r.condition_met]
    if active_recommendations:
        lines.append("RECOMMENDATIONS")
        lines.append("-" * 80)
        for rec in active_recommendations:
            lines.append(f"[{rec.priority}] {rec.rule_name}")
            lines.append(f"  Action: {rec.action}")
            lines.append(f"  Rationale: {rec.rationale}")
            lines.append("")
    else:
        lines.append("RECOMMENDATIONS")
        lines.append("-" * 80)
        lines.append("No actionable recommendations at this time.")
        lines.append("")

    lines.append("=" * 80)

    return "\n".join(lines)


def format_report_json(report: ExecutionAuditReport) -> Dict:
    """Format report as JSON-serializable dict."""
    return {
        "generated_at": report.generated_at,
        "total_trades": report.total_trades,
        "summary": report.summary,
        "metrics": asdict(report.metrics),
        "patterns": [asdict(p) for p in report.patterns],
        "recommendations": [asdict(r) for r in report.recommendations],
    }


def create_report(
    metrics: ExecutionMetrics,
    patterns: List[PatternDetection],
    recommendations: List[Recommendation],
) -> ExecutionAuditReport:
    """Create execution audit report."""
    summary = generate_summary(metrics, patterns, recommendations)

    return ExecutionAuditReport(
        generated_at=datetime.utcnow().isoformat() + "Z",
        total_trades=metrics.total_trades,
        metrics=metrics,
        patterns=patterns,
        recommendations=recommendations,
        summary=summary,
    )
