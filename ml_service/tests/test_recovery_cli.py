import os
import json
import pytest
from unittest import mock
from click.testing import CliRunner

from ml_service.cli.commands import cli
from ml_service.migrations.recovery.orchestrator import RecoveryOrchestrator
from ml_service.migrations.recovery.models import (
    RecoveryDecision,
    SchemaDifference,
    DifferenceType,
    RecoveryClassification,
    RecoveryRisk,
    RecoveryRecommendation,
    ExecutionSummary,
    ExecutionResult,
    ExecutionStatus,
)


@pytest.fixture
def cli_runner():
    return CliRunner()


@pytest.fixture
def mock_orchestrator():
    with mock.patch("ml_service.migrations.recovery.orchestrator.RecoveryOrchestrator", autospec=True) as mock_class:
        yield mock_class


def test_inspect_clean_db(cli_runner, mock_orchestrator):
    """Test `inspect` command when no drift is detected."""
    instance = mock_orchestrator.return_value
    instance.run_diagnostics.return_value = ()

    # Test Text Format
    result = cli_runner.invoke(cli, ["db", "inspect", "--format", "text"])
    assert result.exit_code == 0
    assert "No drift detected" in result.output

    # Test JSON Format
    result = cli_runner.invoke(cli, ["db", "inspect", "--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["status"] == "CLEAN"
    assert data["decisions"] == []


def test_inspect_drift_detected(cli_runner, mock_orchestrator):
    """Test `inspect` command when drift is detected (returns exit code 2)."""
    diff = SchemaDifference(
        difference_type=DifferenceType.MISSING_COLUMN,
        table_name="experiments",
        column_name="hyperparameters"
    )
    decision = RecoveryDecision(
        difference=diff,
        classification=RecoveryClassification.SCHEMA_DRIFT,
        risk=RecoveryRisk.MEDIUM,
        recommendation=RecoveryRecommendation.FORWARD_MIGRATION,
        rationale="Missing column test rationale"
    )

    instance = mock_orchestrator.return_value
    instance.run_diagnostics.return_value = (decision,)

    # Test Text Format
    result = cli_runner.invoke(cli, ["db", "inspect", "--format", "text"])
    assert result.exit_code == 2
    assert "DRIFT DETECTED" in result.output
    assert "experiments" in result.output
    assert "hyperparameters" in result.output

    # Test JSON Format
    result = cli_runner.invoke(cli, ["db", "inspect", "--format", "json"])
    assert result.exit_code == 2
    data = json.loads(result.output)
    assert data["status"] == "DRIFT_DETECTED"
    assert len(data["decisions"]) == 1
    assert data["decisions"][0]["difference"]["table_name"] == "experiments"
    assert data["decisions"][0]["risk"] == "MEDIUM"


def test_recover_clean_db(cli_runner, mock_orchestrator):
    """Test `recover` command when no decisions are computed."""
    instance = mock_orchestrator.return_value
    instance.run_diagnostics.return_value = ()

    result = cli_runner.invoke(cli, ["db", "recover", "--format", "text"])
    assert result.exit_code == 0
    assert "No recovery decisions to execute" in result.output

    result = cli_runner.invoke(cli, ["db", "recover", "--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["status"] == "SUCCESS"
    assert "No recovery decisions" in data["message"]


def test_recover_dry_run(cli_runner, mock_orchestrator):
    """Test `recover` with dry-run mode enabled."""
    diff = SchemaDifference(
        difference_type=DifferenceType.MISSING_COLUMN,
        table_name="experiments",
        column_name="hyperparameters"
    )
    decision = RecoveryDecision(
        difference=diff,
        classification=RecoveryClassification.SCHEMA_DRIFT,
        risk=RecoveryRisk.MEDIUM,
        recommendation=RecoveryRecommendation.FORWARD_MIGRATION,
        rationale="Missing column test rationale"
    )

    instance = mock_orchestrator.return_value
    instance.run_diagnostics.return_value = (decision,)

    # Dry-run text
    result = cli_runner.invoke(cli, ["db", "recover", "--dry-run", "--format", "text"])
    assert result.exit_code == 0
    assert "[DRY-RUN]" in result.output
    assert "FORWARD_MIGRATION" in result.output
    instance.apply_recovery.assert_not_called()

    # Dry-run JSON
    result = cli_runner.invoke(cli, ["db", "recover", "--dry-run", "--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["status"] == "DRY_RUN"
    assert data["summary"]["total_drift_items"] == 1


def test_recover_low_risk_apply(cli_runner, mock_orchestrator):
    """Test standard apply flow for LOW risk decisions (no token required)."""
    diff = SchemaDifference(
        difference_type=DifferenceType.MISSING_INDEX,
        table_name="experiments",
        index_name="idx_exp_status"
    )
    decision = RecoveryDecision(
        difference=diff,
        classification=RecoveryClassification.SCHEMA_DRIFT,
        risk=RecoveryRisk.LOW,
        recommendation=RecoveryRecommendation.FORWARD_MIGRATION,
        rationale="Missing index test rationale"
    )

    instance = mock_orchestrator.return_value
    instance.run_diagnostics.return_value = (decision,)

    exec_result = ExecutionResult(
        decision=decision,
        status=ExecutionStatus.SUCCESS,
        duration_ms=10.5,
        executed_sql=("CREATE INDEX idx_exp_status ON experiments(status);",),
        rolled_back=False,
        timestamp="2026-07-30T08:20:00Z"
    )
    summary = ExecutionSummary(
        total_decisions=1,
        successful_executions=1,
        failed_executions=0,
        skipped_executions=0,
        total_duration_ms=10.5,
        results=(exec_result,)
    )
    instance.apply_recovery.return_value = (summary, "/mock/audit/log.json")

    result = cli_runner.invoke(cli, ["db", "recover", "--non-interactive", "--format", "text"])
    assert result.exit_code == 0
    assert "MOROQUANT DATABASE RECOVERY EXECUTION SUMMARY" in result.output
    assert "SUCCESS [FORWARD_MIGRATION]" in result.output
    assert "Audit Report:     /mock/audit/log.json" in result.output


def test_recover_high_risk_token_gate_fails(cli_runner, mock_orchestrator):
    """Test high risk decisions block execution when token is missing/mismatched in non-interactive mode."""
    diff = SchemaDifference(
        difference_type=DifferenceType.EXTRA_COLUMN,
        table_name="positions",
        column_name="untracked_metric"
    )
    decision = RecoveryDecision(
        difference=diff,
        classification=RecoveryClassification.MANUAL_DATABASE_MODIFICATION,
        risk=RecoveryRisk.HIGH,
        recommendation=RecoveryRecommendation.MANUAL_PATCH,
        rationale="Extra column design test"
    )

    instance = mock_orchestrator.return_value
    instance.run_diagnostics.return_value = (decision,)

    # Mismatched/missing token in non-interactive
    with mock.patch.dict(os.environ, {"MQ_CTO_APPROVAL_TOKEN": "correct_token"}):
        result = cli_runner.invoke(cli, ["db", "recover", "--non-interactive", "--approve-token", "wrong_token", "--format", "text"])
        assert result.exit_code == 1
        assert "Approval token missing or mismatched" in result.output
        instance.apply_recovery.assert_not_called()


def test_recover_high_risk_token_gate_success(cli_runner, mock_orchestrator):
    """Test high risk decisions execute successfully when token matches in non-interactive mode."""
    diff = SchemaDifference(
        difference_type=DifferenceType.EXTRA_COLUMN,
        table_name="positions",
        column_name="untracked_metric"
    )
    decision = RecoveryDecision(
        difference=diff,
        classification=RecoveryClassification.MANUAL_DATABASE_MODIFICATION,
        risk=RecoveryRisk.HIGH,
        recommendation=RecoveryRecommendation.MANUAL_PATCH,
        rationale="Extra column design test"
    )

    instance = mock_orchestrator.return_value
    instance.run_diagnostics.return_value = (decision,)

    exec_result = ExecutionResult(
        decision=decision,
        status=ExecutionStatus.SUCCESS,
        duration_ms=5.0,
        executed_sql=("-- manual patch execution log",),
        rolled_back=False,
        timestamp="2026-07-30T08:20:00Z"
    )
    summary = ExecutionSummary(
        total_decisions=1,
        successful_executions=1,
        failed_executions=0,
        skipped_executions=0,
        total_duration_ms=5.0,
        results=(exec_result,)
    )
    instance.apply_recovery.return_value = (summary, "/mock/audit/log.json")

    with mock.patch.dict(os.environ, {"MQ_CTO_APPROVAL_TOKEN": "correct_token"}):
        result = cli_runner.invoke(cli, [
            "db", "recover",
            "--non-interactive",
            "--approve-token", "correct_token",
            "--format", "json"
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["status"] == "SUCCESS"
        assert data["audit_report"] == "/mock/audit/log.json"


def test_recover_interactive_abort(cli_runner, mock_orchestrator):
    """Test that interactive mode aborts if the operator does not confirm correctly."""
    diff = SchemaDifference(
        difference_type=DifferenceType.EXTRA_COLUMN,
        table_name="positions",
        column_name="untracked_metric"
    )
    decision = RecoveryDecision(
        difference=diff,
        classification=RecoveryClassification.MANUAL_DATABASE_MODIFICATION,
        risk=RecoveryRisk.HIGH,
        recommendation=RecoveryRecommendation.MANUAL_PATCH,
        rationale="Extra column design test"
    )

    instance = mock_orchestrator.return_value
    instance.run_diagnostics.return_value = (decision,)

    # Interactive input is not 'I UNDERSTAND'
    result = cli_runner.invoke(cli, ["db", "recover", "--interactive", "--format", "text"], input="NO\n")
    assert result.exit_code == 1
    assert "Aborted" in result.output
    instance.apply_recovery.assert_not_called()


def test_recover_interactive_confirm(cli_runner, mock_orchestrator):
    """Test that interactive mode proceeds if the operator confirms correctly."""
    diff = SchemaDifference(
        difference_type=DifferenceType.EXTRA_COLUMN,
        table_name="positions",
        column_name="untracked_metric"
    )
    decision = RecoveryDecision(
        difference=diff,
        classification=RecoveryClassification.MANUAL_DATABASE_MODIFICATION,
        risk=RecoveryRisk.HIGH,
        recommendation=RecoveryRecommendation.MANUAL_PATCH,
        rationale="Extra column design test"
    )

    instance = mock_orchestrator.return_value
    instance.run_diagnostics.return_value = (decision,)

    exec_result = ExecutionResult(
        decision=decision,
        status=ExecutionStatus.SUCCESS,
        duration_ms=5.0,
        executed_sql=("-- manual patch execution log",),
        rolled_back=False,
        timestamp="2026-07-30T08:20:00Z"
    )
    summary = ExecutionSummary(
        total_decisions=1,
        successful_executions=1,
        failed_executions=0,
        skipped_executions=0,
        total_duration_ms=5.0,
        results=(exec_result,)
    )
    instance.apply_recovery.return_value = (summary, "/mock/audit/log.json")

    # Interactive input is 'I UNDERSTAND'
    result = cli_runner.invoke(cli, ["db", "recover", "--interactive", "--format", "text"], input="I UNDERSTAND\n")
    assert result.exit_code == 0
    assert "MOROQUANT DATABASE RECOVERY EXECUTION SUMMARY" in result.output
    instance.apply_recovery.assert_called_once()
