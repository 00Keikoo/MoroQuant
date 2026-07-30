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

    def __init__(self, context: DecisionContext, runner: any) -> None:
        """Initialize the recovery executor.

        Args:
            context: Immutable decision context containing migration metadata
            runner: MigrationRunner instance or path to SQLite database file
        """
        self._context = context
        from ml_service.migrations.recovery.migration_runner import MigrationRunner
        if isinstance(runner, MigrationRunner):
            self._runner = runner
            self._db_path = runner._db_path
        else:
            self._runner = MigrationRunner(runner)
            self._db_path = runner
        self._conn = None

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

        for decision in decisions:
            if not isinstance(decision, RecoveryDecision):
                raise TypeError(
                    f"All decisions must be RecoveryDecision instances, "
                    f"got {type(decision).__name__}"
                )

            # Delegate execution to the migration runner
            result = self._runner.execute_action(decision)
            results.append(result)

        return tuple(results)

