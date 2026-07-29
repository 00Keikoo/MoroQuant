"""Recovery executor for applying recovery decisions to database.

Implements ADR-023 execution layer.
This module handles the controlled execution of recovery decisions.
"""

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

    def __init__(self, context: DecisionContext) -> None:
        """Initialize the recovery executor.

        Args:
            context: Immutable decision context containing migration metadata
        """
        self._context = context

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

        for decision in decisions:
            if not isinstance(decision, RecoveryDecision):
                raise TypeError(
                    f"All decisions must be RecoveryDecision instances, "
                    f"got {type(decision).__name__}"
                )

            result = self._execute_single(decision)
            results.append(result)

        return tuple(results)

    def _execute_single(self, decision: RecoveryDecision) -> ExecutionResult:
        """Execute a single recovery decision.

        For this skeleton implementation, all decisions return placeholder
        SKIPPED results. Actual execution logic will be added in later commits.

        Args:
            decision: The recovery decision to execute

        Returns:
            ExecutionResult with SKIPPED status
        """
        timestamp = datetime.now(UTC).isoformat().replace("+00:00", "Z")

        return ExecutionResult(
            decision=decision,
            status=ExecutionStatus.SKIPPED,
            duration_ms=0.0,
            executed_sql=(),
            rolled_back=False,
            timestamp=timestamp,
            error_message=None,
        )
