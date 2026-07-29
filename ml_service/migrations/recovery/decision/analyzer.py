"""Decision analyzer for database recovery framework.

Sprint 2.3B: Implements classification logic that maps SchemaDifference
to RecoveryDecision according to ADR-023.

This is a pure logic object with no I/O dependencies.
"""

from typing import Tuple

from ml_service.migrations.recovery.models import (
    DecisionContext,
    RecoveryDecision,
    SchemaDifference,
)


class DecisionAnalyzer:
    """Analyzes schema differences and produces recovery decisions.

    Sprint 2.3B Commit 2: Skeleton only - classification rules not yet implemented.
    """

    def __init__(self, context: DecisionContext) -> None:
        """Initialize the DecisionAnalyzer.

        Args:
            context: Immutable context containing metadata ledger and migration file information.
        """
        self._context = context

    @property
    def context(self) -> DecisionContext:
        """Get the decision context."""
        return self._context

    def analyze(
        self,
        differences: Tuple[SchemaDifference, ...],
    ) -> Tuple[RecoveryDecision, ...]:
        """Analyze schema differences and produce recovery decisions.

        Args:
            differences: Tuple of detected schema differences

        Returns:
            Tuple of recovery decisions, one per difference

        Raises:
            NotImplementedError: Classification rules not yet implemented
        """
        if not differences:
            return ()

        raise NotImplementedError(
            "Decision classification is not implemented yet."
        )
