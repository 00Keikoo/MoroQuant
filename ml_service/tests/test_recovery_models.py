"""Unit tests for database recovery framework models (Sprint 2.3A Phase 1).

Tests immutability, serialization, and basic model construction per ADR-023 v1.1.
"""

import pytest
from dataclasses import FrozenInstanceError

from ml_service.migrations.recovery.models import (
    ColumnSchema,
    IndexSchema,
    TableSchema,
    CheckConstraint,
    ForeignKey,
    SchemaDifference,
    DifferenceType,
    RecoveryClassification,
    RecoveryRisk,
    RecoveryRecommendation,
    DecisionContext,
    RecoveryDecision,
)
from ml_service.migrations.recovery.snapshot import SchemaSnapshot


class TestImmutability:
    """Verify all models are immutable post-initialization."""

    def test_column_schema_immutable(self):
        col = ColumnSchema(name="id", data_type="INTEGER", nullable=False)
        with pytest.raises(FrozenInstanceError):
            col.name = "new_name"

    def test_index_schema_immutable(self):
        idx = IndexSchema(
            name="idx_test",
            table_name="test_table",
            columns=("id",),
            unique=True,
        )
        with pytest.raises(FrozenInstanceError):
            idx.unique = False

    def test_table_schema_immutable(self):
        col = ColumnSchema(name="id", data_type="INTEGER", nullable=False)
        table = TableSchema(name="test_table", columns=(col,))
        with pytest.raises(FrozenInstanceError):
            table.name = "new_table"

    def test_check_constraint_immutable(self):
        check = CheckConstraint(name="check_positive", expression="value > 0")
        with pytest.raises(FrozenInstanceError):
            check.expression = "value >= 0"

    def test_foreign_key_immutable(self):
        fk = ForeignKey(
            column="user_id",
            referenced_table="users",
            referenced_column="id",
        )
        with pytest.raises(FrozenInstanceError):
            fk.column = "new_column"

    def test_schema_difference_immutable(self):
        diff = SchemaDifference(
            difference_type=DifferenceType.MISSING_COLUMN,
            table_name="test_table",
            column_name="test_column",
        )
        with pytest.raises(FrozenInstanceError):
            diff.difference_type = DifferenceType.EXTRA_COLUMN

    def test_schema_snapshot_immutable(self):
        snapshot = SchemaSnapshot(
            database_path="/tmp/test.db",
            timestamp=1234567890,
        )
        with pytest.raises(FrozenInstanceError):
            snapshot.timestamp = 9999999999

    def test_decision_context_immutable(self):
        context = DecisionContext(
            applied_migration_names=("001_initial", "002_add_users"),
            available_migration_files=("001_initial.sql", "002_add_users.sql"),
            migration_checksums={"001_initial": "abc123", "002_add_users": "def456"},
        )
        with pytest.raises(FrozenInstanceError):
            context.applied_migration_names = ("003_new",)

    def test_recovery_decision_immutable(self):
        diff = SchemaDifference(
            difference_type=DifferenceType.MISSING_COLUMN,
            table_name="users",
            column_name="email",
        )
        decision = RecoveryDecision(
            difference=diff,
            classification=RecoveryClassification.SCHEMA_DRIFT,
            risk=RecoveryRisk.HIGH,
            recommendation=RecoveryRecommendation.FORWARD_MIGRATION,
            rationale="Column missing from physical schema",
        )
        with pytest.raises(FrozenInstanceError):
            decision.risk = RecoveryRisk.LOW


class TestSerialization:
    """Verify deterministic JSON serialization."""

    def test_column_schema_to_dict(self):
        col = ColumnSchema(
            name="id",
            data_type="INTEGER",
            nullable=False,
            default_value="1",
            is_primary_key=True,
        )
        result = col.to_dict()
        assert result == {
            "name": "id",
            "data_type": "INTEGER",
            "nullable": False,
            "default_value": "1",
            "is_primary_key": True,
        }

    def test_index_schema_to_dict(self):
        idx = IndexSchema(
            name="idx_user_email",
            table_name="users",
            columns=("email",),
            unique=True,
            partial=True,
            where_clause="deleted_at IS NULL",
        )
        result = idx.to_dict()
        assert result == {
            "name": "idx_user_email",
            "table_name": "users",
            "columns": ["email"],
            "unique": True,
            "partial": True,
            "where_clause": "deleted_at IS NULL",
        }

    def test_table_schema_to_dict(self):
        col1 = ColumnSchema(name="id", data_type="INTEGER", nullable=False, is_primary_key=True)
        col2 = ColumnSchema(name="name", data_type="TEXT", nullable=True)
        check = CheckConstraint(name="check_positive", expression="id > 0")
        fk = ForeignKey(column="user_id", referenced_table="users", referenced_column="id")

        table = TableSchema(
            name="test_table",
            columns=(col1, col2),
            primary_key=("id",),
            check_constraints=(check,),
            foreign_keys=(fk,),
            indexes=("idx_name",),
        )
        result = table.to_dict()

        assert result["name"] == "test_table"
        assert len(result["columns"]) == 2
        assert result["primary_key"] == ["id"]
        assert len(result["check_constraints"]) == 1
        assert result["check_constraints"][0]["name"] == "check_positive"
        assert len(result["foreign_keys"]) == 1
        assert result["foreign_keys"][0]["column"] == "user_id"
        assert result["indexes"] == ["idx_name"]

    def test_schema_difference_to_dict(self):
        diff = SchemaDifference(
            difference_type=DifferenceType.MISSING_COLUMN,
            target_migration="029",
            table_name="execution_decisions",
            column_name="strategy_id",
            details={"expected_type": "TEXT", "reason": "column_missing"},
        )
        result = diff.to_dict()

        assert result["difference_type"] == "MISSING_COLUMN"
        assert result["target_migration"] == "029"
        assert result["table_name"] == "execution_decisions"
        assert result["column_name"] == "strategy_id"
        assert result["details"]["expected_type"] == "TEXT"

    def test_schema_snapshot_to_dict_sorted_keys(self):
        col1 = ColumnSchema(name="id", data_type="INTEGER", nullable=False)
        col2 = ColumnSchema(name="name", data_type="TEXT", nullable=True)
        table_a = TableSchema(name="table_a", columns=(col1,))
        table_b = TableSchema(name="table_b", columns=(col2,))
        idx_a = IndexSchema(name="idx_a", table_name="table_a", columns=("id",), unique=True)
        idx_b = IndexSchema(name="idx_b", table_name="table_b", columns=("name",), unique=False)

        snapshot = SchemaSnapshot(
            database_path="/tmp/test.db",
            timestamp=1234567890,
            tables={"table_b": table_b, "table_a": table_a},
            indexes={"idx_b": idx_b, "idx_a": idx_a},
        )
        result = snapshot.to_dict()

        assert result["database_path"] == "/tmp/test.db"
        assert result["timestamp"] == 1234567890
        table_names = list(result["tables"].keys())
        assert table_names == ["table_a", "table_b"]
        index_names = list(result["indexes"].keys())
        assert index_names == ["idx_a", "idx_b"]


class TestModelConstruction:
    """Verify models can be constructed with valid inputs."""

    def test_column_schema_minimal(self):
        col = ColumnSchema(name="id", data_type="INTEGER", nullable=False)
        assert col.name == "id"
        assert col.data_type == "INTEGER"
        assert col.nullable is False
        assert col.default_value is None
        assert col.is_primary_key is False

    def test_column_schema_full(self):
        col = ColumnSchema(
            name="created_at",
            data_type="TIMESTAMP",
            nullable=False,
            default_value="CURRENT_TIMESTAMP",
            is_primary_key=False,
        )
        assert col.default_value == "CURRENT_TIMESTAMP"

    def test_table_schema_with_multiple_columns(self):
        columns = (
            ColumnSchema(name="id", data_type="INTEGER", nullable=False, is_primary_key=True),
            ColumnSchema(name="email", data_type="TEXT", nullable=False),
            ColumnSchema(name="created_at", data_type="TIMESTAMP", nullable=False),
        )
        table = TableSchema(name="users", columns=columns, primary_key=("id",))
        assert len(table.columns) == 3
        assert table.primary_key == ("id",)

    def test_foreign_key_with_actions(self):
        fk = ForeignKey(
            column="user_id",
            referenced_table="users",
            referenced_column="id",
            on_delete="CASCADE",
            on_update="RESTRICT",
        )
        assert fk.on_delete == "CASCADE"
        assert fk.on_update == "RESTRICT"

    def test_index_schema_partial(self):
        idx = IndexSchema(
            name="idx_active_users",
            table_name="users",
            columns=("email",),
            unique=True,
            partial=True,
            where_clause="deleted_at IS NULL",
        )
        assert idx.partial is True
        assert idx.where_clause == "deleted_at IS NULL"

    def test_schema_snapshot_empty(self):
        snapshot = SchemaSnapshot(
            database_path="/tmp/empty.db",
            timestamp=1234567890,
        )
        assert len(snapshot.tables) == 0
        assert len(snapshot.indexes) == 0


class TestEnums:
    """Verify enum values for structural difference types."""

    def test_difference_type_values(self):
        assert DifferenceType.MISSING_COLUMN.value == "MISSING_COLUMN"
        assert DifferenceType.CONSTRAINT_MISMATCH.value == "CONSTRAINT_MISMATCH"
        assert DifferenceType.MISSING_TABLE.value == "MISSING_TABLE"
        assert DifferenceType.EXTRA_TABLE.value == "EXTRA_TABLE"
        assert DifferenceType.MISSING_INDEX.value == "MISSING_INDEX"

    def test_recovery_classification_values(self):
        assert RecoveryClassification.METADATA_DRIFT.value == "METADATA_DRIFT"
        assert RecoveryClassification.SCHEMA_DRIFT.value == "SCHEMA_DRIFT"
        assert RecoveryClassification.REPLAY_CONFLICT.value == "REPLAY_CONFLICT"
        assert RecoveryClassification.SUPERSEDED_MIGRATION.value == "SUPERSEDED_MIGRATION"
        assert RecoveryClassification.MISSING_MIGRATION.value == "MISSING_MIGRATION"
        assert RecoveryClassification.DESTRUCTIVE_MIGRATION.value == "DESTRUCTIVE_MIGRATION"
        assert RecoveryClassification.MANUAL_DATABASE_MODIFICATION.value == "MANUAL_DATABASE_MODIFICATION"
        assert RecoveryClassification.UNKNOWN_STATE.value == "UNKNOWN_STATE"

    def test_recovery_risk_values(self):
        assert RecoveryRisk.LOW.value == "LOW"
        assert RecoveryRisk.MEDIUM.value == "MEDIUM"
        assert RecoveryRisk.HIGH.value == "HIGH"
        assert RecoveryRisk.CRITICAL.value == "CRITICAL"

    def test_recovery_recommendation_values(self):
        assert RecoveryRecommendation.SAFE_SKIP.value == "SAFE_SKIP"
        assert RecoveryRecommendation.FORCE_RECORD.value == "FORCE_RECORD"
        assert RecoveryRecommendation.FORWARD_MIGRATION.value == "FORWARD_MIGRATION"
        assert RecoveryRecommendation.MANUAL_PATCH.value == "MANUAL_PATCH"
        assert RecoveryRecommendation.HALT.value == "HALT"


class TestTupleImmutability:
    """Verify tuple fields maintain immutability."""

    def test_table_columns_tuple_immutable(self):
        col = ColumnSchema(name="id", data_type="INTEGER", nullable=False)
        table = TableSchema(name="test_table", columns=(col,))
        with pytest.raises((TypeError, AttributeError)):
            table.columns[0] = ColumnSchema(name="new_id", data_type="TEXT", nullable=True)

    def test_index_columns_tuple_immutable(self):
        idx = IndexSchema(name="idx_test", table_name="test", columns=("id", "name"), unique=False)
        with pytest.raises(TypeError):
            idx.columns[0] = "new_column"

    def test_table_primary_key_tuple_immutable(self):
        table = TableSchema(
            name="test_table",
            columns=(ColumnSchema(name="id", data_type="INTEGER", nullable=False),),
            primary_key=("id",),
        )
        with pytest.raises(TypeError):
            table.primary_key[0] = "new_id"


class TestDecisionContext:
    """Sprint 2.3B: Verify DecisionContext construction and immutability."""

    def test_decision_context_construction(self):
        context = DecisionContext(
            applied_migration_names=("001_initial", "002_add_users", "003_add_indexes"),
            available_migration_files=("001_initial.sql", "002_add_users.sql", "003_add_indexes.sql"),
            migration_checksums={
                "001_initial": "abc123",
                "002_add_users": "def456",
                "003_add_indexes": "ghi789",
            },
        )
        assert len(context.applied_migration_names) == 3
        assert context.applied_migration_names[0] == "001_initial"
        assert len(context.available_migration_files) == 3
        assert context.migration_checksums["002_add_users"] == "def456"

    def test_decision_context_empty(self):
        context = DecisionContext(
            applied_migration_names=(),
            available_migration_files=(),
            migration_checksums={},
        )
        assert len(context.applied_migration_names) == 0
        assert len(context.available_migration_files) == 0
        assert len(context.migration_checksums) == 0

    def test_decision_context_tuple_fields_immutable(self):
        context = DecisionContext(
            applied_migration_names=("001_initial",),
            available_migration_files=("001_initial.sql",),
            migration_checksums={"001_initial": "abc123"},
        )
        with pytest.raises(TypeError):
            context.applied_migration_names[0] = "002_new"


class TestRecoveryDecision:
    """Sprint 2.3B: Verify RecoveryDecision construction, serialization, and immutability."""

    def test_recovery_decision_construction_minimal(self):
        diff = SchemaDifference(
            difference_type=DifferenceType.MISSING_COLUMN,
            table_name="users",
            column_name="email",
        )
        decision = RecoveryDecision(
            difference=diff,
            classification=RecoveryClassification.SCHEMA_DRIFT,
            risk=RecoveryRisk.HIGH,
            recommendation=RecoveryRecommendation.FORWARD_MIGRATION,
            rationale="Column configuration does not match the target schema.",
        )
        assert decision.difference == diff
        assert decision.classification == RecoveryClassification.SCHEMA_DRIFT
        assert decision.risk == RecoveryRisk.HIGH
        assert decision.recommendation == RecoveryRecommendation.FORWARD_MIGRATION
        assert len(decision.details) == 0

    def test_recovery_decision_construction_with_details(self):
        diff = SchemaDifference(
            difference_type=DifferenceType.MISSING_TABLE,
            table_name="audit_log",
            target_migration="005_add_audit",
        )
        decision = RecoveryDecision(
            difference=diff,
            classification=RecoveryClassification.METADATA_DRIFT,
            risk=RecoveryRisk.CRITICAL,
            recommendation=RecoveryRecommendation.HALT,
            rationale="Schema element has been recorded as applied, but is physically missing.",
            details={
                "ledger_status": "applied",
                "physical_status": "missing",
                "data_loss_risk": True,
            },
        )
        assert decision.details["ledger_status"] == "applied"
        assert decision.details["data_loss_risk"] is True

    def test_recovery_decision_to_dict(self):
        diff = SchemaDifference(
            difference_type=DifferenceType.EXTRA_TABLE,
            table_name="temp_data",
        )
        decision = RecoveryDecision(
            difference=diff,
            classification=RecoveryClassification.MANUAL_DATABASE_MODIFICATION,
            risk=RecoveryRisk.HIGH,
            recommendation=RecoveryRecommendation.MANUAL_PATCH,
            rationale="Elements exist physically but are absent from migration files.",
            details={"requires_dba": True},
        )
        result = decision.to_dict()

        assert result["classification"] == "MANUAL_DATABASE_MODIFICATION"
        assert result["risk"] == "HIGH"
        assert result["recommended_action"] == "MANUAL_PATCH"
        assert result["rationale"] == "Elements exist physically but are absent from migration files."
        assert result["details"]["requires_dba"] is True
        assert "difference" in result
        assert result["difference"]["difference_type"] == "EXTRA_TABLE"

    def test_recovery_decision_serialization_deterministic(self):
        diff = SchemaDifference(
            difference_type=DifferenceType.COLUMN_TYPE_MISMATCH,
            table_name="trades",
            column_name="price",
            details={"expected": "REAL", "actual": "TEXT"},
        )
        decision = RecoveryDecision(
            difference=diff,
            classification=RecoveryClassification.SCHEMA_DRIFT,
            risk=RecoveryRisk.MEDIUM,
            recommendation=RecoveryRecommendation.FORWARD_MIGRATION,
            rationale="Column configuration mismatch requires normalization.",
        )
        result1 = decision.to_dict()
        result2 = decision.to_dict()
        assert result1 == result2

    def test_recovery_decision_all_classifications(self):
        """Verify all ADR-023 classifications can be instantiated."""
        diff = SchemaDifference(difference_type=DifferenceType.MISSING_INDEX)

        classifications = [
            RecoveryClassification.METADATA_DRIFT,
            RecoveryClassification.SCHEMA_DRIFT,
            RecoveryClassification.REPLAY_CONFLICT,
            RecoveryClassification.SUPERSEDED_MIGRATION,
            RecoveryClassification.MISSING_MIGRATION,
            RecoveryClassification.DESTRUCTIVE_MIGRATION,
            RecoveryClassification.MANUAL_DATABASE_MODIFICATION,
            RecoveryClassification.UNKNOWN_STATE,
        ]

        for classification in classifications:
            decision = RecoveryDecision(
                difference=diff,
                classification=classification,
                risk=RecoveryRisk.LOW,
                recommendation=RecoveryRecommendation.SAFE_SKIP,
                rationale=f"Test {classification.value}",
            )
            assert decision.classification == classification

    def test_recovery_decision_all_risk_levels(self):
        """Verify all risk levels can be assigned."""
        diff = SchemaDifference(difference_type=DifferenceType.MISSING_COLUMN)

        risk_levels = [
            RecoveryRisk.LOW,
            RecoveryRisk.MEDIUM,
            RecoveryRisk.HIGH,
            RecoveryRisk.CRITICAL,
        ]

        for risk in risk_levels:
            decision = RecoveryDecision(
                difference=diff,
                classification=RecoveryClassification.SCHEMA_DRIFT,
                risk=risk,
                recommendation=RecoveryRecommendation.FORWARD_MIGRATION,
                rationale=f"Test {risk.value}",
            )
            assert decision.risk == risk

    def test_recovery_decision_all_recommendations(self):
        """Verify all recommendations can be assigned."""
        diff = SchemaDifference(difference_type=DifferenceType.EXTRA_COLUMN)

        recommendations = [
            RecoveryRecommendation.SAFE_SKIP,
            RecoveryRecommendation.FORCE_RECORD,
            RecoveryRecommendation.FORWARD_MIGRATION,
            RecoveryRecommendation.MANUAL_PATCH,
            RecoveryRecommendation.HALT,
        ]

        for recommendation in recommendations:
            decision = RecoveryDecision(
                difference=diff,
                classification=RecoveryClassification.REPLAY_CONFLICT,
                risk=RecoveryRisk.LOW,
                recommendation=recommendation,
                rationale=f"Test {recommendation.value}",
            )
            assert decision.recommendation == recommendation
