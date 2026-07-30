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
from typing import Tuple, Any
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

                with pytest.raises(ValueError, match="Simulated Error"):
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
            with pytest.raises(ValueError, match="Simulated Error"):
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

            # Fail twice with locked error, then succeed for BEGIN IMMEDIATE, then succeed for SQL execution
            mock_cursor.execute.side_effect = [
                sqlite3.OperationalError("database is locked"),
                sqlite3.OperationalError("database is locked"),
                None,  # succeeds on 3rd attempt for BEGIN IMMEDIATE
                None,  # succeeds for SELECT 1;
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


class TestSqlExecutionLayer:
    """Comprehensive unit tests for the SQL Execution Layer."""

    def test_single_sql_execution(self, tmp_path) -> None:
        """Verify executing a single SQL statement works and returns metadata."""
        db_file = str(tmp_path / "test.db")
        runner = MigrationRunner(db_path=db_file)
        result = runner.execute_sql_statements(("CREATE TABLE test_single (id INT);",))
        assert result == ("CREATE TABLE test_single (id INT);",)

        # Verify side effects occurred in database
        runner._open_connection()
        cursor = runner._conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='test_single';")
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == "test_single"
        runner._close()

    def test_multiple_sql_execution(self, tmp_path) -> None:
        """Verify multiple SQL statements are executed sequentially."""
        db_file = str(tmp_path / "test.db")
        runner = MigrationRunner(db_path=db_file)
        statements = (
            "CREATE TABLE test_multi (id INT);",
            "INSERT INTO test_multi VALUES (42);",
            "INSERT INTO test_multi VALUES (100);",
        )
        result = runner.execute_sql_statements(statements)
        assert result == statements

        # Verify side effects occurred in database
        runner._open_connection()
        cursor = runner._conn.cursor()
        cursor.execute("SELECT id FROM test_multi ORDER BY id;")
        rows = cursor.fetchall()
        assert len(rows) == 2
        assert rows[0][0] == 42
        assert rows[1][0] == 100
        runner._close()

    def test_failure_on_second_statement(self, tmp_path) -> None:
        """Verify that execution stops immediately on the first SQL error (e.g. second statement)."""
        db_file = str(tmp_path / "test.db")
        runner = MigrationRunner(db_path=db_file)
        statements = (
            "CREATE TABLE test_fail (id INT);",
            "INSERT INTO test_fail VALUES ('not_an_int_but_ok');",
            "INVALID SQL STATEMENT HERE;",
            "INSERT INTO test_fail VALUES (999);",
        )
        with pytest.raises(sqlite3.OperationalError):
            runner.execute_sql_statements(statements)

        # The table should not even exist because of rollback
        runner._open_connection()
        cursor = runner._conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='test_fail';")
        assert cursor.fetchone() is None
        runner._close()

    def test_rollback_on_failure(self, tmp_path) -> None:
        """Verify that a failure triggers rollback through existing transaction lifecycle."""
        db_file = str(tmp_path / "test.db")
        runner = MigrationRunner(db_path=db_file)
        # Let's pre-create a table to check state
        runner._open_connection()
        runner._conn.execute("CREATE TABLE test_rollback (val TEXT);")
        runner._conn.execute("INSERT INTO test_rollback VALUES ('original');")
        runner._conn.commit()
        runner._close()

        statements = (
            "INSERT INTO test_rollback VALUES ('new_value');",
            "SOME WRONG SQL;",
        )

        with pytest.raises(sqlite3.OperationalError):
            runner.execute_sql_statements(statements)

        # Check that table state rolled back to 'original' and doesn't contain 'new_value'
        runner._open_connection()
        cursor = runner._conn.cursor()
        cursor.execute("SELECT val FROM test_rollback;")
        rows = cursor.fetchall()
        assert len(rows) == 1
        assert rows[0][0] == "original"
        runner._close()

    def test_deterministic_ordering(self) -> None:
        """Verify deterministic execution ordering."""
        # Using a mock cursor to track order of execution
        runner = MigrationRunner(db_path=":memory:")
        with patch("sqlite3.connect") as mock_connect:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_connect.return_value = mock_conn
            mock_conn.cursor.return_value = mock_cursor

            statements = ("SELECT 'first';", "SELECT 'second';", "SELECT 'third';")
            runner.execute_sql_statements(statements)

            # Check that mock_cursor.execute was called with each statement in order
            calls = [call[1][0] for call in mock_cursor.execute.mock_calls if "BEGIN" not in call[1][0]]
            assert calls == list(statements)

    def test_dry_run_executes_zero_sql(self) -> None:
        """Verify dry-run executes zero SQL modifications."""
        runner = MigrationRunner(db_path=":memory:", dry_run=True)
        statements = ("CREATE TABLE should_not_exist (id INT);",)
        result = runner.execute_sql_statements(statements)
        assert result == statements

        # Verify the table was not actually created
        runner._open_connection()
        cursor = runner._conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='should_not_exist';")
        assert cursor.fetchone() is None
        runner._close()

    def test_empty_statement_list(self) -> None:
        """Verify passing an empty statement list works and returns empty tuple."""
        runner = MigrationRunner(db_path=":memory:")
        result = runner.execute_sql_statements(())
        assert result == ()

    def test_sql_execution_exception_propagation(self) -> None:
        """Verify SQL execution exceptions propagate as their original exception type."""
        runner = MigrationRunner(db_path=":memory:")
        with pytest.raises(sqlite3.OperationalError) as exc_info:
            runner.execute_sql_statements(("SELECT * FROM non_existent_table;",))

        assert "no such table" in str(exc_info.value)


class TestMigrationRunnerExecutePlan:
    """Comprehensive unit tests for execute_plan and execute_action methods."""

    @pytest.fixture
    def sample_decision(self) -> Any:
        """Create a sample recovery decision."""
        from ml_service.migrations.recovery.models import (
            RecoveryDecision,
            SchemaDifference,
            DifferenceType,
            RecoveryClassification,
            RecoveryRisk,
            RecoveryRecommendation,
        )
        diff = SchemaDifference(
            difference_type=DifferenceType.MISSING_TABLE,
            target_migration="003_test_migration",
            table_name="test_table",
        )
        return RecoveryDecision(
            difference=diff,
            classification=RecoveryClassification.SCHEMA_DRIFT,
            risk=RecoveryRisk.MEDIUM,
            recommendation=RecoveryRecommendation.FORCE_RECORD,
            rationale="Test rationale",
        )

    def test_execute_plan_success_path(self, sample_decision) -> None:
        """Verify successful execute_plan execution path constructs ExecutionResult correctly."""
        runner = MigrationRunner(db_path=":memory:")
        results = runner.execute_plan((sample_decision,))
        assert isinstance(results, tuple)
        assert len(results) == 1

        result = results[0]
        from ml_service.migrations.recovery.models import ExecutionResult, ExecutionStatus
        assert isinstance(result, ExecutionResult)
        assert result.decision == sample_decision
        assert result.status == ExecutionStatus.SUCCESS
        assert result.rolled_back is False
        assert result.error_message is None
        assert result.duration_ms >= 0.0
        assert result.timestamp.endswith("Z")

    def test_execute_plan_multiple_action_ordering(self) -> None:
        """Verify that multiple decisions are executed in exact ordering."""
        from ml_service.migrations.recovery.models import (
            RecoveryDecision,
            SchemaDifference,
            DifferenceType,
            RecoveryClassification,
            RecoveryRisk,
            RecoveryRecommendation,
        )
        decisions = (
            RecoveryDecision(
                difference=SchemaDifference(DifferenceType.MISSING_TABLE, target_migration="001"),
                classification=RecoveryClassification.SCHEMA_DRIFT,
                risk=RecoveryRisk.LOW,
                recommendation=RecoveryRecommendation.SAFE_SKIP,
                rationale="Reason 1",
            ),
            RecoveryDecision(
                difference=SchemaDifference(DifferenceType.MISSING_TABLE, target_migration="002"),
                classification=RecoveryClassification.SCHEMA_DRIFT,
                risk=RecoveryRisk.LOW,
                recommendation=RecoveryRecommendation.FORCE_RECORD,
                rationale="Reason 2",
            ),
        )
        runner = MigrationRunner(db_path=":memory:")
        results = runner.execute_plan(decisions)
        assert len(results) == 2
        assert results[0].decision.difference.target_migration == "001"
        assert results[1].decision.difference.target_migration == "002"

    def test_execute_plan_dry_run_path(self, tmp_path, sample_decision) -> None:
        """Verify dry-run execution routes read-only and does not write or raise database lock issues."""
        db_file = str(tmp_path / "fake_dry_run.db")
        # Initialize an empty sqlite file first so that opening it mode=ro works
        conn = sqlite3.connect(db_file)
        conn.close()

        runner = MigrationRunner(db_path=db_file, dry_run=True)
        results = runner.execute_plan((sample_decision,))
        assert len(results) == 1
        assert results[0].status.value == "SUCCESS"
        assert results[0].rolled_back is False

    def test_execute_action_immutable_output(self, sample_decision) -> None:
        """Verify returned ExecutionResult output is immutable (frozen)."""
        runner = MigrationRunner(db_path=":memory:")
        result = runner.execute_action(sample_decision)
        with pytest.raises((AttributeError, TypeError)):
            result.status = "FAILED"  # type: ignore

    def test_execute_action_rollback_path_on_database_error(self, sample_decision) -> None:
        """Verify database transaction failure triggers rollback and propagates ExecutionError."""
        runner = MigrationRunner(db_path=":memory:")
        # Mock _begin_transaction to raise a database lock/operational error
        with patch.object(runner, "_begin_transaction", side_effect=sqlite3.OperationalError("database is locked")):
            from ml_service.migrations.recovery.executor import ExecutionError
            with pytest.raises(ExecutionError) as exc_info:
                runner.execute_action(sample_decision)
            assert "Database error during execution" in str(exc_info.value)

    def test_execute_action_exception_propagation_on_halt(self) -> None:
        """Verify RecoveryHaltedError propagates directly on HALT recommendation."""
        from ml_service.migrations.recovery.models import (
            RecoveryDecision,
            SchemaDifference,
            DifferenceType,
            RecoveryClassification,
            RecoveryRisk,
            RecoveryRecommendation,
        )
        halt_decision = RecoveryDecision(
            difference=SchemaDifference(DifferenceType.MISSING_TABLE, target_migration="003"),
            classification=RecoveryClassification.METADATA_DRIFT,
            risk=RecoveryRisk.CRITICAL,
            recommendation=RecoveryRecommendation.HALT,
            rationale="Halt requested",
        )
        runner = MigrationRunner(db_path=":memory:")
        from ml_service.migrations.recovery.executor import RecoveryHaltedError
        with pytest.raises(RecoveryHaltedError) as exc_info:
            runner.execute_action(halt_decision)
        assert "Recovery halted due to HALT recommendation" in str(exc_info.value)

    def test_execute_plan_rejects_non_tuple(self, sample_decision) -> None:
        """Verify execute_plan raises TypeError when input is not a tuple."""
        runner = MigrationRunner(db_path=":memory:")
        with pytest.raises(TypeError, match="decisions must be a tuple"):
            runner.execute_plan([sample_decision])  # type: ignore

    def test_execute_plan_rejects_non_decision_types(self) -> None:
        """Verify execute_plan raises TypeError if any item is not a RecoveryDecision."""
        runner = MigrationRunner(db_path=":memory:")
        with pytest.raises(TypeError, match="All decisions must be RecoveryDecision instances"):
            runner.execute_plan(("not_a_decision",))  # type: ignore

    def test_deterministic_timing_metadata(self, sample_decision) -> None:
        """Verify execution timing duration_ms is measured and returns positive/zero value."""
        runner = MigrationRunner(db_path=":memory:")
        result = runner.execute_action(sample_decision)
        assert isinstance(result.duration_ms, float)
        assert result.duration_ms >= 0.0

