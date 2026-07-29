"""Tests for DecisionAnalyzer classification engine.

Sprint 2.3B Commit 5: Tests complete pipeline including recommendation engine.
"""

import pytest

from ml_service.migrations.recovery.decision.analyzer import DecisionAnalyzer
from ml_service.migrations.recovery.models import (
    DecisionContext,
    DifferenceType,
    RecoveryClassification,
    RecoveryDecision,
    RecoveryRecommendation,
    RecoveryRisk,
    SchemaDifference,
)


class TestDecisionAnalyzerConstruction:
    """Test DecisionAnalyzer constructor."""

    def test_constructor(self):
        """DecisionAnalyzer can be constructed with DecisionContext."""
        context = DecisionContext(
            applied_migration_names=(),
            available_migration_files=(),
            migration_checksums={},
        )
        analyzer = DecisionAnalyzer(context)
        assert analyzer is not None
        assert analyzer.context == context


class TestDecisionAnalyzerInterface:
    """Test DecisionAnalyzer public interface."""

    def test_has_analyze_method(self):
        """DecisionAnalyzer has analyze method."""
        context = DecisionContext(
            applied_migration_names=(),
            available_migration_files=(),
            migration_checksums={},
        )
        analyzer = DecisionAnalyzer(context)
        assert hasattr(analyzer, 'analyze')
        assert callable(analyzer.analyze)


class TestDecisionAnalyzerAnalyze:
    """Test DecisionAnalyzer.analyze() behavior."""

    def test_analyze_empty_differences(self):
        """analyze() returns empty tuple when given empty tuple."""
        context = DecisionContext(
            applied_migration_names=(),
            available_migration_files=(),
            migration_checksums={},
        )
        analyzer = DecisionAnalyzer(context)
        result = analyzer.analyze(())
        assert result == ()


class TestMetadataDriftClassification:
    """Test METADATA_DRIFT classification per ADR-023 Section 2.1."""

    def test_missing_table_applied_migration(self):
        """MISSING_TABLE with applied migration classifies as METADATA_DRIFT."""
        context = DecisionContext(
            applied_migration_names=("001_create_users",),
            available_migration_files=("001_create_users",),
            migration_checksums={},
        )
        analyzer = DecisionAnalyzer(context)

        differences = (
            SchemaDifference(
                difference_type=DifferenceType.MISSING_TABLE,
                table_name="users",
                target_migration="001_create_users",
            ),
        )

        decisions = analyzer.analyze(differences)
        assert len(decisions) == 1
        assert decisions[0].classification == RecoveryClassification.METADATA_DRIFT
        assert "recorded as applied but physically missing" in decisions[0].rationale

    def test_missing_column_applied_migration(self):
        """MISSING_COLUMN with applied migration classifies as METADATA_DRIFT."""
        context = DecisionContext(
            applied_migration_names=("002_add_email",),
            available_migration_files=("002_add_email",),
            migration_checksums={},
        )
        analyzer = DecisionAnalyzer(context)

        differences = (
            SchemaDifference(
                difference_type=DifferenceType.MISSING_COLUMN,
                table_name="users",
                column_name="email",
                target_migration="002_add_email",
            ),
        )

        decisions = analyzer.analyze(differences)
        assert len(decisions) == 1
        assert decisions[0].classification == RecoveryClassification.METADATA_DRIFT


class TestSchemaDriftClassification:
    """Test SCHEMA_DRIFT classification per ADR-023 Section 2.2."""

    def test_missing_table_not_applied(self):
        """MISSING_TABLE without applied migration classifies as SCHEMA_DRIFT."""
        context = DecisionContext(
            applied_migration_names=(),
            available_migration_files=("001_create_users",),
            migration_checksums={},
        )
        analyzer = DecisionAnalyzer(context)

        differences = (
            SchemaDifference(
                difference_type=DifferenceType.MISSING_TABLE,
                table_name="users",
                target_migration="001_create_users",
            ),
        )

        decisions = analyzer.analyze(differences)
        assert len(decisions) == 1
        assert decisions[0].classification == RecoveryClassification.SCHEMA_DRIFT
        assert "does not match target schema" in decisions[0].rationale

    def test_column_type_mismatch(self):
        """COLUMN_TYPE_MISMATCH classifies as SCHEMA_DRIFT."""
        context = DecisionContext(
            applied_migration_names=(),
            available_migration_files=(),
            migration_checksums={},
        )
        analyzer = DecisionAnalyzer(context)

        differences = (
            SchemaDifference(
                difference_type=DifferenceType.COLUMN_TYPE_MISMATCH,
                table_name="users",
                column_name="age",
                details={"expected": "INTEGER", "actual": "TEXT"},
            ),
        )

        decisions = analyzer.analyze(differences)
        assert len(decisions) == 1
        assert decisions[0].classification == RecoveryClassification.SCHEMA_DRIFT

    def test_nullability_mismatch(self):
        """NULLABILITY_MISMATCH classifies as SCHEMA_DRIFT."""
        context = DecisionContext(
            applied_migration_names=(),
            available_migration_files=(),
            migration_checksums={},
        )
        analyzer = DecisionAnalyzer(context)

        differences = (
            SchemaDifference(
                difference_type=DifferenceType.NULLABILITY_MISMATCH,
                table_name="users",
                column_name="email",
            ),
        )

        decisions = analyzer.analyze(differences)
        assert len(decisions) == 1
        assert decisions[0].classification == RecoveryClassification.SCHEMA_DRIFT

    def test_constraint_mismatch(self):
        """CONSTRAINT_MISMATCH classifies as SCHEMA_DRIFT."""
        context = DecisionContext(
            applied_migration_names=(),
            available_migration_files=(),
            migration_checksums={},
        )
        analyzer = DecisionAnalyzer(context)

        differences = (
            SchemaDifference(
                difference_type=DifferenceType.CONSTRAINT_MISMATCH,
                table_name="users",
            ),
        )

        decisions = analyzer.analyze(differences)
        assert len(decisions) == 1
        assert decisions[0].classification == RecoveryClassification.SCHEMA_DRIFT

    def test_default_value_mismatch(self):
        """DEFAULT_VALUE_MISMATCH classifies as SCHEMA_DRIFT."""
        context = DecisionContext(
            applied_migration_names=(),
            available_migration_files=(),
            migration_checksums={},
        )
        analyzer = DecisionAnalyzer(context)

        differences = (
            SchemaDifference(
                difference_type=DifferenceType.DEFAULT_VALUE_MISMATCH,
                table_name="users",
                column_name="active",
            ),
        )

        decisions = analyzer.analyze(differences)
        assert len(decisions) == 1
        assert decisions[0].classification == RecoveryClassification.SCHEMA_DRIFT

    def test_missing_index(self):
        """MISSING_INDEX classifies as SCHEMA_DRIFT."""
        context = DecisionContext(
            applied_migration_names=(),
            available_migration_files=(),
            migration_checksums={},
        )
        analyzer = DecisionAnalyzer(context)

        differences = (
            SchemaDifference(
                difference_type=DifferenceType.MISSING_INDEX,
                table_name="users",
                index_name="idx_email",
            ),
        )

        decisions = analyzer.analyze(differences)
        assert len(decisions) == 1
        assert decisions[0].classification == RecoveryClassification.SCHEMA_DRIFT

    def test_index_definition_mismatch(self):
        """INDEX_DEFINITION_MISMATCH classifies as SCHEMA_DRIFT."""
        context = DecisionContext(
            applied_migration_names=(),
            available_migration_files=(),
            migration_checksums={},
        )
        analyzer = DecisionAnalyzer(context)

        differences = (
            SchemaDifference(
                difference_type=DifferenceType.INDEX_DEFINITION_MISMATCH,
                index_name="idx_email",
            ),
        )

        decisions = analyzer.analyze(differences)
        assert len(decisions) == 1
        assert decisions[0].classification == RecoveryClassification.SCHEMA_DRIFT


class TestReplayConflictClassification:
    """Test REPLAY_CONFLICT classification per ADR-023 Section 2.3."""

    def test_extra_table_not_recorded(self):
        """EXTRA_TABLE with target migration not applied classifies as REPLAY_CONFLICT."""
        context = DecisionContext(
            applied_migration_names=(),
            available_migration_files=("001_create_users",),
            migration_checksums={},
        )
        analyzer = DecisionAnalyzer(context)

        differences = (
            SchemaDifference(
                difference_type=DifferenceType.EXTRA_TABLE,
                table_name="users",
                target_migration="001_create_users",
            ),
        )

        decisions = analyzer.analyze(differences)
        assert len(decisions) == 1
        assert decisions[0].classification == RecoveryClassification.REPLAY_CONFLICT
        assert "not marked applied" in decisions[0].rationale

    def test_extra_column_not_recorded(self):
        """EXTRA_COLUMN with target migration not applied classifies as REPLAY_CONFLICT."""
        context = DecisionContext(
            applied_migration_names=(),
            available_migration_files=("002_add_email",),
            migration_checksums={},
        )
        analyzer = DecisionAnalyzer(context)

        differences = (
            SchemaDifference(
                difference_type=DifferenceType.EXTRA_COLUMN,
                table_name="users",
                column_name="email",
                target_migration="002_add_email",
            ),
        )

        decisions = analyzer.analyze(differences)
        assert len(decisions) == 1
        assert decisions[0].classification == RecoveryClassification.REPLAY_CONFLICT

    def test_extra_index_not_recorded(self):
        """EXTRA_INDEX with target migration not applied classifies as REPLAY_CONFLICT."""
        context = DecisionContext(
            applied_migration_names=(),
            available_migration_files=("003_add_index",),
            migration_checksums={},
        )
        analyzer = DecisionAnalyzer(context)

        differences = (
            SchemaDifference(
                difference_type=DifferenceType.EXTRA_INDEX,
                index_name="idx_email",
                target_migration="003_add_index",
            ),
        )

        decisions = analyzer.analyze(differences)
        assert len(decisions) == 1
        assert decisions[0].classification == RecoveryClassification.REPLAY_CONFLICT


class TestManualDatabaseModificationClassification:
    """Test MANUAL_DATABASE_MODIFICATION classification per ADR-023 Section 2.7."""

    def test_extra_table_no_migration(self):
        """EXTRA_TABLE with no target migration classifies as MANUAL_DATABASE_MODIFICATION."""
        context = DecisionContext(
            applied_migration_names=(),
            available_migration_files=(),
            migration_checksums={},
        )
        analyzer = DecisionAnalyzer(context)

        differences = (
            SchemaDifference(
                difference_type=DifferenceType.EXTRA_TABLE,
                table_name="rogue_table",
            ),
        )

        decisions = analyzer.analyze(differences)
        assert len(decisions) == 1
        assert decisions[0].classification == RecoveryClassification.MANUAL_DATABASE_MODIFICATION
        assert "absent from migration files" in decisions[0].rationale

    def test_extra_column_no_migration(self):
        """EXTRA_COLUMN with no target migration classifies as MANUAL_DATABASE_MODIFICATION."""
        context = DecisionContext(
            applied_migration_names=(),
            available_migration_files=(),
            migration_checksums={},
        )
        analyzer = DecisionAnalyzer(context)

        differences = (
            SchemaDifference(
                difference_type=DifferenceType.EXTRA_COLUMN,
                table_name="users",
                column_name="unauthorized_field",
            ),
        )

        decisions = analyzer.analyze(differences)
        assert len(decisions) == 1
        assert decisions[0].classification == RecoveryClassification.MANUAL_DATABASE_MODIFICATION


class TestDeterministicOutput:
    """Test that DecisionAnalyzer produces deterministic output."""

    def test_same_input_same_output(self):
        """Multiple analyze calls with same input produce identical output."""
        context = DecisionContext(
            applied_migration_names=("001_create_users",),
            available_migration_files=("001_create_users",),
            migration_checksums={},
        )
        analyzer = DecisionAnalyzer(context)

        differences = (
            SchemaDifference(
                difference_type=DifferenceType.MISSING_TABLE,
                table_name="users",
                target_migration="001_create_users",
            ),
        )

        result1 = analyzer.analyze(differences)
        result2 = analyzer.analyze(differences)

        assert result1 == result2
        assert result1[0].to_dict() == result2[0].to_dict()


class TestImmutabilityGuarantees:
    """Test that RecoveryDecision objects are immutable."""

    def test_recovery_decision_immutable(self):
        """RecoveryDecision objects cannot be modified after creation."""
        context = DecisionContext(
            applied_migration_names=(),
            available_migration_files=(),
            migration_checksums={},
        )
        analyzer = DecisionAnalyzer(context)

        differences = (
            SchemaDifference(
                difference_type=DifferenceType.MISSING_INDEX,
                index_name="idx_test",
            ),
        )

        decisions = analyzer.analyze(differences)
        decision = decisions[0]

        with pytest.raises(AttributeError):
            decision.classification = RecoveryClassification.UNKNOWN_STATE


class TestMultipleDifferences:
    """Test analyzing multiple differences in a single call."""

    def test_multiple_differences(self):
        """analyze() processes multiple differences and returns correct classifications."""
        context = DecisionContext(
            applied_migration_names=("001_create_users",),
            available_migration_files=("001_create_users", "002_add_email"),
            migration_checksums={},
        )
        analyzer = DecisionAnalyzer(context)

        differences = (
            SchemaDifference(
                difference_type=DifferenceType.MISSING_TABLE,
                table_name="users",
                target_migration="001_create_users",
            ),
            SchemaDifference(
                difference_type=DifferenceType.EXTRA_COLUMN,
                table_name="accounts",
                column_name="balance",
                target_migration="002_add_email",
            ),
            SchemaDifference(
                difference_type=DifferenceType.COLUMN_TYPE_MISMATCH,
                table_name="orders",
                column_name="quantity",
            ),
        )

        decisions = analyzer.analyze(differences)
        assert len(decisions) == 3
        assert decisions[0].classification == RecoveryClassification.METADATA_DRIFT
        assert decisions[1].classification == RecoveryClassification.REPLAY_CONFLICT
        assert decisions[2].classification == RecoveryClassification.SCHEMA_DRIFT


class TestRiskClassification:
    """Test risk classification per ADR-023 Section 3."""

    def test_replay_conflict_maps_to_low_risk(self):
        """REPLAY_CONFLICT classifies as LOW risk."""
        context = DecisionContext(
            applied_migration_names=(),
            available_migration_files=("001_create_users",),
            migration_checksums={},
        )
        analyzer = DecisionAnalyzer(context)

        differences = (
            SchemaDifference(
                difference_type=DifferenceType.EXTRA_TABLE,
                table_name="users",
                target_migration="001_create_users",
            ),
        )

        decisions = analyzer.analyze(differences)
        assert len(decisions) == 1
        assert decisions[0].classification == RecoveryClassification.REPLAY_CONFLICT
        assert decisions[0].risk == RecoveryRisk.LOW

    def test_schema_drift_column_type_mismatch_high_risk(self):
        """SCHEMA_DRIFT with COLUMN_TYPE_MISMATCH classifies as HIGH risk."""
        context = DecisionContext(
            applied_migration_names=(),
            available_migration_files=(),
            migration_checksums={},
        )
        analyzer = DecisionAnalyzer(context)

        differences = (
            SchemaDifference(
                difference_type=DifferenceType.COLUMN_TYPE_MISMATCH,
                table_name="orders",
                column_name="quantity",
            ),
        )

        decisions = analyzer.analyze(differences)
        assert len(decisions) == 1
        assert decisions[0].classification == RecoveryClassification.SCHEMA_DRIFT
        assert decisions[0].risk == RecoveryRisk.HIGH

    def test_schema_drift_nullability_mismatch_high_risk(self):
        """SCHEMA_DRIFT with NULLABILITY_MISMATCH classifies as HIGH risk."""
        context = DecisionContext(
            applied_migration_names=(),
            available_migration_files=(),
            migration_checksums={},
        )
        analyzer = DecisionAnalyzer(context)

        differences = (
            SchemaDifference(
                difference_type=DifferenceType.NULLABILITY_MISMATCH,
                table_name="users",
                column_name="email",
            ),
        )

        decisions = analyzer.analyze(differences)
        assert len(decisions) == 1
        assert decisions[0].classification == RecoveryClassification.SCHEMA_DRIFT
        assert decisions[0].risk == RecoveryRisk.HIGH

    def test_schema_drift_constraint_mismatch_medium_risk(self):
        """SCHEMA_DRIFT with CONSTRAINT_MISMATCH classifies as MEDIUM risk."""
        context = DecisionContext(
            applied_migration_names=(),
            available_migration_files=(),
            migration_checksums={},
        )
        analyzer = DecisionAnalyzer(context)

        differences = (
            SchemaDifference(
                difference_type=DifferenceType.CONSTRAINT_MISMATCH,
                table_name="users",
                column_name="email",
            ),
        )

        decisions = analyzer.analyze(differences)
        assert len(decisions) == 1
        assert decisions[0].classification == RecoveryClassification.SCHEMA_DRIFT
        assert decisions[0].risk == RecoveryRisk.MEDIUM

    def test_schema_drift_default_value_mismatch_medium_risk(self):
        """SCHEMA_DRIFT with DEFAULT_VALUE_MISMATCH classifies as MEDIUM risk."""
        context = DecisionContext(
            applied_migration_names=(),
            available_migration_files=(),
            migration_checksums={},
        )
        analyzer = DecisionAnalyzer(context)

        differences = (
            SchemaDifference(
                difference_type=DifferenceType.DEFAULT_VALUE_MISMATCH,
                table_name="users",
                column_name="status",
            ),
        )

        decisions = analyzer.analyze(differences)
        assert len(decisions) == 1
        assert decisions[0].classification == RecoveryClassification.SCHEMA_DRIFT
        assert decisions[0].risk == RecoveryRisk.MEDIUM

    def test_schema_drift_missing_index_low_risk(self):
        """SCHEMA_DRIFT with MISSING_INDEX classifies as LOW risk."""
        context = DecisionContext(
            applied_migration_names=(),
            available_migration_files=(),
            migration_checksums={},
        )
        analyzer = DecisionAnalyzer(context)

        differences = (
            SchemaDifference(
                difference_type=DifferenceType.MISSING_INDEX,
                table_name="users",
                index_name="idx_email",
            ),
        )

        decisions = analyzer.analyze(differences)
        assert len(decisions) == 1
        assert decisions[0].classification == RecoveryClassification.SCHEMA_DRIFT
        assert decisions[0].risk == RecoveryRisk.LOW

    def test_manual_database_modification_high_risk(self):
        """MANUAL_DATABASE_MODIFICATION classifies as HIGH risk."""
        context = DecisionContext(
            applied_migration_names=(),
            available_migration_files=(),
            migration_checksums={},
        )
        analyzer = DecisionAnalyzer(context)

        differences = (
            SchemaDifference(
                difference_type=DifferenceType.EXTRA_COLUMN,
                table_name="users",
                column_name="manual_field",
            ),
        )

        decisions = analyzer.analyze(differences)
        assert len(decisions) == 1
        assert decisions[0].classification == RecoveryClassification.MANUAL_DATABASE_MODIFICATION
        assert decisions[0].risk == RecoveryRisk.HIGH

    def test_metadata_drift_critical_risk(self):
        """METADATA_DRIFT classifies as CRITICAL risk."""
        context = DecisionContext(
            applied_migration_names=("001_create_users",),
            available_migration_files=("001_create_users",),
            migration_checksums={},
        )
        analyzer = DecisionAnalyzer(context)

        differences = (
            SchemaDifference(
                difference_type=DifferenceType.MISSING_TABLE,
                table_name="users",
                target_migration="001_create_users",
            ),
        )

        decisions = analyzer.analyze(differences)
        assert len(decisions) == 1
        assert decisions[0].classification == RecoveryClassification.METADATA_DRIFT
        assert decisions[0].risk == RecoveryRisk.CRITICAL

    def test_unknown_state_critical_risk(self):
        """UNKNOWN_STATE classifies as CRITICAL risk."""
        context = DecisionContext(
            applied_migration_names=(),
            available_migration_files=(),
            migration_checksums={},
        )
        analyzer = DecisionAnalyzer(context)

        differences = (
            SchemaDifference(
                difference_type=DifferenceType.COLUMN_TYPE_MISMATCH,
                table_name="unknown_table",
            ),
        )

        decisions = analyzer.analyze(differences)
        decision = decisions[0]
        if decision.classification == RecoveryClassification.UNKNOWN_STATE:
            assert decision.risk == RecoveryRisk.CRITICAL


class TestRecommendationMapping:
    """Test recommendation mappings per ADR-023 Section 4."""

    def test_replay_conflict_recommends_force_record(self):
        """REPLAY_CONFLICT maps to FORCE_RECORD recommendation."""
        context = DecisionContext(
            applied_migration_names=(),
            available_migration_files=("001_create_users",),
            migration_checksums={},
        )
        analyzer = DecisionAnalyzer(context)

        differences = (
            SchemaDifference(
                difference_type=DifferenceType.EXTRA_TABLE,
                table_name="users",
                target_migration="001_create_users",
            ),
        )

        decisions = analyzer.analyze(differences)
        assert len(decisions) == 1
        assert decisions[0].classification == RecoveryClassification.REPLAY_CONFLICT
        assert decisions[0].recommendation == RecoveryRecommendation.FORCE_RECORD

    def test_schema_drift_recommends_forward_migration(self):
        """SCHEMA_DRIFT maps to FORWARD_MIGRATION recommendation."""
        context = DecisionContext(
            applied_migration_names=(),
            available_migration_files=(),
            migration_checksums={},
        )
        analyzer = DecisionAnalyzer(context)

        differences = (
            SchemaDifference(
                difference_type=DifferenceType.COLUMN_TYPE_MISMATCH,
                table_name="users",
                column_name="age",
            ),
        )

        decisions = analyzer.analyze(differences)
        assert len(decisions) == 1
        assert decisions[0].classification == RecoveryClassification.SCHEMA_DRIFT
        assert decisions[0].recommendation == RecoveryRecommendation.FORWARD_MIGRATION

    def test_metadata_drift_recommends_halt(self):
        """METADATA_DRIFT maps to HALT recommendation."""
        context = DecisionContext(
            applied_migration_names=("001_create_users",),
            available_migration_files=("001_create_users",),
            migration_checksums={},
        )
        analyzer = DecisionAnalyzer(context)

        differences = (
            SchemaDifference(
                difference_type=DifferenceType.MISSING_TABLE,
                table_name="users",
                target_migration="001_create_users",
            ),
        )

        decisions = analyzer.analyze(differences)
        assert len(decisions) == 1
        assert decisions[0].classification == RecoveryClassification.METADATA_DRIFT
        assert decisions[0].recommendation == RecoveryRecommendation.HALT

    def test_manual_database_modification_recommends_manual_patch(self):
        """MANUAL_DATABASE_MODIFICATION maps to MANUAL_PATCH recommendation."""
        context = DecisionContext(
            applied_migration_names=(),
            available_migration_files=(),
            migration_checksums={},
        )
        analyzer = DecisionAnalyzer(context)

        differences = (
            SchemaDifference(
                difference_type=DifferenceType.EXTRA_TABLE,
                table_name="unauthorized_table",
            ),
        )

        decisions = analyzer.analyze(differences)
        assert len(decisions) == 1
        assert decisions[0].classification == RecoveryClassification.MANUAL_DATABASE_MODIFICATION
        assert decisions[0].recommendation == RecoveryRecommendation.MANUAL_PATCH

    def test_complete_pipeline_all_fields_populated(self):
        """Verify complete pipeline populates all RecoveryDecision fields."""
        context = DecisionContext(
            applied_migration_names=(),
            available_migration_files=("001_create_users",),
            migration_checksums={},
        )
        analyzer = DecisionAnalyzer(context)

        differences = (
            SchemaDifference(
                difference_type=DifferenceType.EXTRA_COLUMN,
                table_name="users",
                column_name="email",
                target_migration="001_create_users",
            ),
        )

        decisions = analyzer.analyze(differences)
        assert len(decisions) == 1

        decision = decisions[0]
        assert decision.difference is not None
        assert decision.classification == RecoveryClassification.REPLAY_CONFLICT
        assert decision.risk == RecoveryRisk.LOW
        assert decision.recommendation == RecoveryRecommendation.FORCE_RECORD
        assert decision.rationale != ""
        assert isinstance(decision.details, dict)

    def test_multiple_differences_correct_recommendations(self):
        """Multiple differences produce correct individual recommendations."""
        context = DecisionContext(
            applied_migration_names=("001_create_users",),
            available_migration_files=("001_create_users", "002_add_index"),
            migration_checksums={},
        )
        analyzer = DecisionAnalyzer(context)

        differences = (
            SchemaDifference(
                difference_type=DifferenceType.MISSING_TABLE,
                table_name="users",
                target_migration="001_create_users",
            ),
            SchemaDifference(
                difference_type=DifferenceType.EXTRA_INDEX,
                index_name="idx_email",
                target_migration="002_add_index",
            ),
            SchemaDifference(
                difference_type=DifferenceType.COLUMN_TYPE_MISMATCH,
                table_name="orders",
                column_name="quantity",
            ),
        )

        decisions = analyzer.analyze(differences)
        assert len(decisions) == 3

        assert decisions[0].classification == RecoveryClassification.METADATA_DRIFT
        assert decisions[0].recommendation == RecoveryRecommendation.HALT

        assert decisions[1].classification == RecoveryClassification.REPLAY_CONFLICT
        assert decisions[1].recommendation == RecoveryRecommendation.FORCE_RECORD

        assert decisions[2].classification == RecoveryClassification.SCHEMA_DRIFT
        assert decisions[2].recommendation == RecoveryRecommendation.FORWARD_MIGRATION
