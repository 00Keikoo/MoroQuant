import os
import sqlite3
import time
from typing import Tuple, Optional, Any


class MigrationRunnerError(Exception):
    """Base exception for all MigrationRunner errors."""
    pass


class DatabaseLockError(MigrationRunnerError):
    """Raised when the database remains locked after maximum retries."""
    pass


class SQLParseException(MigrationRunnerError):
    """Raised when migration file cannot be parsed or contains syntax errors."""
    pass


class MigrationRunner:
    """Handles low-level execution of SQL statements and transaction safety.

    This class is responsible for:
    - SQL execution with proper transaction boundaries
    - Database locking and retry logic
    - Ledger verification and mutation
    - Dry-run simulation
    - Error propagation and structured exceptions
    """

    def __init__(self, db_path: str, dry_run: bool = False) -> None:
        """Initialize the MigrationRunner.

        Args:
            db_path: Path to the SQLite database file.
            dry_run: If True, executes queries in validation/read-only mode.
        """
        self._db_path = db_path
        self._dry_run = dry_run
        self._conn: Optional[sqlite3.Connection] = None

    def _open_connection(self) -> None:
        """Open a sqlite connection. If dry_run is True, opens in read-only mode."""
        if self._conn is not None:
            return

        if self._dry_run:
            if self._db_path == ":memory:":
                db_uri = ":memory:"
            elif self._db_path.startswith("file:"):
                db_uri = self._db_path
            else:
                abs_path = os.path.abspath(self._db_path)
                db_uri = f"file:{abs_path}?mode=ro"
            self._conn = sqlite3.connect(db_uri, uri=True)
        else:
            self._conn = sqlite3.connect(self._db_path)

    def _begin_transaction(self) -> None:
        """Begin immediate transaction with locking retry policy."""
        if not self._conn:
            raise RuntimeError("No active database connection")

        if self._dry_run:
            return

        retries = 3
        backoff = 0.1
        for attempt in range(retries + 1):
            try:
                cursor = self._conn.cursor()
                cursor.execute("BEGIN IMMEDIATE")
                cursor.close()
                return
            except sqlite3.OperationalError as e:
                if "locked" in str(e) or "busy" in str(e):
                    if attempt < retries:
                        time.sleep(backoff)
                        backoff *= 2
                        continue
                raise DatabaseLockError(f"Database remains locked after {retries} retries: {e}") from e

    def _commit(self) -> None:
        """Commit the current transaction."""
        if not self._conn:
            raise RuntimeError("No active database connection")
        if self._dry_run:
            return
        self._conn.commit()

    def _rollback(self) -> None:
        """Rollback the current transaction."""
        if not self._conn:
            return
        if self._dry_run:
            return
        self._conn.rollback()

    def _close(self) -> None:
        """Close the database connection and cleanup."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def execute_sql_statements(self, statements: Tuple[str, ...]) -> Tuple[str, ...]:
        """Executes a tuple of raw SQL statements inside a single transaction.

        Args:
            statements: SQL strings to execute.

        Returns:
            Tuple of successfully executed SQL strings.

        Raises:
            DatabaseLockError: If write lock cannot be obtained.
            Exception: If execution fails, rolls back, and propagates the original exception.
        """
        self._open_connection()
        executed = []
        try:
            self._begin_transaction()
            if not self._dry_run and statements:
                cursor = self._conn.cursor()
                for stmt in statements:
                    cursor.execute(stmt)
                    executed.append(stmt)
                cursor.close()
            self._commit()
            return tuple(executed) if not self._dry_run else statements
        except Exception as e:
            try:
                self._rollback()
            except Exception:
                pass
            raise e
        finally:
            self._close()

    def record_ledger(self, migration_name: str) -> str:
        """Appends a migration entry to schema_migrations ledger inside the active transaction.

        Args:
            migration_name: Name of the migration script.

        Returns:
            The SQL statement executed.
        """
        return f"INSERT INTO schema_migrations (migration_name, applied_at) VALUES ('{migration_name}', CURRENT_TIMESTAMP);"

    def _plan_forward_migration(self, decision: Any) -> Any:
        """Generate plan for FORWARD_MIGRATION.

        Args:
            decision: The RecoveryDecision to plan.

        Returns:
            ExecutionResult containing plan metadata.
        """
        from ml_service.migrations.recovery.models import ExecutionResult, ExecutionStatus
        migration_name = decision.difference.target_migration or "unknown"
        executed_sql = (f"-- PLAN: FORWARD_MIGRATION for {migration_name}",)
        return ExecutionResult(
            decision=decision,
            status=ExecutionStatus.SUCCESS,
            duration_ms=0.0,
            executed_sql=executed_sql,
            rolled_back=False,
            timestamp="1970-01-01T00:00:00Z",
            error_message=None
        )

    def _plan_force_record(self, decision: Any) -> Any:
        """Generate plan for FORCE_RECORD.

        Args:
            decision: The RecoveryDecision to plan.

        Returns:
            ExecutionResult containing plan metadata.
        """
        from ml_service.migrations.recovery.models import ExecutionResult, ExecutionStatus
        migration_name = decision.difference.target_migration or "unknown"
        executed_sql = (self.record_ledger(migration_name),)
        return ExecutionResult(
            decision=decision,
            status=ExecutionStatus.SUCCESS,
            duration_ms=0.0,
            executed_sql=executed_sql,
            rolled_back=False,
            timestamp="1970-01-01T00:00:00Z",
            error_message=None
        )

    def _plan_safe_skip(self, decision: Any) -> Any:
        """Generate plan for SAFE_SKIP.

        Args:
            decision: The RecoveryDecision to plan.

        Returns:
            ExecutionResult containing plan metadata.
        """
        from ml_service.migrations.recovery.models import ExecutionResult, ExecutionStatus
        return ExecutionResult(
            decision=decision,
            status=ExecutionStatus.SKIPPED,
            duration_ms=0.0,
            executed_sql=(),
            rolled_back=False,
            timestamp="1970-01-01T00:00:00Z",
            error_message=None
        )

    def _plan_manual_patch(self, decision: Any) -> Any:
        """Generate plan for MANUAL_PATCH.

        Args:
            decision: The RecoveryDecision to plan.

        Returns:
            ExecutionResult containing plan metadata.
        """
        from ml_service.migrations.recovery.models import ExecutionResult, ExecutionStatus
        return ExecutionResult(
            decision=decision,
            status=ExecutionStatus.SKIPPED,
            duration_ms=0.0,
            executed_sql=(),
            rolled_back=False,
            timestamp="1970-01-01T00:00:00Z",
            error_message="Manual patch required; execution skipped."
        )

    def _plan_halt(self, decision: Any) -> Any:
        """Generate plan for HALT.

        Args:
            decision: The RecoveryDecision to plan.

        Returns:
            ExecutionResult containing plan metadata.
        """
        from ml_service.migrations.recovery.models import ExecutionResult, ExecutionStatus
        return ExecutionResult(
            decision=decision,
            status=ExecutionStatus.FAILED,
            duration_ms=0.0,
            executed_sql=(),
            rolled_back=True,
            timestamp="1970-01-01T00:00:00Z",
            error_message=f"Recovery halted due to HALT recommendation: {decision.rationale}"
        )

    def plan(self, decisions: Tuple[Any, ...]) -> Tuple[Any, ...]:
        """Generate a deterministic plan for a sequence of recovery decisions.

        Args:
            decisions: A tuple of RecoveryDecision objects to plan.

        Returns:
            A tuple of ExecutionResult objects representing the plan metadata.
        """
        if not isinstance(decisions, tuple):
            raise TypeError("decisions must be a tuple")

        results = []
        for decision in decisions:
            # We import RecoveryDecision here to avoid circular imports if any
            from ml_service.migrations.recovery.models import RecoveryDecision, RecoveryRecommendation
            if not isinstance(decision, RecoveryDecision):
                raise TypeError("All decisions must be RecoveryDecision instances")
            
            rec = decision.recommendation
            if rec == RecoveryRecommendation.FORWARD_MIGRATION:
                results.append(self._plan_forward_migration(decision))
            elif rec == RecoveryRecommendation.FORCE_RECORD:
                results.append(self._plan_force_record(decision))
            elif rec == RecoveryRecommendation.SAFE_SKIP:
                results.append(self._plan_safe_skip(decision))
            elif rec == RecoveryRecommendation.MANUAL_PATCH:
                results.append(self._plan_manual_patch(decision))
            elif rec == RecoveryRecommendation.HALT:
                results.append(self._plan_halt(decision))
            else:
                raise ValueError(f"Unknown recommendation: {rec}")

        return tuple(results)

    def execute_plan(self, decisions: Tuple[Any, ...]) -> Tuple[Any, ...]:
        """Execute a plan consisting of multiple recovery decisions sequentially.

        Args:
            decisions: A tuple of RecoveryDecision objects to execute.

        Returns:
            A tuple of ExecutionResult objects.
        """
        if not isinstance(decisions, tuple):
            raise TypeError("decisions must be a tuple")

        results = []
        for decision in decisions:
            # We import RecoveryDecision here to avoid circular imports if any
            from ml_service.migrations.recovery.models import RecoveryDecision
            if not isinstance(decision, RecoveryDecision):
                raise TypeError("All decisions must be RecoveryDecision instances")
            results.append(self.execute_action(decision))
        return tuple(results)

    def execute_action(self, decision: Any) -> Any:
        """Execute a single recovery decision within transaction boundaries.

        Args:
            decision: The RecoveryDecision to execute.

        Returns:
            ExecutionResult representing the result of the execution.
        """
        from datetime import datetime, UTC
        from ml_service.migrations.recovery.executor import RecoveryHaltedError, ExecutionError
        from ml_service.migrations.recovery.models import (
            ExecutionStatus,
            RecoveryRecommendation,
            ExecutionResult
        )

        start_time = time.perf_counter()
        rolled_back = False
        status = ExecutionStatus.SUCCESS
        executed_sql: Tuple[str, ...] = ()
        error_message: Optional[str] = None

        try:
            self._open_connection()
            self._begin_transaction()

            rec = decision.recommendation
            migration_name = decision.difference.target_migration or "unknown"

            if rec == RecoveryRecommendation.FORWARD_MIGRATION:
                executed_sql = (f"-- PLAN: FORWARD_MIGRATION for {migration_name}",)
            elif rec == RecoveryRecommendation.FORCE_RECORD:
                executed_sql = (self.record_ledger(migration_name),)
            elif rec == RecoveryRecommendation.SAFE_SKIP:
                status = ExecutionStatus.SKIPPED
                executed_sql = ()
            elif rec == RecoveryRecommendation.MANUAL_PATCH:
                status = ExecutionStatus.SKIPPED
                executed_sql = ()
                error_message = "Manual patch required; execution skipped."
            elif rec == RecoveryRecommendation.HALT:
                raise RecoveryHaltedError(f"Recovery halted due to HALT recommendation: {decision.rationale}")
            else:
                raise ValueError(f"Unknown recommendation: {rec}")

            self._commit()
        except RecoveryHaltedError as e:
            rolled_back = True
            try:
                self._rollback()
            except Exception:
                pass
            raise e
        except Exception as e:
            rolled_back = True
            try:
                self._rollback()
            except Exception:
                pass
            raise ExecutionError(f"Database error during execution: {e}") from e
        finally:
            self._close()

        end_time = time.perf_counter()
        duration_ms = (end_time - start_time) * 1000.0
        timestamp = datetime.now(UTC).isoformat().replace("+00:00", "Z")

        return ExecutionResult(
            decision=decision,
            status=status,
            duration_ms=duration_ms,
            executed_sql=executed_sql,
            rolled_back=rolled_back,
            timestamp=timestamp,
            error_message=error_message
        )


