"""Unit tests for the RecoveryReporter (Sprint 2.3C Commit 5).

Tests compilation, determinism, JSON serialization, filesystem persistence,
path protection, error raising, and reading of recovery audit reports.
"""

import os
import json
import tempfile
from datetime import datetime, UTC
import pytest

from ml_service.migrations.recovery.models import (
    DifferenceType,
    ExecutionResult,
    ExecutionStatus,
    RecoveryClassification,
    RecoveryDecision,
    RecoveryRecommendation,
    RecoveryRisk,
    SchemaDifference,
)
from ml_service.migrations.recovery.reporter import RecoveryReporter, ReporterError


@pytest.fixture
def sample_results():
    diff1 = SchemaDifference(
        difference_type=DifferenceType.MISSING_COLUMN,
        table_name="trades",
        column_name="execution_time",
    )
    dec1 = RecoveryDecision(
        difference=diff1,
        classification=RecoveryClassification.SCHEMA_DRIFT,
        risk=RecoveryRisk.HIGH,
        recommendation=RecoveryRecommendation.FORWARD_MIGRATION,
        rationale="Column execution_time is missing",
    )
    res1 = ExecutionResult(
        decision=dec1,
        status=ExecutionStatus.SUCCESS,
        duration_ms=45.2,
        executed_sql=("ALTER TABLE trades ADD COLUMN execution_time TEXT;",),
        rolled_back=False,
        timestamp="2026-07-29T19:10:00Z",
    )

    diff2 = SchemaDifference(
        difference_type=DifferenceType.EXTRA_TABLE,
        table_name="execution_decisions_old",
    )
    dec2 = RecoveryDecision(
        difference=diff2,
        classification=RecoveryClassification.REPLAY_CONFLICT,
        risk=RecoveryRisk.LOW,
        recommendation=RecoveryRecommendation.SAFE_SKIP,
        rationale="Table already deleted downstream",
    )
    res2 = ExecutionResult(
        decision=dec2,
        status=ExecutionStatus.SKIPPED,
        duration_ms=10.0,
        executed_sql=(),
        rolled_back=False,
        timestamp="2026-07-29T19:10:05Z",
    )

    diff3 = SchemaDifference(
        difference_type=DifferenceType.COLUMN_TYPE_MISMATCH,
        table_name="experiments",
        column_name="id",
    )
    dec3 = RecoveryDecision(
        difference=diff3,
        classification=RecoveryClassification.UNKNOWN_STATE,
        risk=RecoveryRisk.CRITICAL,
        recommendation=RecoveryRecommendation.HALT,
        rationale="Primary key ID type mismatched",
    )
    res3 = ExecutionResult(
        decision=dec3,
        status=ExecutionStatus.FAILED,
        duration_ms=5.5,
        executed_sql=(),
        rolled_back=True,
        timestamp="2026-07-29T19:10:10Z",
        error_message="Recovery halted",
    )

    return (res1, res2, res3)


class TestRecoveryReporterCompilation:
    """Verify aggregation metrics compiled from execution results."""

    def test_compile_summary(self, sample_results):
        summary = RecoveryReporter.compile_summary(sample_results)
        assert summary.total_decisions == 3
        assert summary.successful_executions == 1
        assert summary.skipped_executions == 1
        assert summary.failed_executions == 1
        assert summary.total_duration_ms == 60.7
        assert summary.results == sample_results

    def test_compile_summary_empty(self):
        summary = RecoveryReporter.compile_summary(())
        assert summary.total_decisions == 0
        assert summary.successful_executions == 0
        assert summary.skipped_executions == 0
        assert summary.failed_executions == 0
        assert summary.total_duration_ms == 0.0
        assert summary.results == ()

    def test_compile_summary_type_validation(self):
        with pytest.raises(TypeError):
            # Must be tuple, not list
            RecoveryReporter.compile_summary([])

        with pytest.raises(TypeError):
            # Must contain only ExecutionResult elements
            RecoveryReporter.compile_summary((1, 2, 3))  # type: ignore


class TestRecoveryReporterSerialization:
    """Verify deterministic JSON serialization rules."""

    def test_serialize_summary_determinism(self, sample_results):
        summary = RecoveryReporter.compile_summary(sample_results)
        t = datetime(2026, 7, 29, 19, 30, 0, tzinfo=UTC)
        
        json_str_1 = RecoveryReporter.serialize_summary(summary, "test_op", report_time=t)
        json_str_2 = RecoveryReporter.serialize_summary(summary, "test_op", report_time=t)
        
        # Byte-for-byte matching check
        assert json_str_1 == json_str_2

        # Verify parsed dict structures
        parsed = json.loads(json_str_1)
        assert parsed["operator"] == "test_op"
        assert parsed["report_timestamp"] == "2026-07-29T19:30:00Z"
        assert parsed["summary"]["total_decisions"] == 3
        assert parsed["summary"]["successful_executions"] == 1

        # Check key alphabetical sorting at first-level
        first_level_keys = list(parsed.keys())
        assert first_level_keys == sorted(first_level_keys)

    def test_serialize_summary_types(self):
        with pytest.raises(TypeError):
            RecoveryReporter.serialize_summary(None, "op")  # type: ignore
        with pytest.raises(TypeError):
            RecoveryReporter.serialize_summary(RecoveryReporter.compile_summary(()), 123)  # type: ignore


class TestRecoveryReporterFileOperations:
    """Verify writing, reading, directory bounds protection, and filesystem errors."""

    def test_write_and_read_report(self, sample_results):
        t = datetime(2026, 7, 29, 19, 30, 0, tzinfo=UTC)
        with tempfile.TemporaryDirectory() as tmp_dir:
            summary, file_path = RecoveryReporter.write_report(
                sample_results, "test_user", output_dir=tmp_dir, report_time=t
            )
            
            assert summary.total_decisions == 3
            assert os.path.exists(file_path)
            assert os.path.basename(file_path) == "recovery_audit_20260729_193000.json"
            
            # Read and verify content
            loaded = RecoveryReporter.read_report(file_path)
            assert loaded["operator"] == "test_user"
            assert loaded["report_timestamp"] == "2026-07-29T19:30:00Z"
            assert loaded["summary"]["total_decisions"] == 3

    def test_write_report_directory_creation(self, sample_results):
        with tempfile.TemporaryDirectory() as tmp_dir:
            nested_dir = os.path.join(tmp_dir, "nested", "audit_logs")
            # Should automatically create directory
            _, file_path = RecoveryReporter.write_report(
                sample_results, "runner", output_dir=nested_dir
            )
            assert os.path.exists(file_path)
            assert os.path.dirname(file_path) == nested_dir

    def test_write_report_traversal_protection(self, sample_results):
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Inject traversal in output_dir
            invalid_dir = os.path.join(tmp_dir, "dir", "..", "..", "unauthorized")
            # Path matching validation check
            with pytest.raises(ReporterError):
                RecoveryReporter.write_report(
                    sample_results, "runner", output_dir=invalid_dir
                )

    def test_write_report_write_failure_raises(self, sample_results):
        # Point to a path that is not a directory but a file, causing write failure
        with tempfile.NamedTemporaryFile() as tmp_file:
            with pytest.raises(ReporterError):
                RecoveryReporter.write_report(
                    sample_results, "runner", output_dir=tmp_file.name
                )

    def test_read_report_failure(self):
        with pytest.raises(ReporterError):
            RecoveryReporter.read_report("/non/existent/path/report.json")
