"""Tests for RecoveryExecutor skeleton implementation.

Sprint 2.3C Commit 2: Tests executor construction and placeholder execution logic.
"""

import pytest
from datetime import datetime

from ml_service.migrations.recovery.executor import RecoveryExecutor
from ml_service.migrations.recovery.models import (
    DecisionContext,
    RecoveryDecision,
    SchemaDifference,
    DifferenceType,
    RecoveryClassification,
    RecoveryRisk,
    RecoveryRecommendation,
    ExecutionResult,
    ExecutionStatus,
)


@pytest.fixture
def decision_context() -> DecisionContext:
    """Create a minimal decision context for testing."""
    return DecisionContext(
        applied_migration_names=("001_initial", "002_add_table"),
        available_migration_files=("001_initial.sql", "002_add_table.sql", "003_new.sql"),
        migration_checksums={
            "001_initial.sql": "abc123",
            "002_add_table.sql": "def456",
        }
    )


@pytest.fixture
def sample_decision() -> RecoveryDecision:
    """Create a sample recovery decision for testing."""
    difference = SchemaDifference(
        difference_type=DifferenceType.EXTRA_TABLE,
        target_migration="003_new",
        table_name="test_table",
    )
    return RecoveryDecision(
        difference=difference,
        classification=RecoveryClassification.REPLAY_CONFLICT,
        risk=RecoveryRisk.LOW,
        recommendation=RecoveryRecommendation.FORCE_RECORD,
        rationale="Test rationale",
    )


class TestRecoveryExecutorConstruction:
    """Test RecoveryExecutor constructor."""

    def test_constructor_accepts_decision_context(self, decision_context: DecisionContext):
        """Constructor should accept DecisionContext."""
        executor = RecoveryExecutor(decision_context)
        assert executor is not None
        assert executor._context is decision_context

    def test_constructor_stores_context_immutably(self, decision_context: DecisionContext):
        """Constructor should store context reference without mutation."""
        executor = RecoveryExecutor(decision_context)
        assert executor._context == decision_context
        assert executor._context.applied_migration_names == decision_context.applied_migration_names


class TestRecoveryExecutorExecute:
    """Test RecoveryExecutor.execute() method."""

    def test_execute_accepts_empty_tuple(self, decision_context: DecisionContext):
        """Execute should handle empty tuple of decisions."""
        executor = RecoveryExecutor(decision_context)
        results = executor.execute(())

        assert isinstance(results, tuple)
        assert len(results) == 0

    def test_execute_single_decision(
        self,
        decision_context: DecisionContext,
        sample_decision: RecoveryDecision
    ):
        """Execute should process single decision and return ExecutionResult."""
        executor = RecoveryExecutor(decision_context)
        results = executor.execute((sample_decision,))

        assert isinstance(results, tuple)
        assert len(results) == 1

        result = results[0]
        assert isinstance(result, ExecutionResult)
        assert result.decision is sample_decision
        assert result.status == ExecutionStatus.SKIPPED
        assert result.executed_sql == ()
        assert result.rolled_back is False
        assert result.error_message is None
        assert result.duration_ms == 0.0

    def test_execute_multiple_decisions(self, decision_context: DecisionContext):
        """Execute should process multiple decisions in order."""
        decision1 = RecoveryDecision(
            difference=SchemaDifference(
                difference_type=DifferenceType.MISSING_TABLE,
                target_migration="003",
                table_name="table1",
            ),
            classification=RecoveryClassification.MISSING_MIGRATION,
            risk=RecoveryRisk.HIGH,
            recommendation=RecoveryRecommendation.HALT,
            rationale="Missing migration",
        )

        decision2 = RecoveryDecision(
            difference=SchemaDifference(
                difference_type=DifferenceType.EXTRA_COLUMN,
                target_migration="004",
                table_name="table2",
                column_name="col1",
            ),
            classification=RecoveryClassification.SCHEMA_DRIFT,
            risk=RecoveryRisk.MEDIUM,
            recommendation=RecoveryRecommendation.FORWARD_MIGRATION,
            rationale="Schema drift detected",
        )

        executor = RecoveryExecutor(decision_context)
        results = executor.execute((decision1, decision2))

        assert isinstance(results, tuple)
        assert len(results) == 2
        assert results[0].decision is decision1
        assert results[1].decision is decision2

    def test_execute_preserves_deterministic_ordering(self, decision_context: DecisionContext):
        """Execute should maintain input order in output."""
        decisions = tuple(
            RecoveryDecision(
                difference=SchemaDifference(
                    difference_type=DifferenceType.MISSING_COLUMN,
                    target_migration=f"00{i}",
                    table_name=f"table_{i}",
                    column_name=f"col_{i}",
                ),
                classification=RecoveryClassification.SCHEMA_DRIFT,
                risk=RecoveryRisk.LOW,
                recommendation=RecoveryRecommendation.SAFE_SKIP,
                rationale=f"Reason {i}",
            )
            for i in range(5)
        )

        executor = RecoveryExecutor(decision_context)
        results = executor.execute(decisions)

        assert len(results) == 5
        for i, result in enumerate(results):
            assert result.decision is decisions[i]
            assert result.decision.difference.table_name == f"table_{i}"

    def test_execute_returns_immutable_tuple(
        self,
        decision_context: DecisionContext,
        sample_decision: RecoveryDecision
    ):
        """Execute should return immutable tuple."""
        executor = RecoveryExecutor(decision_context)
        results = executor.execute((sample_decision,))

        assert isinstance(results, tuple)

        with pytest.raises((TypeError, AttributeError)):
            results[0] = None  # type: ignore

    def test_execute_does_not_mutate_input_decisions(
        self,
        decision_context: DecisionContext,
        sample_decision: RecoveryDecision
    ):
        """Execute should not mutate input decisions."""
        original_difference = sample_decision.difference
        original_classification = sample_decision.classification
        original_risk = sample_decision.risk
        original_recommendation = sample_decision.recommendation
        original_rationale = sample_decision.rationale

        executor = RecoveryExecutor(decision_context)
        executor.execute((sample_decision,))

        assert sample_decision.difference is original_difference
        assert sample_decision.classification == original_classification
        assert sample_decision.risk == original_risk
        assert sample_decision.recommendation == original_recommendation
        assert sample_decision.rationale == original_rationale

    def test_execute_does_not_mutate_context(self, decision_context: DecisionContext):
        """Execute should not mutate decision context."""
        original_migrations = decision_context.applied_migration_names
        original_files = decision_context.available_migration_files
        original_checksums = decision_context.migration_checksums

        decision = RecoveryDecision(
            difference=SchemaDifference(
                difference_type=DifferenceType.EXTRA_TABLE,
                target_migration="003",
                table_name="test",
            ),
            classification=RecoveryClassification.REPLAY_CONFLICT,
            risk=RecoveryRisk.LOW,
            recommendation=RecoveryRecommendation.FORCE_RECORD,
            rationale="Test",
        )

        executor = RecoveryExecutor(decision_context)
        executor.execute((decision,))

        assert decision_context.applied_migration_names is original_migrations
        assert decision_context.available_migration_files is original_files
        assert decision_context.migration_checksums is original_checksums

    def test_execute_result_contains_valid_timestamp(
        self,
        decision_context: DecisionContext,
        sample_decision: RecoveryDecision
    ):
        """Execute should generate valid ISO8601 timestamp."""
        executor = RecoveryExecutor(decision_context)
        results = executor.execute((sample_decision,))

        result = results[0]
        assert result.timestamp.endswith("Z")

        datetime.fromisoformat(result.timestamp.replace("Z", "+00:00"))

    def test_execute_rejects_non_tuple_input(self, decision_context: DecisionContext):
        """Execute should reject list instead of tuple."""
        executor = RecoveryExecutor(decision_context)

        with pytest.raises(TypeError, match="decisions must be tuple"):
            executor.execute([])  # type: ignore

    def test_execute_rejects_invalid_decision_types(self, decision_context: DecisionContext):
        """Execute should reject tuple containing non-RecoveryDecision items."""
        executor = RecoveryExecutor(decision_context)

        with pytest.raises(TypeError, match="must be RecoveryDecision instances"):
            executor.execute(("not a decision",))  # type: ignore


class TestExecutionResultContract:
    """Test ExecutionResult type contract for skeleton implementation."""

    def test_execution_result_is_frozen(
        self,
        decision_context: DecisionContext,
        sample_decision: RecoveryDecision
    ):
        """ExecutionResult should be immutable (frozen dataclass)."""
        executor = RecoveryExecutor(decision_context)
        results = executor.execute((sample_decision,))
        result = results[0]

        with pytest.raises((AttributeError, Exception)):
            result.status = ExecutionStatus.SUCCESS  # type: ignore

    def test_skeleton_returns_skipped_status(
        self,
        decision_context: DecisionContext,
        sample_decision: RecoveryDecision
    ):
        """Skeleton implementation should return SKIPPED status."""
        executor = RecoveryExecutor(decision_context)
        results = executor.execute((sample_decision,))

        assert results[0].status == ExecutionStatus.SKIPPED

    def test_skeleton_returns_empty_sql(
        self,
        decision_context: DecisionContext,
        sample_decision: RecoveryDecision
    ):
        """Skeleton implementation should return empty SQL tuple."""
        executor = RecoveryExecutor(decision_context)
        results = executor.execute((sample_decision,))

        assert results[0].executed_sql == ()
        assert isinstance(results[0].executed_sql, tuple)

    def test_skeleton_returns_no_rollback(
        self,
        decision_context: DecisionContext,
        sample_decision: RecoveryDecision
    ):
        """Skeleton implementation should indicate no rollback occurred."""
        executor = RecoveryExecutor(decision_context)
        results = executor.execute((sample_decision,))

        assert results[0].rolled_back is False

    def test_skeleton_returns_no_error(
        self,
        decision_context: DecisionContext,
        sample_decision: RecoveryDecision
    ):
        """Skeleton implementation should return no error message."""
        executor = RecoveryExecutor(decision_context)
        results = executor.execute((sample_decision,))

        assert results[0].error_message is None

    def test_skeleton_returns_zero_duration(
        self,
        decision_context: DecisionContext,
        sample_decision: RecoveryDecision
    ):
        """Skeleton implementation should return zero duration."""
        executor = RecoveryExecutor(decision_context)
        results = executor.execute((sample_decision,))

        assert results[0].duration_ms == 0.0
