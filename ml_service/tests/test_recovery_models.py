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
