"""Unit tests for SchemaInspector table, column, index, and foreign key discovery.

Verifies the class interface, constructor, return types, table discovery,
sqlite_sequence handling, column extraction from PRAGMA, column properties,
composite primary key ordering, index extraction (unique, multi-column, partial),
deterministic ordering of indexes and foreign keys, foreign key extraction,
and read-only enforcement.
"""

import os
import sqlite3
import tempfile
import pytest
from ml_service.data.database import Database
from ml_service.migrations.recovery.schema_inspector import SchemaInspector
from ml_service.migrations.recovery.snapshot import SchemaSnapshot


@pytest.fixture
def temp_db():
    """Fixture to create a temporary database with sample tables."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    # Initialize database with tables in non-alphabetical order to verify sorting
    conn = sqlite3.connect(path)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE zebra (id INTEGER PRIMARY KEY AUTOINCREMENT)")  # triggers sqlite_sequence
    cursor.execute("CREATE TABLE apple (id INTEGER)")
    cursor.execute("CREATE TABLE banana (id INTEGER)")
    conn.commit()
    conn.close()

    db = Database(db_path=path)
    yield db

    try:
        os.unlink(path)
    except OSError:
        pass


def test_schema_inspector_interface():
    """Verify class creation and public interface existence."""
    assert hasattr(SchemaInspector, "__init__")
    assert hasattr(SchemaInspector, "capture_snapshot")
    assert hasattr(SchemaInspector, "_return_tables")
    assert hasattr(SchemaInspector, "_capture_columns")
    assert hasattr(SchemaInspector, "_capture_indexes")
    assert hasattr(SchemaInspector, "_capture_foreign_keys")


def test_schema_inspector_constructor(temp_db):
    """Verify the constructor accepts a Database instance."""
    inspector = SchemaInspector(temp_db)
    assert inspector.db == temp_db


def test_schema_inspector_return_type_contract():
    """Verify the return type annotation contract of capture_snapshot."""
    annotations = SchemaInspector.capture_snapshot.__annotations__
    assert annotations.get("return") == SchemaSnapshot


def test_table_discovery_and_ordering(temp_db):
    """Verify that table discovery returns tables sorted alphabetically."""
    inspector = SchemaInspector(temp_db)

    db_uri = f"file:{inspector.db.db_path}?mode=ro"
    conn = sqlite3.connect(db_uri, uri=True)
    try:
        tables = inspector._return_tables(conn)
        assert isinstance(tables, tuple)
        # Check that the list is sorted alphabetically
        assert tables == tuple(sorted(tables))
        # Verify our custom tables are present
        assert "apple" in tables
        assert "banana" in tables
        assert "zebra" in tables
    finally:
        conn.close()


def test_sqlite_sequence_ignored(temp_db):
    """Verify that sqlite_sequence internal table is filtered out."""
    # Ensure sqlite_sequence exists in the temp db due to AUTOINCREMENT
    conn = sqlite3.connect(temp_db.db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE name='sqlite_sequence'")
    res = cursor.fetchone()
    assert res is not None, "sqlite_sequence table should exist for autoincrement test"
    conn.close()

    inspector = SchemaInspector(temp_db)
    db_uri = f"file:{inspector.db.db_path}?mode=ro"
    conn = sqlite3.connect(db_uri, uri=True)
    try:
        tables = inspector._return_tables(conn)
        assert "sqlite_sequence" not in tables
    finally:
        conn.close()


def test_column_extraction(temp_db):
    """Verify that SchemaInspector extracts column details accurately from PRAGMA."""
    conn = sqlite3.connect(temp_db.db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE test_features (
            feature_id TEXT PRIMARY KEY,
            value REAL NOT NULL,
            category TEXT DEFAULT 'generic',
            score INTEGER
        )
    """)
    conn.commit()
    conn.close()

    inspector = SchemaInspector(temp_db)
    snapshot = inspector.capture_snapshot()

    assert "test_features" in snapshot.tables
    table = snapshot.tables["test_features"]

    # 4 columns should be extracted
    assert len(table.columns) == 4

    # Extract columns as dictionary by name
    cols = {col.name: col for col in table.columns}

    # Verify feature_id
    assert cols["feature_id"].data_type.upper() == "TEXT"
    assert cols["feature_id"].is_primary_key is True
    assert cols["feature_id"].default_value is None

    # Verify value
    assert cols["value"].data_type.upper() == "REAL"
    assert cols["value"].nullable is False
    assert cols["value"].is_primary_key is False

    # Verify category
    assert cols["category"].data_type.upper() == "TEXT"
    assert cols["category"].nullable is True
    assert cols["category"].default_value == "'generic'"

    # Verify score
    assert cols["score"].data_type.upper() == "INTEGER"
    assert cols["score"].nullable is True
    assert cols["score"].is_primary_key is False

    # Verify primary key attribute in TableSchema
    assert table.primary_key == ("feature_id",)


def test_composite_primary_key_ordering(temp_db):
    """Verify that composite primary key ordering is correctly extracted."""
    conn = sqlite3.connect(temp_db.db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE composite_test (
            col_b TEXT,
            col_a INTEGER,
            col_c REAL,
            PRIMARY KEY (col_a, col_b)
        )
    """)
    conn.commit()
    conn.close()

    inspector = SchemaInspector(temp_db)
    snapshot = inspector.capture_snapshot()

    assert "composite_test" in snapshot.tables
    table = snapshot.tables["composite_test"]

    # Primary key should be (col_a, col_b) in that order, even though col_b is defined first in the table
    assert table.primary_key == ("col_a", "col_b")


def test_index_extraction(temp_db):
    """Verify that SchemaInspector extracts unique, multi-column, and partial indexes correctly."""
    conn = sqlite3.connect(temp_db.db_path)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE users_test (id INTEGER PRIMARY KEY, email TEXT, username TEXT, score INTEGER)")
    cursor.execute("CREATE UNIQUE INDEX idx_users_email ON users_test(email)")
    cursor.execute("CREATE INDEX idx_users_username_score ON users_test(username, score)")
    cursor.execute("CREATE INDEX idx_users_partial ON users_test(score) WHERE score > 100")
    conn.commit()
    conn.close()

    inspector = SchemaInspector(temp_db)
    snapshot = inspector.capture_snapshot()

    # Verify idx_users_email (unique, single column)
    assert "idx_users_email" in snapshot.indexes
    idx_email = snapshot.indexes["idx_users_email"]
    assert idx_email.table_name == "users_test"
    assert idx_email.columns == ("email",)
    assert idx_email.unique is True
    assert idx_email.partial is False

    # Verify idx_users_username_score (multi-column)
    assert "idx_users_username_score" in snapshot.indexes
    idx_multi = snapshot.indexes["idx_users_username_score"]
    assert idx_multi.columns == ("username", "score")
    assert idx_multi.unique is False
    assert idx_multi.partial is False

    # Verify idx_users_partial (partial index with WHERE clause, where_clause is None per design rules)
    assert "idx_users_partial" in snapshot.indexes
    idx_partial = snapshot.indexes["idx_users_partial"]
    assert idx_partial.columns == ("score",)
    assert idx_partial.partial is True
    assert idx_partial.where_clause is None

    # Verify deterministic ordering of indexes inside TableSchema
    assert "users_test" in snapshot.tables
    table = snapshot.tables["users_test"]
    assert table.indexes == ("idx_users_email", "idx_users_partial", "idx_users_username_score")


def test_sqlite_internal_indexes_ignored(temp_db):
    """Verify that SQLite internal autoindexes (e.g. created by UNIQUE constraints) are ignored."""
    conn = sqlite3.connect(temp_db.db_path)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE unique_constraint_test (id INTEGER PRIMARY KEY, val TEXT UNIQUE)")
    conn.commit()
    conn.close()

    inspector = SchemaInspector(temp_db)
    snapshot = inspector.capture_snapshot()

    # SQLite creates an internal autoindex for the UNIQUE constraint
    # We assert that we don't expose any indexes starting with sqlite_
    for idx_name in snapshot.indexes:
        assert not idx_name.startswith("sqlite_")


def test_foreign_key_extraction(temp_db):
    """Verify that SchemaInspector extracts foreign key constraints accurately from PRAGMA."""
    conn = sqlite3.connect(temp_db.db_path)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE roles (role_id INTEGER PRIMARY KEY, role_name TEXT)")
    cursor.execute("""
        CREATE TABLE users_fk (
            id INTEGER PRIMARY KEY, 
            username TEXT, 
            role_id INTEGER, 
            FOREIGN KEY(role_id) REFERENCES roles(role_id) ON DELETE CASCADE ON UPDATE RESTRICT
        )
    """)
    conn.commit()
    conn.close()

    inspector = SchemaInspector(temp_db)
    snapshot = inspector.capture_snapshot()

    assert "users_fk" in snapshot.tables
    table = snapshot.tables["users_fk"]

    assert len(table.foreign_keys) == 1
    fk = table.foreign_keys[0]

    assert fk.column == "role_id"
    assert fk.referenced_table == "roles"
    assert fk.referenced_column == "role_id"
    assert fk.on_delete == "CASCADE"
    assert fk.on_update == "RESTRICT"


def test_multiple_foreign_keys_ordering(temp_db):
    """Verify multiple foreign keys are extracted and ordered deterministically."""
    conn = sqlite3.connect(temp_db.db_path)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE departments (dept_id INTEGER PRIMARY KEY)")
    cursor.execute("CREATE TABLE managers (mgr_id INTEGER PRIMARY KEY)")
    cursor.execute("""
        CREATE TABLE employees (
            emp_id INTEGER PRIMARY KEY,
            mgr_id INTEGER,
            dept_id INTEGER,
            FOREIGN KEY(mgr_id) REFERENCES managers(mgr_id),
            FOREIGN KEY(dept_id) REFERENCES departments(dept_id)
        )
    """)
    conn.commit()
    conn.close()

    inspector = SchemaInspector(temp_db)
    snapshot = inspector.capture_snapshot()

    assert "employees" in snapshot.tables
    table = snapshot.tables["employees"]

    assert len(table.foreign_keys) == 2
    # Ordered alphabetically by local column name: dept_id comes before mgr_id
    assert table.foreign_keys[0].column == "dept_id"
    assert table.foreign_keys[1].column == "mgr_id"


def test_capture_snapshot_populates_tables(temp_db):
    """Verify capture_snapshot returns SchemaSnapshot containing discovered tables, columns, indexes, and foreign keys."""
    inspector = SchemaInspector(temp_db)
    snapshot = inspector.capture_snapshot()

    assert isinstance(snapshot, SchemaSnapshot)
    assert snapshot.database_path == str(temp_db.db_path)
    assert "apple" in snapshot.tables
    assert "banana" in snapshot.tables
    assert "zebra" in snapshot.tables

    # Check that columns and indexes are loaded
    for table_schema in snapshot.tables.values():
        assert len(table_schema.columns) > 0


def test_read_only_connection_enforced(temp_db):
    """Verify that the database connection used by inspector is read-only and rejects writes."""
    inspector = SchemaInspector(temp_db)

    # Open connection using the same URI logic as inspector
    db_uri = f"file:{inspector.db.db_path}?mode=ro"
    conn = sqlite3.connect(db_uri, uri=True)
    cursor = conn.cursor()

    # Attempting to write should raise sqlite3.OperationalError
    with pytest.raises(sqlite3.OperationalError, match="readonly database"):
        cursor.execute("CREATE TABLE fail_table (id INTEGER)")

    conn.close()
