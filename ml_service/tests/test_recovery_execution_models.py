"""Unit tests for recovery execution models (Sprint 2.3C Commit 1).

Tests immutability, enum definitions, serialization, and construction of execution models.
"""

import pytest
from dataclasses import FrozenInstanceError

from ml_service.migrations.recovery.models import (
    DifferenceType,
    ExecutionResult,
    ExecutionStatus,
    ExecutionSummary,
    RecoveryClassification,
    RecoveryDecision,
    RecoveryRecommendation,
    RecoveryRisk,
    SchemaDifference,
)


@pytest.fixture
def sample_decision():
    diff = SchemaDifference(
        difference_type=DifferenceType.MISSING_COLUMN,
        table_name="trades",
        column_name="execution_time",
    )
    return RecoveryDecision(
        difference=diff,
        classification=RecoveryClassification.SCHEMA_DRIFT,
        risk=RecoveryRisk.HIGH,
        recommendation=RecoveryRecommendation.FORWARD_MIGRATION,
        rationale="Column execution_time is missing",
    )


class TestExecutionStatusEnum:
    """Verify ExecutionStatus enum keys and values."""

    def test_enum_values(self):
        assert ExecutionStatus.SUCCESS == "SUCCESS"
        assert ExecutionStatus.FAILED == "FAILED"
        assert ExecutionStatus.SKIPPED == "SKIPPED"


class TestExecutionResultModel:
    """Verify structure, immutability, and serialization of ExecutionResult."""

    def test_construction(self, sample_decision):
        result = ExecutionResult(
            decision=sample_decision,
            status=ExecutionStatus.SUCCESS,
            duration_ms=45.2,
            executed_sql=("ALTER TABLE trades ADD COLUMN execution_time TEXT;",),
            rolled_back=False,
            timestamp="2026-07-29T19:10:00Z",
            error_message=None,
        )
        assert result.decision == sample_decision
        assert result.status == ExecutionStatus.SUCCESS
        assert result.duration_ms == 45.2
        assert result.executed_sql == ("ALTER TABLE trades ADD COLUMN execution_time TEXT;",)
        assert result.rolled_back is False
        assert result.timestamp == "2026-07-29T19:10:00Z"
        assert result.error_message is None

    def test_immutability(self, sample_decision):
        result = ExecutionResult(
            decision=sample_decision,
            status=ExecutionStatus.SUCCESS,
            duration_ms=45.2,
            executed_sql=(),
            rolled_back=False,
            timestamp="2026-07-29T19:10:00Z",
        )
        with pytest.raises(FrozenInstanceError):
            result.status = ExecutionStatus.FAILED

    def test_serialization(self, sample_decision):
        result = ExecutionResult(
            decision=sample_decision,
            status=ExecutionStatus.SUCCESS,
            duration_ms=45.2,
            executed_sql=("ALTER TABLE trades ADD COLUMN execution_time TEXT;",),
            rolled_back=False,
            timestamp="2026-07-29T19:10:00Z",
            error_message="some error",
        )
        serialized = result.to_dict()
        assert isinstance(serialized, dict)
        assert serialized["status"] == "SUCCESS"
        assert serialized["duration_ms"] == 45.2
        assert serialized["executed_sql"] == ["ALTER TABLE trades ADD COLUMN execution_time TEXT;"]
        assert serialized["rolled_back"] is False
        assert serialized["timestamp"] == "2026-07-29T19:10:00Z"
        assert serialized["error_message"] == "some error"
        assert isinstance(serialized["decision"], dict)


class TestExecutionSummaryModel:
    """Verify structure, immutability, and serialization of ExecutionSummary."""

    def test_construction_and_serialization(self, sample_decision):
        res1 = ExecutionResult(
            decision=sample_decision,
            status=ExecutionStatus.SUCCESS,
            duration_ms=45.2,
            executed_sql=("ALTER TABLE trades ADD COLUMN execution_time TEXT;",),
            rolled_back=False,
            timestamp="2026-07-29T19:10:00Z",
        )
        res2 = ExecutionResult(
            decision=sample_decision,
            status=ExecutionStatus.FAILED,
            duration_ms=10.1,
            executed_sql=(),
            rolled_back=True,
            timestamp="2026-07-29T19:10:01Z",
            error_message="Connection timed out",
        )
        summary = ExecutionSummary(
            total_decisions=2,
            successful_executions=1,
            failed_executions=1,
            skipped_executions=0,
            total_duration_ms=55.3,
            results=(res1, res2),
        )

        assert summary.total_decisions == 2
        assert summary.successful_executions == 1
        assert summary.failed_executions == 1
        assert summary.skipped_executions == 0
        assert summary.total_duration_ms == 55.3
        assert summary.results == (res1, res2)

        # Immutability
        with pytest.raises(FrozenInstanceError):
            summary.total_decisions = 3

        # Serialization
        serialized = summary.to_dict()
        assert isinstance(serialized, dict)
        assert serialized["total_decisions"] == 2
        assert serialized["successful_executions"] == 1
        assert serialized["failed_executions"] == 1
        assert serialized["skipped_executions"] == 0
        assert serialized["total_duration_ms"] == 55.3
        assert isinstance(serialized["results"], list)
        assert len(serialized["results"]) == 2
        assert serialized["results"][0]["status"] == "SUCCESS"
        assert serialized["results"][1]["status"] == "FAILED"
        assert serialized["results"][1]["error_message"] == "Connection timed out"
