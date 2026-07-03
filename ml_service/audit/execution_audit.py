"""Execution Audit Framework.

Main orchestrator for the Execution Audit Framework as defined in
docs/research/execution_audit_framework.md.

This module coordinates metrics computation, pattern detection, and
recommendation generation to identify the precise drivers of alpha degradation.
"""

import json
import sys
from pathlib import Path
from typing import Optional

from ml_service.utils.logger import get_logger

from .execution_metrics import compute_all_metrics, load_trade_data
from .execution_patterns import detect_all_patterns
from .execution_recommendations import generate_all_recommendations
from .execution_report import (
    ExecutionAuditReport,
    create_report,
    format_report_json,
    format_report_text,
)

logger = get_logger()


def run_execution_audit(
    output_format: str = "text",
    output_path: Optional[Path] = None,
) -> ExecutionAuditReport:
    """Run complete execution audit.

    Args:
        output_format: 'text' or 'json'
        output_path: Optional file path to write report

    Returns:
        ExecutionAuditReport
    """
    logger.info("Starting execution audit")

    trades = load_trade_data()
    logger.info(f"Loaded {len(trades)} closed trades")

    if len(trades) == 0:
        logger.warning("No closed trades found, cannot perform audit")
        report = create_report(
            metrics=compute_all_metrics([]),
            patterns=[],
            recommendations=[],
        )
        return report

    logger.info("Computing execution metrics")
    metrics = compute_all_metrics(trades)

    logger.info("Detecting execution patterns")
    patterns = detect_all_patterns(trades)

    logger.info("Generating recommendations")
    recommendations = generate_all_recommendations(metrics, trades, patterns)

    logger.info("Creating audit report")
    report = create_report(metrics, patterns, recommendations)

    if output_path:
        logger.info(f"Writing report to {output_path}")
        if output_format == "json":
            report_data = format_report_json(report)
            output_path.write_text(json.dumps(report_data, indent=2))
        else:
            report_text = format_report_text(report)
            output_path.write_text(report_text)

    logger.info("Execution audit complete")
    return report


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Run Execution Audit Framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m audit.execution_audit
  python -m audit.execution_audit --format json
  python -m audit.execution_audit --output report.txt
  python -m audit.execution_audit --format json --output report.json
        """,
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Output file path (default: stdout)",
    )

    args = parser.parse_args()

    try:
        report = run_execution_audit(
            output_format=args.format,
            output_path=args.output,
        )

        if not args.output:
            if args.format == "json":
                print(json.dumps(format_report_json(report), indent=2))
            else:
                print(format_report_text(report))

        detected_patterns = [p for p in report.patterns if p.detected]
        critical_patterns = [p for p in detected_patterns if p.severity == "CRITICAL"]

        if critical_patterns:
            logger.warning(f"CRITICAL: {len(critical_patterns)} critical patterns detected")
            sys.exit(2)
        elif detected_patterns:
            logger.info(f"Detected {len(detected_patterns)} execution issues")
            sys.exit(1)
        else:
            logger.info("No execution issues detected")
            sys.exit(0)

    except Exception as e:
        logger.error(f"Execution audit failed: {e}", exc_info=True)
        sys.exit(3)


if __name__ == "__main__":
    main()
