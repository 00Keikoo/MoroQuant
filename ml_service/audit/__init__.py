"""Execution Audit Framework.

Implements the Execution Audit Framework as defined in
docs/research/execution_audit_framework.md.

Main entry point: execution_audit.run_execution_audit()
"""

from .execution_audit import run_execution_audit
from .execution_metrics import ExecutionMetrics, TradeData, compute_all_metrics
from .execution_patterns import PatternDetection, detect_all_patterns
from .execution_recommendations import Recommendation, generate_all_recommendations
from .execution_report import (
    ExecutionAuditReport,
    create_report,
    format_report_json,
    format_report_text,
)

__all__ = [
    "run_execution_audit",
    "ExecutionMetrics",
    "TradeData",
    "compute_all_metrics",
    "PatternDetection",
    "detect_all_patterns",
    "Recommendation",
    "generate_all_recommendations",
    "ExecutionAuditReport",
    "create_report",
    "format_report_json",
    "format_report_text",
]
