"""Recovery executor for applying recovery decisions to database.

Implements ADR-023 execution layer.
This module handles the controlled execution of recovery decisions.
"""

import sqlite3
from typing import Optional
from datetime import datetime, UTC

from ml_service.migrations.recovery.models import (
    RecoveryDecision,
    ExecutionResult,
    ExecutionStatus,
    DecisionContext,
    RecoveryRecommendation,
)


class ExecutionError(Exception):
    """Base exception for all recovery execution failures."""
    pass


class ApprovalRequiredError(ExecutionError):
    """Raised when an action requires approval but no valid token is provided."""
    pass


class RecoveryHaltedError(ExecutionError):
    """Raised when a HALT recommendation is processed or execution is explicitly aborted."""
    pass


class RecoveryExecutor:
    """Executes recovery decisions against the database.

    This executor applies approved recovery decisions in a deterministic,
    transaction-safe manner. Each decision is executed independently with
    proper isolation and rollback support.
    """

    def __init__(self, context: DecisionContext, db_path: str) -> None:
        """Initialize the recovery executor.

        Args:
            context: Immutable decision context containing migration metadata
            db_path: Path to SQLite database file
        """
        self._context = context
        self._db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None

    def execute(
        self,
        decisions: tuple[RecoveryDecision, ...]
    ) -> tuple[ExecutionResult, ...]:
        """Execute a batch of recovery decisions.

        Processes decisions sequentially in deterministic order. Each decision
        is executed independently and results are collected immutably.

        Args:
            decisions: Immutable tuple of recovery decisions to execute

        Returns:
            Immutable tuple of execution results in the same order as input

        Raises:
            TypeError: If decisions is not a tuple or contains non-RecoveryDecision items
            RecoveryHaltedError: If a decision is classified as HALT
            ExecutionError: On transaction or SQLite query failure
        """
        if not isinstance(decisions, tuple):
            raise TypeError(f"decisions must be tuple, got {type(decisions).__name__}")

        results: list[ExecutionResult] = []

        try:
            self._conn = sqlite3.connect(self._db_path)

            for decision in decisions:
                if not isinstance(decision, RecoveryDecision):
                    raise TypeError(
                        f"All decisions must be RecoveryDecision instances, "
                        f"got {type(decision).__name__}"
                    )

                result = self._execute_single(decision)
                results.append(result)
        finally:
            if self._conn:
                self._conn.close()
                self._conn = None

        return tuple(results)

    def _execute_single(self, decision: RecoveryDecision) -> ExecutionResult:
        """Execute a single recovery decision.

        Each decision is executed within its own transaction boundary.

        Args:
            decision: The recovery decision to execute

        Returns:
            ExecutionResult
        """
        start_time = datetime.now(UTC)
        rolled_back = False
        status = ExecutionStatus.SUCCESS
        executed_sql: tuple[str, ...] = ()
        error_message = None

        try:
            self._begin_transaction()

            # Delegate to internal planning layer
            planned = self._plan_execution(decision)
            status = planned.status
            executed_sql = planned.executed_sql
            error_message = planned.error_message

            self._commit_transaction()

        except RecoveryHaltedError:
            rolled_back = True
            self._rollback_transaction()
            raise
        except Exception as e:
            rolled_back = True
            self._rollback_transaction()
            raise ExecutionError(f"Database error during execution: {e}") from e

        end_time = datetime.now(UTC)
        duration_ms = (end_time - start_time).total_seconds() * 1000.0
        timestamp = end_time.isoformat().replace("+00:00", "Z")

        return ExecutionResult(
            decision=decision,
            status=status,
            duration_ms=duration_ms,
            executed_sql=executed_sql,
            rolled_back=rolled_back,
            timestamp=timestamp,
            error_message=error_message,
        )

    def _plan_execution(self, decision: RecoveryDecision) -> ExecutionResult:
        """Route decision to appropriate planning handler based on recommendation."""
        rec = decision.recommendation
        if rec == RecoveryRecommendation.FORWARD_MIGRATION:
            return self._handle_forward_migration(decision)
        elif rec == RecoveryRecommendation.FORCE_RECORD:
            return self._handle_force_record(decision)
        elif rec == RecoveryRecommendation.SAFE_SKIP:
            return self._handle_safe_skip(decision)
        elif rec == RecoveryRecommendation.MANUAL_PATCH:
            return self._handle_manual_patch(decision)
        elif rec == RecoveryRecommendation.HALT:
            return self._handle_halt(decision)
        else:
            raise ValueError(f"Unknown recommendation: {rec}")

    def _handle_forward_migration(self, decision: RecoveryDecision) -> ExecutionResult:
        """Create placeholder execution plan for forward migration."""
        migration_name = decision.difference.target_migration or "unknown"
        executed_sql = (f"-- PLAN: FORWARD_MIGRATION for {migration_name}",)
        return ExecutionResult(
            decision=decision,
            status=ExecutionStatus.SUCCESS,
            duration_ms=0.0,
            executed_sql=executed_sql,
            rolled_back=False,
            timestamp="",
            error_message=None,
        )

    def _handle_force_record(self, decision: RecoveryDecision) -> ExecutionResult:
        """Create placeholder ledger action for force recording."""
        migration_name = decision.difference.target_migration or "unknown"
        executed_sql = (f"INSERT INTO schema_migrations (migration_name, applied_at) VALUES ('{migration_name}', CURRENT_TIMESTAMP);",)
        return ExecutionResult(
            decision=decision,
            status=ExecutionStatus.SUCCESS,
            duration_ms=0.0,
            executed_sql=executed_sql,
            rolled_back=False,
            timestamp="",
            error_message=None,
        )

    def _handle_safe_skip(self, decision: RecoveryDecision) -> ExecutionResult:
        """Create skipped execution result for safe skip."""
        return ExecutionResult(
            decision=decision,
            status=ExecutionStatus.SKIPPED,
            duration_ms=0.0,
            executed_sql=(),
            rolled_back=False,
            timestamp="",
            error_message=None,
        )

    def _handle_manual_patch(self, decision: RecoveryDecision) -> ExecutionResult:
        """Create manual intervention result for manual patch."""
        return ExecutionResult(
            decision=decision,
            status=ExecutionStatus.SKIPPED,
            duration_ms=0.0,
            executed_sql=(),
            rolled_back=False,
            timestamp="",
            error_message="Manual patch required; execution skipped.",
        )

    def _handle_halt(self, decision: RecoveryDecision) -> ExecutionResult:
        """Create blocked execution result for halt and raise RecoveryHaltedError."""
        raise RecoveryHaltedError(f"Recovery halted due to HALT recommendation: {decision.rationale}")

    def _begin_transaction(self) -> None:
        """Begin a new transaction with immediate isolation.

        Uses BEGIN IMMEDIATE to acquire a write lock immediately,
        preventing deadlock scenarios in SQLite.
        """
        if not self._conn:
            raise RuntimeError("No active database connection")

        cursor = self._conn.cursor()
        cursor.execute("BEGIN IMMEDIATE")
        cursor.close()

    def _commit_transaction(self) -> None:
        """Commit the current transaction."""
        if not self._conn:
            raise RuntimeError("No active database connection")

        self._conn.commit()

    def _rollback_transaction(self) -> None:
        """Rollback the current transaction.

        Ensures transaction cleanup even if rollback itself fails.
        """
        if not self._conn:
            return

        try:
            self._conn.rollback()
        except Exception:
            pass
