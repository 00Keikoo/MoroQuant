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
)


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
        For this commit, all decisions return placeholder SKIPPED results.
        Actual migration execution logic will be added in later commits.

        Args:
            decision: The recovery decision to execute

        Returns:
            ExecutionResult with SKIPPED status
        """
        start_time = datetime.now(UTC)
        rolled_back = False

        try:
            self._begin_transaction()

            # Placeholder: actual execution logic will be added in next commit
            # For now, all decisions are skipped but transaction lifecycle is exercised

            self._commit_transaction()

        except Exception as e:
            rolled_back = True
            self._rollback_transaction()

        end_time = datetime.now(UTC)
        duration_ms = (end_time - start_time).total_seconds() * 1000.0
        timestamp = end_time.isoformat().replace("+00:00", "Z")

        return ExecutionResult(
            decision=decision,
            status=ExecutionStatus.SKIPPED,
            duration_ms=duration_ms,
            executed_sql=(),
            rolled_back=rolled_back,
            timestamp=timestamp,
            error_message=None,
        )

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
