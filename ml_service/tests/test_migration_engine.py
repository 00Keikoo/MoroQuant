#!/usr/bin/env python3
"""Regression tests for migration engine transaction boundaries and idempotency."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import sqlite3
import tempfile
import pytest
from unittest.mock import patch

from ml_service.data.database import Database
from ml_service.migrations.run_migration import (
    apply_migration,
    get_applied_migrations,
    column_exists,
    table_exists
)


@pytest.fixture
def test_db():
    """Create a test database with schema_migrations table."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    db = Database(db_path)

    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                migration_name TEXT NOT NULL UNIQUE,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS test_table (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            )
        """)
        conn.commit()

    yield db

    Path(db_path).unlink()


@pytest.fixture
def temp_migration_dir(tmp_path):
    """Create a temporary directory for migration files."""
    return tmp_path


def test_successful_migration_records_in_schema_migrations(test_db, temp_migration_dir):
    """Test that successful migrations are recorded in schema_migrations."""
    migration_file = temp_migration_dir / "001_add_column.sql"
    migration_file.write_text("ALTER TABLE test_table ADD COLUMN age INTEGER DEFAULT 0;")

    with patch('ml_service.migrations.run_migration.get_database', return_value=test_db):
        success = apply_migration(migration_file)

    assert success is True

    with test_db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT migration_name FROM schema_migrations WHERE migration_name = ?",
                      (migration_file.name,))
        result = cursor.fetchone()

    assert result is not None
    assert result[0] == migration_file.name


def test_failed_migration_does_not_record_in_schema_migrations(test_db, temp_migration_dir):
    """Test that failed migrations do NOT record in schema_migrations (rollback behavior)."""
    migration_file = temp_migration_dir / "002_duplicate_column.sql"
    migration_file.write_text("""
        ALTER TABLE test_table ADD COLUMN status TEXT DEFAULT 'active';
        ALTER TABLE test_table ADD COLUMN status TEXT DEFAULT 'active';
    """)

    with patch('ml_service.migrations.run_migration.get_database', return_value=test_db):
        success = apply_migration(migration_file)

    assert success is False

    with test_db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT migration_name FROM schema_migrations WHERE migration_name = ?",
                      (migration_file.name,))
        result = cursor.fetchone()

    assert result is None


def test_rollback_prevents_partial_migration(test_db, temp_migration_dir):
    """Test that rollback prevents partial application of multi-statement migrations."""
    migration_file = temp_migration_dir / "003_partial_migration.sql"
    migration_file.write_text("""
        ALTER TABLE test_table ADD COLUMN email TEXT;
        ALTER TABLE test_table ADD COLUMN phone TEXT;
        ALTER TABLE nonexistent_table ADD COLUMN invalid TEXT;
    """)

    with patch('ml_service.migrations.run_migration.get_database', return_value=test_db):
        success = apply_migration(migration_file)

    assert success is False

    with test_db.get_connection() as conn:
        cursor = conn.cursor()

        has_email = column_exists(cursor, 'test_table', 'email')
        has_phone = column_exists(cursor, 'test_table', 'phone')

    assert has_email is False
    assert has_phone is False


def test_duplicate_table_fails_cleanly(test_db, temp_migration_dir):
    """Test that creating a duplicate table fails without recording migration."""
    migration_file = temp_migration_dir / "004_duplicate_table.sql"
    migration_file.write_text("""
        CREATE TABLE test_table (
            id INTEGER PRIMARY KEY,
            duplicate TEXT
        );
    """)

    with patch('ml_service.migrations.run_migration.get_database', return_value=test_db):
        success = apply_migration(migration_file)

    assert success is False

    with test_db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT migration_name FROM schema_migrations WHERE migration_name = ?",
                      (migration_file.name,))
        result = cursor.fetchone()

    assert result is None


def test_migration_with_syntax_error_does_not_record(test_db, temp_migration_dir):
    """Test that migrations with syntax errors fail cleanly without recording."""
    migration_file = temp_migration_dir / "005_syntax_error.sql"
    migration_file.write_text("THIS IS NOT VALID SQL AT ALL;")

    with patch('ml_service.migrations.run_migration.get_database', return_value=test_db):
        success = apply_migration(migration_file)

    assert success is False

    with test_db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT migration_name FROM schema_migrations WHERE migration_name = ?",
                      (migration_file.name,))
        result = cursor.fetchone()

    assert result is None


def test_schema_migrations_consistency_after_multiple_failures(test_db, temp_migration_dir):
    """Test schema_migrations consistency after multiple migration failures."""
    migrations = [
        ("001_success.sql", "ALTER TABLE test_table ADD COLUMN field1 TEXT;"),
        ("002_fail.sql", "ALTER TABLE test_table ADD COLUMN field2 TEXT; ALTER TABLE test_table ADD COLUMN field2 TEXT;"),
        ("003_success.sql", "ALTER TABLE test_table ADD COLUMN field3 TEXT;"),
        ("004_fail.sql", "ALTER TABLE nonexistent ADD COLUMN invalid TEXT;"),
    ]

    expected_applied = []

    for migration_name, sql in migrations:
        migration_file = temp_migration_dir / migration_name
        migration_file.write_text(sql)

        with patch('ml_service.migrations.run_migration.get_database', return_value=test_db):
            success = apply_migration(migration_file)

        if success:
            expected_applied.append(migration_name)

    with patch('ml_service.migrations.run_migration.get_database', return_value=test_db):
        applied_migrations = get_applied_migrations()

    assert applied_migrations == set(expected_applied)
    assert "001_success.sql" in applied_migrations
    assert "002_fail.sql" not in applied_migrations
    assert "003_success.sql" in applied_migrations
    assert "004_fail.sql" not in applied_migrations


def test_column_exists_utility():
    """Test column_exists helper function."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
        conn.commit()

        assert column_exists(cursor, 'test', 'id') is True
        assert column_exists(cursor, 'test', 'name') is True
        assert column_exists(cursor, 'test', 'nonexistent') is False

        conn.close()
    finally:
        Path(db_path).unlink()


def test_table_exists_utility():
    """Test table_exists helper function."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE existing_table (id INTEGER PRIMARY KEY)")
        conn.commit()

        assert table_exists(cursor, 'existing_table') is True
        assert table_exists(cursor, 'nonexistent_table') is False

        conn.close()
    finally:
        Path(db_path).unlink()


def test_idempotent_migration_with_column_check(test_db, temp_migration_dir):
    """Test that migrations can be made idempotent using column_exists."""
    migration_file = temp_migration_dir / "006_idempotent.sql"
    migration_file.write_text("ALTER TABLE test_table ADD COLUMN idempotent_field TEXT;")

    with patch('ml_service.migrations.run_migration.get_database', return_value=test_db):
        success = apply_migration(migration_file)

    assert success is True

    with test_db.get_connection() as conn:
        cursor = conn.cursor()
        assert column_exists(cursor, 'test_table', 'idempotent_field') is True


def test_temp_table_migration_preserves_context(test_db, temp_migration_dir):
    """Test that migrations using temp tables execute in single context."""
    migration_file = temp_migration_dir / "007_temp_table.sql"
    migration_file.write_text("""
        CREATE TEMP TABLE temp_data (value INTEGER);
        INSERT INTO temp_data VALUES (1), (2), (3);
        INSERT INTO test_table (name) SELECT 'entry_' || value FROM temp_data;
    """)

    with patch('ml_service.migrations.run_migration.get_database', return_value=test_db):
        success = apply_migration(migration_file)

    assert success is True

    with test_db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM test_table WHERE name LIKE 'entry_%'")
        count = cursor.fetchone()[0]

    assert count == 3


def test_migration_024_regression_single_line_comments_before_create_table(test_db, temp_migration_dir):
    """
    Regression test for migration 024 bug.

    Bug: Parser split by ';' and skipped blocks starting with '--'.
    Result: Comments before CREATE TABLE caused entire block to be skipped.
    """
    migration_file = temp_migration_dir / "024_regime_blocks.sql"
    migration_file.write_text("""-- Migration 024: Regime Execution Policy - Structural Blocking Support
--
-- Creates table to support manual structural blocking of regimes as defined in
-- docs/research/regime_execution_policy.md Section 6 (Decision Rules).
--
-- Structural blocks are static overrides for regimes that cannot be traded due to
-- system design limits (e.g., API constraints, execution infrastructure gaps).

CREATE TABLE IF NOT EXISTS regime_blocks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    regime TEXT NOT NULL UNIQUE,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0, 1)),
    reason TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_regime_blocks_regime ON regime_blocks(regime);
CREATE INDEX IF NOT EXISTS idx_regime_blocks_active ON regime_blocks(is_active);
""")

    with patch('ml_service.migrations.run_migration.get_database', return_value=test_db):
        success = apply_migration(migration_file)

    assert success is True

    with test_db.get_connection() as conn:
        cursor = conn.cursor()

        assert table_exists(cursor, 'regime_blocks') is True

        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_regime_blocks_regime'")
        assert cursor.fetchone() is not None

        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_regime_blocks_active'")
        assert cursor.fetchone() is not None


def test_multiline_comments_before_statements(test_db, temp_migration_dir):
    """Test that multi-line comments before statements are handled correctly."""
    migration_file = temp_migration_dir / "008_multiline_comments.sql"
    migration_file.write_text("""/* This is a multi-line comment
 * that spans several lines
 * and precedes a CREATE TABLE statement
 */
CREATE TABLE IF NOT EXISTS multiline_test (
    id INTEGER PRIMARY KEY,
    value TEXT
);

/* Another multi-line comment */
CREATE INDEX IF NOT EXISTS idx_multiline_value ON multiline_test(value);
""")

    with patch('ml_service.migrations.run_migration.get_database', return_value=test_db):
        success = apply_migration(migration_file)

    assert success is True

    with test_db.get_connection() as conn:
        cursor = conn.cursor()
        assert table_exists(cursor, 'multiline_test') is True


def test_mixed_comments_and_statements(test_db, temp_migration_dir):
    """Test handling of mixed single-line and multi-line comments with statements."""
    migration_file = temp_migration_dir / "009_mixed_comments.sql"
    migration_file.write_text("""-- Single line comment at top

/* Multi-line comment
   spanning multiple lines */

-- Another single line comment
CREATE TABLE IF NOT EXISTS mixed_test (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL
);

-- Comment between statements
/* Another multi-line comment */

INSERT INTO mixed_test (name) VALUES ('test1');
INSERT INTO mixed_test (name) VALUES ('test2'); -- inline comment

-- Final comment
ALTER TABLE mixed_test ADD COLUMN status TEXT DEFAULT 'active';
""")

    with patch('ml_service.migrations.run_migration.get_database', return_value=test_db):
        success = apply_migration(migration_file)

    assert success is True

    with test_db.get_connection() as conn:
        cursor = conn.cursor()
        assert table_exists(cursor, 'mixed_test') is True
        assert column_exists(cursor, 'mixed_test', 'status') is True

        cursor.execute("SELECT COUNT(*) FROM mixed_test")
        count = cursor.fetchone()[0]
        assert count == 2
