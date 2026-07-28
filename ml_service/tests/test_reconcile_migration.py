#!/usr/bin/env python3
"""
Unit tests for reconcile_migration.py recovery utility.
"""

import sys
import json
import sqlite3
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to sys.path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent
sys.path.insert(0, str(project_root))

from ml_service.data.database import Database
from ml_service.migrations.recovery.reconcile_migration import (
    strip_sql_comments,
    parse_sql_requirements,
    check_table_exists,
    check_column_exists,
    check_index_exists,
    check_migration_recorded,
    calculate_checksum,
    main
)


@pytest.fixture
def temp_db():
    """Create a temporary test database with schema_migrations table."""
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
        conn.commit()

    yield db

    Path(db_path).unlink()


@pytest.fixture
def temp_migration_file(tmp_path):
    """Create a temporary migration file."""
    m_file = tmp_path / "029_enrich_execution_audit.sql"
    m_file.write_text("""-- Migration 029
ALTER TABLE execution_decisions ADD COLUMN source TEXT NOT NULL DEFAULT 'PAPER';
ALTER TABLE execution_decisions ADD COLUMN signal_timestamp INTEGER;
CREATE INDEX IF NOT EXISTS idx_exec_dec_src ON execution_decisions(source);
""")
    return m_file


def test_strip_sql_comments():
    sql = """-- comment
    SELECT * /* comment */ FROM test; -- comment
    /* multiline
    comment */
    """
    cleaned = strip_sql_comments(sql)
    assert "comment" not in cleaned
    # Normalize internal spaces to 1 space for assertion
    normalized = " ".join(cleaned.split())
    assert "SELECT * FROM test;" in normalized


def test_parse_sql_requirements():
    sql = """
    CREATE TABLE test_table (
        id INTEGER PRIMARY KEY,
        name TEXT,
        CHECK (name IS NOT NULL)
    );
    ALTER TABLE test_table ADD COLUMN email TEXT;
    CREATE INDEX idx_test ON test_table(name);
    """
    reqs = parse_sql_requirements(sql)
    assert {"type": "table", "table": "test_table"} in reqs
    assert {"type": "column", "table": "test_table", "column": "id"} in reqs
    assert {"type": "column", "table": "test_table", "column": "name"} in reqs
    assert {"type": "column", "table": "test_table", "column": "email"} in reqs
    assert {"type": "index", "index": "idx_test"} in reqs


def test_schema_checks(temp_db):
    with temp_db.get_connection() as conn:
        cursor = conn.cursor()
        
        # Test table check
        assert not check_table_exists(cursor, "execution_decisions")
        cursor.execute("CREATE TABLE execution_decisions (id INTEGER)")
        assert check_table_exists(cursor, "execution_decisions")

        # Test column check
        assert not check_column_exists(cursor, "execution_decisions", "source")
        cursor.execute("ALTER TABLE execution_decisions ADD COLUMN source TEXT")
        assert check_column_exists(cursor, "execution_decisions", "source")

        # Test index check
        assert not check_index_exists(cursor, "idx_exec_dec_src")
        cursor.execute("CREATE INDEX idx_exec_dec_src ON execution_decisions(source)")
        assert check_index_exists(cursor, "idx_exec_dec_src")

        # Test migration recorded
        assert not check_migration_recorded(cursor, "029_enrich_execution_audit.sql")
        cursor.execute("INSERT INTO schema_migrations (migration_name) VALUES ('029_enrich_execution_audit.sql')")
        assert check_migration_recorded(cursor, "029_enrich_execution_audit.sql")


def test_calculate_checksum(temp_migration_file):
    checksum = calculate_checksum(temp_migration_file)
    assert len(checksum) == 64  # SHA-256 is 64 hex characters


@patch("ml_service.migrations.recovery.reconcile_migration.get_database")
def test_dry_run_pass(mock_get_db, temp_db, temp_migration_file, capsys):
    mock_get_db.return_value = temp_db

    # Setup physical schema to satisfy the migration
    with temp_db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE execution_decisions (id INTEGER, source TEXT, signal_timestamp INTEGER)")
        cursor.execute("CREATE INDEX idx_exec_dec_src ON execution_decisions(source)")
        conn.commit()

    test_args = [
        "reconcile_migration.py",
        "--migration", temp_migration_file.name,
        "--dry-run"
    ]

    mock_proj_root = temp_migration_file.parent.parent
    migrations_dir = mock_proj_root / "ml_service" / "migrations"
    migrations_dir.mkdir(parents=True, exist_ok=True)
    dest = migrations_dir / temp_migration_file.name
    dest.write_text(temp_migration_file.read_text())

    with patch("sys.argv", test_args), \
         patch("ml_service.migrations.recovery.reconcile_migration.project_root", mock_proj_root), \
         pytest.raises(SystemExit) as e:
        main()

    assert e.value.code == 0
    captured = capsys.readouterr()
    assert "Physical Schema:\nPASS" in captured.out
    assert "Metadata:\nMISSING" in captured.out
    assert "Recovery:\nWOULD INSERT" in captured.out


@patch("ml_service.migrations.recovery.reconcile_migration.get_database")
def test_dry_run_fail(mock_get_db, temp_db, temp_migration_file, capsys):
    mock_get_db.return_value = temp_db

    # Do NOT setup physical schema (schema mismatch)
    test_args = [
        "reconcile_migration.py",
        "--migration", temp_migration_file.name,
        "--dry-run"
    ]

    mock_proj_root = temp_migration_file.parent.parent
    migrations_dir = mock_proj_root / "ml_service" / "migrations"
    migrations_dir.mkdir(parents=True, exist_ok=True)
    dest = migrations_dir / temp_migration_file.name
    dest.write_text(temp_migration_file.read_text())

    with patch("sys.argv", test_args), \
         patch("ml_service.migrations.recovery.reconcile_migration.project_root", mock_proj_root), \
         pytest.raises(SystemExit) as e:
        main()

    assert e.value.code == 1
    captured = capsys.readouterr()
    assert "Physical Schema:\nFAIL" in captured.out
    assert "Recovery:\nDENIED" in captured.out


@patch("ml_service.migrations.recovery.reconcile_migration.get_database")
def test_execute_success(mock_get_db, temp_db, temp_migration_file, capsys):
    mock_get_db.return_value = temp_db

    # Setup physical schema
    with temp_db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE execution_decisions (id INTEGER, source TEXT, signal_timestamp INTEGER)")
        cursor.execute("CREATE INDEX idx_exec_dec_src ON execution_decisions(source)")
        conn.commit()

    test_args = [
        "reconcile_migration.py",
        "--migration", temp_migration_file.name,
        "--execute"
    ]

    mock_proj_root = temp_migration_file.parent.parent
    migrations_dir = mock_proj_root / "ml_service" / "migrations"
    migrations_dir.mkdir(parents=True, exist_ok=True)
    dest = migrations_dir / temp_migration_file.name
    dest.write_text(temp_migration_file.read_text())

    with patch("sys.argv", test_args), \
         patch("ml_service.migrations.recovery.reconcile_migration.project_root", mock_proj_root), \
         patch("builtins.input", return_value="I UNDERSTAND"), \
         pytest.raises(SystemExit) as e:
        main()

    assert e.value.code == 0
    captured = capsys.readouterr()
    assert "Recovery executed successfully" in captured.out

    # Verify log file exists and is populated
    log_path = mock_proj_root / "logs" / "recovery_029.json"
    assert log_path.exists()
    with open(log_path, 'r') as f:
        log_data = json.load(f)
    assert log_data["verification result"] == "PASS"
    assert log_data["inserted"] is True
    assert log_data["rollback"] is False


@patch("ml_service.migrations.recovery.reconcile_migration.get_database")
def test_execute_already_applied(mock_get_db, temp_db, temp_migration_file, capsys):
    mock_get_db.return_value = temp_db

    # Setup physical schema and record in schema_migrations
    with temp_db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE execution_decisions (id INTEGER, source TEXT, signal_timestamp INTEGER)")
        cursor.execute("CREATE INDEX idx_exec_dec_src ON execution_decisions(source)")
        cursor.execute("INSERT INTO schema_migrations (migration_name) VALUES (?)", (temp_migration_file.name,))
        conn.commit()

    test_args = [
        "reconcile_migration.py",
        "--migration", temp_migration_file.name,
        "--execute"
    ]

    mock_proj_root = temp_migration_file.parent.parent
    migrations_dir = mock_proj_root / "ml_service" / "migrations"
    migrations_dir.mkdir(parents=True, exist_ok=True)
    dest = migrations_dir / temp_migration_file.name
    dest.write_text(temp_migration_file.read_text())

    with patch("sys.argv", test_args), \
         patch("ml_service.migrations.recovery.reconcile_migration.project_root", mock_proj_root), \
         pytest.raises(SystemExit) as e:
        main()

    assert e.value.code == 0
    captured = capsys.readouterr()
    assert "already recorded" in captured.out


@patch("ml_service.migrations.recovery.reconcile_migration.get_database")
def test_execute_no_confirm(mock_get_db, temp_db, temp_migration_file, capsys):
    mock_get_db.return_value = temp_db

    # Setup physical schema
    with temp_db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE execution_decisions (id INTEGER, source TEXT, signal_timestamp INTEGER)")
        cursor.execute("CREATE INDEX idx_exec_dec_src ON execution_decisions(source)")
        conn.commit()

    test_args = [
        "reconcile_migration.py",
        "--migration", temp_migration_file.name,
        "--execute"
    ]

    mock_proj_root = temp_migration_file.parent.parent
    migrations_dir = mock_proj_root / "ml_service" / "migrations"
    migrations_dir.mkdir(parents=True, exist_ok=True)
    dest = migrations_dir / temp_migration_file.name
    dest.write_text(temp_migration_file.read_text())

    with patch("sys.argv", test_args), \
         patch("ml_service.migrations.recovery.reconcile_migration.project_root", mock_proj_root), \
         patch("builtins.input", return_value="NO"), \
         pytest.raises(SystemExit) as e:
        main()

    assert e.value.code == 1
    captured = capsys.readouterr()
    assert "Abort" in captured.out


@patch("ml_service.migrations.recovery.reconcile_migration.get_database")
def test_execute_rollback(mock_get_db, temp_db, temp_migration_file, capsys):
    mock_get_db.return_value = temp_db

    # Setup physical schema
    with temp_db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE execution_decisions (id INTEGER, source TEXT, signal_timestamp INTEGER)")
        cursor.execute("CREATE INDEX idx_exec_dec_src ON execution_decisions(source)")
        conn.commit()

    test_args = [
        "reconcile_migration.py",
        "--migration", temp_migration_file.name,
        "--execute"
    ]

    mock_proj_root = temp_migration_file.parent.parent
    migrations_dir = mock_proj_root / "ml_service" / "migrations"
    migrations_dir.mkdir(parents=True, exist_ok=True)
    dest = migrations_dir / temp_migration_file.name
    dest.write_text(temp_migration_file.read_text())

    original_get_connection = temp_db.get_connection
    
    class MockedConnection:
        def __init__(self, real_conn):
            self.real_conn = real_conn
        def cursor(self):
            return self.real_conn.cursor()
        def commit(self):
            raise sqlite3.OperationalError("Mocked commit error")
        def rollback(self):
            self.real_conn.rollback()
        def __getattr__(self, name):
            return getattr(self.real_conn, name)

    class MockConnectionContext:
        def __init__(self, real_ctx):
            self.real_ctx = real_ctx
            self.conn = None
        def __enter__(self):
            self.conn = self.real_ctx.__enter__()
            return MockedConnection(self.conn)
        def __exit__(self, exc_type, exc_val, exc_tb):
            return self.real_ctx.__exit__(exc_type, exc_val, exc_tb)

    temp_db.get_connection = lambda: MockConnectionContext(original_get_connection())

    with patch("sys.argv", test_args), \
         patch("ml_service.migrations.recovery.reconcile_migration.project_root", mock_proj_root), \
         patch("builtins.input", return_value="I UNDERSTAND"), \
         pytest.raises(SystemExit) as e:
        main()

    assert e.value.code == 1
    captured = capsys.readouterr()
    assert "Recovery execution failed" in captured.out
