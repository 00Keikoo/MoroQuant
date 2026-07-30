"""Unit tests for the RecoveryOrchestrator component.

Verifies coordination of SchemaInspector, DecisionAnalyzer, RecoveryExecutor,
and RecoveryReporter without direct database or filesystem writes from the orchestrator.
"""

import os
import pytest
from unittest.mock import MagicMock, patch

from ml_service.migrations.recovery.orchestrator import RecoveryOrchestrator
from ml_service.migrations.recovery.executor import ApprovalRequiredError
from ml_service.migrations.recovery.models import (
    SchemaDifference,
    DifferenceType,
    RecoveryDecision,
    RecoveryClassification,
    RecoveryRisk,
    RecoveryRecommendation,
    ExecutionResult,
    ExecutionStatus,
    ExecutionSummary,
)


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.db_path = "/tmp/mock_recovery.db"
    return db


@pytest.fixture
def mock_inspector_class():
    inspector_class = MagicMock()
    inspector = MagicMock()
    inspector_class.return_value = inspector
    return inspector_class


@pytest.fixture
def mock_analyzer_class():
    analyzer_class = MagicMock()
    analyzer = MagicMock()
    analyzer_class.return_value = analyzer
    return analyzer_class


@pytest.fixture
def mock_executor_class():
    executor_class = MagicMock()
    executor = MagicMock()
    executor_class.return_value = executor
    return executor_class


@pytest.fixture
def mock_reporter_class():
    reporter_class = MagicMock()
    return reporter_class


class TestRecoveryOrchestratorDiagnostics:
    """Tests the run_diagnostics workflow of the orchestrator."""

    def test_run_diagnostics_delegation(
        self,
        mock_db,
        mock_inspector_class,
        mock_analyzer_class,
    ):
        orchestrator = RecoveryOrchestrator(
            db_path=mock_db,
            migrations_dir="/tmp/migrations",
            inspector_class=mock_inspector_class,
            analyzer_class=mock_analyzer_class,
        )

        differences = (
            SchemaDifference(
                difference_type=DifferenceType.MISSING_TABLE,
                table_name="users",
            ),
        )
        applied = ("001_initial",)
        available = ("001_initial.sql", "002_next.sql")
        checksums = {"001_initial.sql": "checksum1"}

        # Mock the internal state derivation to bypass filesystem/DB I/O
        orchestrator._derive_migration_state = MagicMock(
            return_value=(applied, available, checksums)
        )

        # Mock SchemaInspector methods
        mock_inspector = mock_inspector_class.return_value
        mock_inspector.detect_differences = MagicMock(return_value=differences)

        mock_analyzer = mock_analyzer_class.return_value
        mock_analyzer.analyze.return_value = (
            RecoveryDecision(
                difference=differences[0],
                classification=RecoveryClassification.SCHEMA_DRIFT,
                risk=RecoveryRisk.MEDIUM,
                recommendation=RecoveryRecommendation.FORWARD_MIGRATION,
                rationale="Test rationale",
            ),
        )

        results = orchestrator.run_diagnostics()

        # Assert SchemaInspector instantiation and capture_snapshot invoke
        mock_inspector_class.assert_called_once_with(mock_db)
        mock_inspector_class.return_value.capture_snapshot.assert_called_once()
        mock_inspector.detect_differences.assert_called_once()

        # Assert DecisionAnalyzer instantiation and analyze invoke
        mock_analyzer_class.assert_called_once()
        context = mock_analyzer_class.call_args[0][0]
        assert context.applied_migration_names == applied
        assert context.available_migration_files == available
        assert context.migration_checksums == checksums

        mock_analyzer.analyze.assert_called_once_with(differences)
        assert len(results) == 1
        assert isinstance(results, tuple)
        assert results[0].classification == RecoveryClassification.SCHEMA_DRIFT


class TestRecoveryOrchestratorRecovery:
    """Tests the apply_recovery workflow of the orchestrator."""

    def test_apply_recovery_success_low_risk(
        self,
        mock_db,
        mock_executor_class,
        mock_reporter_class,
    ):
        orchestrator = RecoveryOrchestrator(
            db_path=mock_db,
            migrations_dir="/tmp/migrations",
            executor_class=mock_executor_class,
            reporter_class=mock_reporter_class,
        )

        decision = RecoveryDecision(
            difference=SchemaDifference(
                difference_type=DifferenceType.EXTRA_TABLE,
                table_name="test_table",
            ),
            classification=RecoveryClassification.REPLAY_CONFLICT,
            risk=RecoveryRisk.LOW,
            recommendation=RecoveryRecommendation.FORCE_RECORD,
            rationale="Test rationale",
        )

        # Mock internal state derivation
        orchestrator._derive_migration_state = MagicMock(
            return_value=((), (), {})
        )

        mock_executor = mock_executor_class.return_value
        exec_result = ExecutionResult(
            decision=decision,
            status=ExecutionStatus.SUCCESS,
            duration_ms=5.0,
            executed_sql=("INSERT INTO schema_migrations...",),
            rolled_back=False,
            timestamp="2026-07-30T00:00:00Z",
        )
        mock_executor.execute.return_value = (exec_result,)

        expected_summary = ExecutionSummary(
            total_decisions=1,
            successful_executions=1,
            failed_executions=0,
            skipped_executions=0,
            total_duration_ms=5.0,
            results=(exec_result,),
        )
        mock_reporter_class.write_report.return_value = (
            expected_summary,
            "/tmp/report.json",
        )

        summary, path = orchestrator.apply_recovery(
            decisions=(decision,),
            operator="test_user",
        )

        # Assert executor delegation
        mock_executor_class.assert_called_once_with(
            mock_executor_class.call_args[0][0], mock_db.db_path
        )
        mock_executor.execute.assert_called_once_with((decision,))

        # Assert reporter delegation
        mock_reporter_class.write_report.assert_called_once_with(
            results=(exec_result,),
            operator="test_user",
            output_dir="storage/reports/recovery_audit",
        )

        assert summary == expected_summary
        assert path == "/tmp/report.json"

    def test_apply_recovery_high_risk_token_success(
        self,
        mock_db,
        mock_executor_class,
        mock_reporter_class,
    ):
        orchestrator = RecoveryOrchestrator(
            db_path=mock_db,
            migrations_dir="/tmp/migrations",
            executor_class=mock_executor_class,
            reporter_class=mock_reporter_class,
        )

        decision = RecoveryDecision(
            difference=SchemaDifference(
                difference_type=DifferenceType.COLUMN_TYPE_MISMATCH,
                table_name="users",
            ),
            classification=RecoveryClassification.SCHEMA_DRIFT,
            risk=RecoveryRisk.HIGH,
            recommendation=RecoveryRecommendation.FORWARD_MIGRATION,
            rationale="Test rationale",
        )

        # Mock internal state derivation
        orchestrator._derive_migration_state = MagicMock(
            return_value=((), (), {})
        )

        mock_executor = mock_executor_class.return_value
        exec_result = ExecutionResult(
            decision=decision,
            status=ExecutionStatus.SUCCESS,
            duration_ms=10.0,
            executed_sql=(),
            rolled_back=False,
            timestamp="2026-07-30T00:00:00Z",
        )
        mock_executor.execute.return_value = (exec_result,)

        expected_summary = ExecutionSummary(
            total_decisions=1,
            successful_executions=1,
            failed_executions=0,
            skipped_executions=0,
            total_duration_ms=10.0,
            results=(exec_result,),
        )
        mock_reporter_class.write_report.return_value = (
            expected_summary,
            "/tmp/report.json",
        )

        with patch.dict(os.environ, {"MQ_CTO_APPROVAL_TOKEN": "secure_token"}):
            summary, path = orchestrator.apply_recovery(
                decisions=(decision,),
                operator="test_user",
                approval_token="secure_token",
            )

        assert summary == expected_summary
        assert path == "/tmp/report.json"

    def test_apply_recovery_high_risk_token_failure(
        self,
        mock_db,
    ):
        orchestrator = RecoveryOrchestrator(
            db_path=mock_db,
            migrations_dir="/tmp/migrations",
        )

        decision = RecoveryDecision(
            difference=SchemaDifference(
                difference_type=DifferenceType.COLUMN_TYPE_MISMATCH,
                table_name="users",
            ),
            classification=RecoveryClassification.SCHEMA_DRIFT,
            risk=RecoveryRisk.HIGH,
            recommendation=RecoveryRecommendation.FORWARD_MIGRATION,
            rationale="Test rationale",
        )

        # Mock internal state derivation
        orchestrator._derive_migration_state = MagicMock(
            return_value=((), (), {})
        )

        with patch.dict(os.environ, {"MQ_CTO_APPROVAL_TOKEN": "secure_token"}):
            # Missing token
            with pytest.raises(ApprovalRequiredError) as exc_info:
                orchestrator.apply_recovery(
                    decisions=(decision,),
                    operator="test_user",
                )
            assert "requires CTO approval" in str(exc_info.value)

            # Incorrect token
            with pytest.raises(ApprovalRequiredError):
                orchestrator.apply_recovery(
                    decisions=(decision,),
                    operator="test_user",
                    approval_token="wrong_token",
                )

