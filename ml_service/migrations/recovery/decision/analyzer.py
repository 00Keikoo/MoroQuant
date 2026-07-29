"""Decision analyzer for database recovery framework.

Sprint 2.3B: Implements classification logic that maps SchemaDifference
to RecoveryDecision according to ADR-023.

This is a pure logic object with no I/O dependencies.
"""

from typing import Tuple

from ml_service.migrations.recovery.models import (
    DecisionContext,
    DifferenceType,
    RecoveryClassification,
    RecoveryDecision,
    RecoveryRecommendation,
    RecoveryRisk,
    SchemaDifference,
)


class DecisionAnalyzer:
    """Analyzes schema differences and produces recovery decisions.

    Sprint 2.3B Commit 3: Implements classification engine.
    Maps DifferenceType to RecoveryClassification per ADR-023.
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

        Sprint 2.3B Commit 4: Implements risk classification engine.
        Recommendation remains placeholder for future commits.

        Args:
            differences: Tuple of detected schema differences

        Returns:
            Tuple of recovery decisions, one per difference
        """
        if not differences:
            return ()

        decisions = []
        for diff in differences:
            classification = self._classify_difference(diff)
            risk = self._classify_risk(diff, classification)
            rationale = self._generate_rationale(diff, classification)

            decision = RecoveryDecision(
                difference=diff,
                classification=classification,
                risk=risk,
                recommendation=RecoveryRecommendation.HALT,
                rationale=rationale,
                details={},
            )
            decisions.append(decision)

        return tuple(decisions)

    def _classify_difference(self, diff: SchemaDifference) -> RecoveryClassification:
        """Classify a schema difference according to ADR-023 rules.

        ADR-023 Section 2: Recovery Classification Layer
        """
        diff_type = diff.difference_type
        target_migration = diff.target_migration

        if diff_type in (DifferenceType.MISSING_TABLE, DifferenceType.MISSING_COLUMN):
            if target_migration and target_migration in self._context.applied_migration_names:
                return RecoveryClassification.METADATA_DRIFT
            else:
                return RecoveryClassification.SCHEMA_DRIFT

        if diff_type in (DifferenceType.EXTRA_TABLE, DifferenceType.EXTRA_COLUMN, DifferenceType.EXTRA_INDEX):
            if self._is_replay_conflict(diff):
                return RecoveryClassification.REPLAY_CONFLICT
            else:
                return RecoveryClassification.MANUAL_DATABASE_MODIFICATION

        if diff_type in (DifferenceType.COLUMN_TYPE_MISMATCH, DifferenceType.NULLABILITY_MISMATCH):
            return RecoveryClassification.SCHEMA_DRIFT

        if diff_type in (DifferenceType.CONSTRAINT_MISMATCH, DifferenceType.DEFAULT_VALUE_MISMATCH):
            return RecoveryClassification.SCHEMA_DRIFT

        if diff_type == DifferenceType.MISSING_INDEX:
            return RecoveryClassification.SCHEMA_DRIFT

        if diff_type == DifferenceType.INDEX_DEFINITION_MISMATCH:
            return RecoveryClassification.SCHEMA_DRIFT

        return RecoveryClassification.UNKNOWN_STATE

    def _is_replay_conflict(self, diff: SchemaDifference) -> bool:
        """Determine if an EXTRA element is a replay conflict.

        ADR-023 Section 2.3: Replay Conflict
        Element exists but migration is not recorded in ledger.
        """
        target_migration = diff.target_migration

        if not target_migration:
            return False

        return target_migration not in self._context.applied_migration_names

    def _classify_risk(
        self,
        diff: SchemaDifference,
        classification: RecoveryClassification,
    ) -> RecoveryRisk:
        """Classify risk level according to ADR-023 Section 3.

        Risk levels:
        - LOW: Safe operations, no data impact
        - MEDIUM: Modifies non-critical structures
        - HIGH: Structural changes on transactional data
        - CRITICAL: Data loss risk or corrupted state
        """
        if classification == RecoveryClassification.REPLAY_CONFLICT:
            return RecoveryRisk.LOW

        if classification == RecoveryClassification.SCHEMA_DRIFT:
            diff_type = diff.difference_type
            if diff_type in (DifferenceType.COLUMN_TYPE_MISMATCH, DifferenceType.NULLABILITY_MISMATCH):
                return RecoveryRisk.HIGH
            if diff_type in (DifferenceType.CONSTRAINT_MISMATCH, DifferenceType.DEFAULT_VALUE_MISMATCH):
                return RecoveryRisk.MEDIUM
            if diff_type == DifferenceType.MISSING_INDEX:
                return RecoveryRisk.LOW
            return RecoveryRisk.MEDIUM

        if classification == RecoveryClassification.MANUAL_DATABASE_MODIFICATION:
            return RecoveryRisk.HIGH

        if classification in (
            RecoveryClassification.METADATA_DRIFT,
            RecoveryClassification.MISSING_MIGRATION,
            RecoveryClassification.DESTRUCTIVE_MIGRATION,
            RecoveryClassification.UNKNOWN_STATE,
        ):
            return RecoveryRisk.CRITICAL

        if classification == RecoveryClassification.SUPERSEDED_MIGRATION:
            return RecoveryRisk.LOW

        return RecoveryRisk.CRITICAL

    def _generate_rationale(
        self,
        diff: SchemaDifference,
        classification: RecoveryClassification,
    ) -> str:
        """Generate rationale text matching ADR-023 classifications."""
        element_desc = self._describe_element(diff)

        if classification == RecoveryClassification.METADATA_DRIFT:
            return f"{element_desc} is recorded as applied but physically missing. Implies data corruption or unauthorized deletion."

        if classification == RecoveryClassification.SCHEMA_DRIFT:
            return f"{element_desc} does not match target schema. Normalization requires forward migration."

        if classification == RecoveryClassification.REPLAY_CONFLICT:
            return f"{element_desc} exists but migration {diff.target_migration} not marked applied. Migration was run but not recorded."

        if classification == RecoveryClassification.MANUAL_DATABASE_MODIFICATION:
            return f"{element_desc} exists physically but is absent from migration files. Requires DBA manual reconciliation."

        if classification == RecoveryClassification.UNKNOWN_STATE:
            return f"Schema mismatch for {element_desc} cannot be classified. State is unknown."

        return f"Unhandled classification {classification} for {element_desc}."

    def _describe_element(self, diff: SchemaDifference) -> str:
        """Generate human-readable description of the schema element."""
        if diff.table_name and diff.column_name:
            return f"Column {diff.table_name}.{diff.column_name}"
        if diff.table_name:
            return f"Table {diff.table_name}"
        if diff.index_name:
            return f"Index {diff.index_name}"
        return "Schema element"
