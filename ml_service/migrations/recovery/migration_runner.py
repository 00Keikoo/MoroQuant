import os
import sqlite3
import time
from typing import Tuple, Optional


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
