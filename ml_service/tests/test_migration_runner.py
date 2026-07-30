"""Comprehensive unit tests for MigrationRunner.

Tests cover:
- Constructor validation and initialization
- Exception hierarchy
- Method signatures and return types
- Immutability of instance variables
- Type safety
- BEGIN IMMEDIATE called
- commit called
- rollback called
- connection cleanup
- retry behavior (exponential backoff)
- dry-run isolation
- rollback after failure
- retry exhaustion
- deterministic ordering
"""

import os
import sqlite3
import time
from typing import Tuple
from unittest.mock import MagicMock, patch

import pytest

from ml_service.migrations.recovery.migration_runner import (
    MigrationRunner,
    MigrationRunnerError,
    DatabaseLockError,
    SQLParseException,
)


class TestMigrationRunnerConstruction:
    """Test suite for MigrationRunner instantiation and initialization."""

    def test_constructor_with_required_args(self) -> None:
        """MigrationRunner accepts db_path as required argument."""
        runner = MigrationRunner(db_path="/tmp/test.db")
        assert runner._db_path == "/tmp/test.db"
        assert runner._dry_run is False

    def test_constructor_with_dry_run_true(self) -> None:
        """MigrationRunner accepts dry_run flag."""
        runner = MigrationRunner(db_path="/tmp/test.db", dry_run=True)
        assert runner._db_path == "/tmp/test.db"
        assert runner._dry_run is True

    def test_constructor_with_dry_run_false(self) -> None:
        """MigrationRunner dry_run defaults to False."""
        runner = MigrationRunner(db_path="/tmp/test.db", dry_run=False)
        assert runner._dry_run is False

    def test_instance_variables_are_private(self) -> None:
        """Instance variables use private naming convention."""
        runner = MigrationRunner(db_path="/tmp/test.db")
        assert hasattr(runner, "_db_path")
        assert hasattr(runner, "_dry_run")

    def test_db_path_accepts_string(self) -> None:
        """Constructor accepts string path."""
        runner = MigrationRunner(db_path="/var/lib/production.db")
        assert runner._db_path == "/var/lib/production.db"


class TestExceptionHierarchy:
    """Test suite for custom exception types."""

    def test_migration_runner_error_is_exception(self) -> None:
        """MigrationRunnerError inherits from Exception."""
        assert issubclass(MigrationRunnerError, Exception)

    def test_database_lock_error_is_migration_runner_error(self) -> None:
        """DatabaseLockError inherits from MigrationRunnerError."""
        assert issubclass(DatabaseLockError, MigrationRunnerError)

    def test_sql_parse_exception_is_migration_runner_error(self) -> None:
        """SQLParseException inherits from MigrationRunnerError."""
        assert issubclass(SQLParseException, MigrationRunnerError)

    def test_database_lock_error_instantiation(self) -> None:
        """DatabaseLockError can be instantiated with message."""
        error = DatabaseLockError("Database locked after 3 retries")
        assert str(error) == "Database locked after 3 retries"

    def test_sql_parse_exception_instantiation(self) -> None:
        """SQLParseException can be instantiated with message."""
        error = SQLParseException("Invalid SQL syntax")
        assert str(error) == "Invalid SQL syntax"

    def test_migration_runner_error_instantiation(self) -> None:
        """MigrationRunnerError can be instantiated with message."""
        error = MigrationRunnerError("Generic runner error")
        assert str(error) == "Generic runner error"


class TestExecuteSqlStatementsSignature:
    """Test suite for execute_sql_statements method signature."""

    def test_method_exists(self) -> None:
        """execute_sql_statements method exists."""
        runner = MigrationRunner(db_path=":memory:")
        assert hasattr(runner, "execute_sql_statements")
        assert callable(runner.execute_sql_statements)

    def test_method_accepts_tuple_of_strings(self) -> None:
        """Method signature accepts tuple of strings and returns them."""
        runner = MigrationRunner(db_path=":memory:")
        statements: Tuple[str, ...] = ("SELECT 1;", "SELECT 2;")
        result = runner.execute_sql_statements(statements)
        assert result == statements

    def test_method_accepts_empty_tuple(self) -> None:
        """Method accepts empty tuple."""
        runner = MigrationRunner(db_path=":memory:")
        statements: Tuple[str, ...] = ()
        result = runner.execute_sql_statements(statements)
        assert result == ()


class TestRecordLedgerSignature:
    """Test suite for record_ledger method signature."""

    def test_method_exists(self) -> None:
        """record_ledger method exists."""
        runner = MigrationRunner(db_path="/tmp/test.db")
        assert hasattr(runner, "record_ledger")
        assert callable(runner.record_ledger)

    def test_method_accepts_string(self) -> None:
        """Method signature accepts migration name string and returns SQL."""
        runner = MigrationRunner(db_path="/tmp/test.db")
        result = runner.record_ledger("001_initial_schema.sql")
        assert "schema_migrations" in result
        assert "001_initial_schema.sql" in result

    def test_method_accepts_different_migration_names(self) -> None:
        """Method accepts various migration name formats."""
        runner = MigrationRunner(db_path="/tmp/test.db")
        result1 = runner.record_ledger("001_initial.sql")
        result2 = runner.record_ledger("002_add_users.sql")
        result3 = runner.record_ledger("003_add_indexes.sql")
        assert "001_initial.sql" in result1
        assert "002_add_users.sql" in result2
        assert "003_add_indexes.sql" in result3


class TestImmutability:
    """Test suite for immutability of MigrationRunner state."""

    def test_db_path_remains_constant(self) -> None:
        """Instance db_path does not change after construction."""
        original_path = ":memory:"
        runner = MigrationRunner(db_path=original_path)
        assert runner._db_path == original_path
        runner.execute_sql_statements(())
        assert runner._db_path == original_path

    def test_dry_run_flag_remains_constant(self) -> None:
        """Instance dry_run flag does not change after construction."""
        runner = MigrationRunner(db_path=":memory:", dry_run=True)
        assert runner._dry_run is True
        runner.execute_sql_statements(())
        assert runner._dry_run is True


class TestTypeAnnotations:
    """Test suite verifying type annotations are present."""

    def test_constructor_has_type_annotations(self) -> None:
        """Constructor parameters have type annotations."""
        import inspect
        sig = inspect.signature(MigrationRunner.__init__)
        assert sig.parameters["db_path"].annotation == str
        assert sig.parameters["dry_run"].annotation == bool

    def test_execute_sql_statements_has_return_annotation(self) -> None:
        """execute_sql_statements has return type annotation."""
        import inspect
        sig = inspect.signature(MigrationRunner.execute_sql_statements)
        assert sig.return_annotation != inspect.Parameter.empty

    def test_record_ledger_has_return_annotation(self) -> None:
        """record_ledger has return type annotation."""
        import inspect
        sig = inspect.signature(MigrationRunner.record_ledger)
        assert sig.return_annotation != inspect.Parameter.empty


class TestDryRunModeIsolation:
    """Test suite for dry_run mode initialization."""

    def test_dry_run_true_creates_read_only_runner(self) -> None:
        """MigrationRunner with dry_run=True is configured for read-only."""
        runner = MigrationRunner(db_path="/tmp/test.db", dry_run=True)
        assert runner._dry_run is True

    def test_dry_run_false_creates_write_runner(self) -> None:
        """MigrationRunner with dry_run=False is configured for write operations."""
        runner = MigrationRunner(db_path="/tmp/test.db", dry_run=False)
        assert runner._dry_run is False


class TestTransactionLifecycle:
    """Comprehensive unit tests for the sqlite transaction lifecycle and locking modes."""

    def test_begin_immediate_called(self) -> None:
        """Verify BEGIN IMMEDIATE is called when starting transaction."""
        runner = MigrationRunner(db_path=":memory:")
        with patch("sqlite3.connect") as mock_connect:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_connect.return_value = mock_conn
            mock_conn.cursor.return_value = mock_cursor

            runner.execute_sql_statements(("SELECT 1;",))

            mock_cursor.execute.assert_any_call("BEGIN IMMEDIATE")

    def test_commit_called(self) -> None:
        """Verify commit is called on successful execution."""
        runner = MigrationRunner(db_path=":memory:")
        with patch("sqlite3.connect") as mock_connect:
            mock_conn = MagicMock()
            mock_connect.return_value = mock_conn

            runner.execute_sql_statements(("SELECT 1;",))

            mock_conn.commit.assert_called_once()

    def test_rollback_called_on_failure(self) -> None:
        """Verify rollback is called if execution fails."""
        runner = MigrationRunner(db_path=":memory:")
        # Force a failure during the transaction
        with patch.object(runner, "_begin_transaction", side_effect=ValueError("Simulated Error")):
            with patch("sqlite3.connect") as mock_connect:
                mock_conn = MagicMock()
                mock_connect.return_value = mock_conn

                with pytest.raises(MigrationRunnerError, match="Transaction failed"):
                    runner.execute_sql_statements(("SELECT 1;",))

                mock_conn.rollback.assert_called_once()

    def test_connection_cleanup_on_success(self) -> None:
        """Verify connection is closed and cleaned up on success."""
        runner = MigrationRunner(db_path=":memory:")
        runner.execute_sql_statements(("SELECT 1;",))
        assert runner._conn is None

    def test_connection_cleanup_on_failure(self) -> None:
        """Verify connection is closed and cleaned up on failure."""
        runner = MigrationRunner(db_path=":memory:")
        with patch.object(runner, "_begin_transaction", side_effect=ValueError("Simulated Error")):
            with pytest.raises(MigrationRunnerError):
                runner.execute_sql_statements(("SELECT 1;",))
        assert runner._conn is None

    def test_retry_behavior_succeeds(self) -> None:
        """Verify retry policy handles locked database and succeeds within 3 retries."""
        runner = MigrationRunner(db_path=":memory:")
        with patch("sqlite3.connect") as mock_connect:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_connect.return_value = mock_conn
            mock_conn.cursor.return_value = mock_cursor

            # Fail twice with locked error, then succeed
            mock_cursor.execute.side_effect = [
                sqlite3.OperationalError("database is locked"),
                sqlite3.OperationalError("database is locked"),
                None,  # succeeds on 3rd attempt
            ]

            with patch("time.sleep") as mock_sleep:
                runner.execute_sql_statements(("SELECT 1;",))
                assert mock_sleep.call_count == 2
                # Check exponential backoff durations: 0.1s then 0.2s
                mock_sleep.assert_any_call(0.1)
                mock_sleep.assert_any_call(0.2)

    def test_retry_exhaustion_raises_lock_error(self) -> None:
        """Verify retry policy exhausts all 3 retries and raises DatabaseLockError."""
        runner = MigrationRunner(db_path=":memory:")
        with patch("sqlite3.connect") as mock_connect:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_connect.return_value = mock_conn
            mock_conn.cursor.return_value = mock_cursor

            # Fail consistently
            mock_cursor.execute.side_effect = sqlite3.OperationalError("database is locked")

            with patch("time.sleep") as mock_sleep:
                with pytest.raises(DatabaseLockError, match="Database remains locked after 3 retries"):
                    runner.execute_sql_statements(("SELECT 1;",))

                assert mock_sleep.call_count == 3
                mock_sleep.assert_any_call(0.1)
                mock_sleep.assert_any_call(0.2)
                mock_sleep.assert_any_call(0.4)

    def test_dry_run_isolation(self) -> None:
        """Verify dry-run mode executes zero modifications and opens as read-only."""
        runner = MigrationRunner(db_path="/tmp/fake.db", dry_run=True)
        with patch("sqlite3.connect") as mock_connect:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_connect.return_value = mock_conn
            mock_conn.cursor.return_value = mock_cursor

            runner.execute_sql_statements(("SELECT 1;",))

            # Verify no BEGIN IMMEDIATE was executed
            for call in mock_cursor.execute.mock_calls:
                assert "BEGIN" not in call[1][0]

            # Verify no commit was executed
            mock_conn.commit.assert_not_called()

            # Verify connection URI is read-only
            mock_connect.assert_called_once()
            args, kwargs = mock_connect.call_args
            assert "mode=ro" in args[0]
            assert kwargs.get("uri") is True

    def test_deterministic_ordering(self) -> None:
        """Verify statements are returned in the exact input order."""
        runner = MigrationRunner(db_path=":memory:")
        statements = ("CREATE TABLE t (id INT);", "INSERT INTO t VALUES (1);", "SELECT * FROM t;")
        result = runner.execute_sql_statements(statements)
        assert result == statements
