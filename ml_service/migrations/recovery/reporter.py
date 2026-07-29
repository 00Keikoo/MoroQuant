"""Recovery reporter for serializing and writing recovery execution logs.

Implements MoroQuant-Sprint-2.3C-Reporter-v1.0.
"""

import os
import json
from datetime import datetime, UTC
from typing import Tuple, Optional, Dict, Any

from ml_service.migrations.recovery.models import (
    ExecutionResult,
    ExecutionSummary,
    ExecutionStatus,
)


class ReporterError(Exception):
    """Base exception for reporting issues (e.g. disk write failures)."""
    pass


class RecoveryReporter:
    """Consumes execution results to generate and write immutable, deterministic audit logs."""

    @staticmethod
    def compile_summary(results: Tuple[ExecutionResult, ...]) -> ExecutionSummary:
        """Aggregates execution results into an immutable ExecutionSummary object.

        Args:
            results: Tuple of executed results from the RecoveryExecutor.

        Returns:
            An immutable ExecutionSummary instance.
        """
        if not isinstance(results, tuple):
            raise TypeError(f"results must be a tuple, got {type(results).__name__}")

        total_decisions = len(results)
        successful_executions = 0
        failed_executions = 0
        skipped_executions = 0
        total_duration_ms = 0.0

        for res in results:
            if not isinstance(res, ExecutionResult):
                raise TypeError(
                    f"All items must be ExecutionResult, got {type(res).__name__}"
                )
            
            if res.status == ExecutionStatus.SUCCESS:
                successful_executions += 1
            elif res.status == ExecutionStatus.FAILED:
                failed_executions += 1
            elif res.status == ExecutionStatus.SKIPPED:
                skipped_executions += 1
            
            total_duration_ms += res.duration_ms

        return ExecutionSummary(
            total_decisions=total_decisions,
            successful_executions=successful_executions,
            failed_executions=failed_executions,
            skipped_executions=skipped_executions,
            total_duration_ms=total_duration_ms,
            results=results,
        )

    @staticmethod
    def serialize_summary(
        summary: ExecutionSummary,
        operator: str,
        report_time: Optional[datetime] = None,
    ) -> str:
        """Serializes the summary and execution telemetry to a deterministic JSON string.

        Guarantees:
        - Sorted keys (alphabetical stable sorting).
        - Human-readable indentation (4 spaces).
        - Consistent UTF-8 formatting.
        - ISO-8601 UTC timestamps ending with 'Z'.

        Args:
            summary: Consolidated ExecutionSummary.
            operator: Identifier of the operator run context.
            report_time: Optional timestamp for testing.

        Returns:
            Deterministic JSON formatted string.
        """
        if not isinstance(summary, ExecutionSummary):
            raise TypeError(f"summary must be ExecutionSummary, got {type(summary).__name__}")
        if not isinstance(operator, str):
            raise TypeError(f"operator must be a string, got {type(operator).__name__}")

        if report_time is None:
            timestamp = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        else:
            if report_time.tzinfo is None:
                timestamp = report_time.replace(tzinfo=UTC).isoformat().replace("+00:00", "Z")
            else:
                timestamp = report_time.astimezone(UTC).isoformat().replace("+00:00", "Z")

        report_dict = {
            "operator": operator,
            "report_timestamp": timestamp,
            "summary": summary.to_dict(),
        }

        # sort_keys=True ensures deterministic stable ordering of keys at all levels
        return json.dumps(report_dict, sort_keys=True, indent=4)

    @classmethod
    def write_report(
        cls,
        results: Tuple[ExecutionResult, ...],
        operator: str,
        output_dir: str = "storage/reports/recovery_audit",
        report_time: Optional[datetime] = None,
    ) -> Tuple[ExecutionSummary, str]:
        """Orchestrates summary compilation, deterministic serialization, and file I/O.

        Guarantees directory creation, permission integrity, and path bounds safety.

        Args:
            results: Tuple of completed ExecutionResults.
            operator: Name or system context triggering execution.
            output_dir: Root location where audit files are stored.
            report_time: Optional timestamp (injectable for testing).

        Returns:
            Tuple containing:
            1. Immutable ExecutionSummary
            2. Fully resolved absolute path to the written audit log.

        Raises:
            ReporterError: If file writing or directory creation fails.
        """
        summary = cls.compile_summary(results)
        
        # Build deterministic timestamp for filename
        if report_time is None:
            dt = datetime.now(UTC)
        else:
            dt = report_time if report_time.tzinfo is not None else report_time.replace(tzinfo=UTC)
            
        timestamp_str = dt.strftime("%Y%m%d_%H%M%S")
        filename = f"recovery_audit_{timestamp_str}.json"
        
        # Check for relative directory traversal back-references in raw output_dir
        path_parts = output_dir.split(os.path.sep)
        if ".." in path_parts:
            raise ReporterError(f"Directory traversal detected in output_dir: {output_dir}")

        try:
            # Resolve directory safely
            abs_output_dir = os.path.abspath(output_dir)
            os.makedirs(abs_output_dir, mode=0o755, exist_ok=True)
            
            file_path = os.path.join(abs_output_dir, filename)
            
            # Prevent directory traversal in finalized output filename path
            if not file_path.startswith(abs_output_dir):
                raise ReporterError(f"Target path {file_path} is outside of base directory {abs_output_dir}")

            serialized = cls.serialize_summary(summary, operator, report_time=dt)
            
            # Fail-safe write: write to a temporary file first, then rename atomically
            tmp_path = file_path + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                f.write(serialized)
            
            os.replace(tmp_path, file_path)
            
            return summary, file_path
        except Exception as e:
            if isinstance(e, ReporterError):
                raise
            raise ReporterError(f"Failed to persist recovery audit report: {e}") from e

    @staticmethod
    def read_report(file_path: str) -> Dict[str, Any]:
        """Reads and parses an audit report from disk for CLI ingestion.

        Args:
            file_path: Target log file.

        Returns:
            Dictionary containing parsed JSON contents.
            
        Raises:
            ReporterError: If reading fails or the JSON is malformed.
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            raise ReporterError(f"Failed to read recovery audit report: {e}") from e
