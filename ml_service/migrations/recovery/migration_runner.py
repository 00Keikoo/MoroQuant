"""Migration runner for executing SQL statements with transaction safety.

This module provides the low-level execution engine for database recovery operations.
It manages SQLite connections, transaction boundaries, and ledger updates.
"""

from typing import Tuple


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

    def execute_sql_statements(self, statements: Tuple[str, ...]) -> Tuple[str, ...]:
        """Executes a tuple of raw SQL statements inside a single transaction.

        Args:
            statements: SQL strings to execute.

        Returns:
            Tuple of successfully executed SQL strings.

        Raises:
            DatabaseLockError: If write lock cannot be obtained.
            MigrationRunnerError: If execution fails and is rolled back.
        """
        pass

    def record_ledger(self, migration_name: str) -> str:
        """Appends a migration entry to schema_migrations ledger inside the active transaction.

        Args:
            migration_name: Name of the migration script.

        Returns:
            The SQL statement executed.
        """
        pass
