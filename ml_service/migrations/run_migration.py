#!/usr/bin/env python3
"""Execute database migrations for MoroQuant trading system."""

import sys
from pathlib import Path

# Add ml_service directory to path BEFORE any imports so legacy imports work
sys.path.insert(0, str(Path(__file__).parent.parent))

import sqlite3
from ml_service.data.database import get_database
from ml_service.utils.logger import get_logger

logger = get_logger()


def get_applied_migrations() -> set:
    """
    Query schema_migrations table to get list of already-applied migrations.

    Returns:
        Set of migration filenames that have been applied
    """
    db = get_database()

    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT migration_name FROM schema_migrations")
            rows = cursor.fetchall()
            return {row[0] for row in rows}
    except sqlite3.OperationalError:
        # schema_migrations table doesn't exist yet
        return set()


def column_exists(cursor, table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = {row[1] for row in cursor.fetchall()}
    return column_name in columns


def table_exists(cursor, table_name: str) -> bool:
    """Check if a table exists."""
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,)
    )
    return cursor.fetchone() is not None


def strip_sql_comments(sql: str) -> str:
    """
    Remove SQL comments from a statement while preserving the code.

    Handles:
    - Single-line comments: -- comment
    - Multi-line comments: /* comment */
    """
    result = []
    i = 0
    while i < len(sql):
        # Check for multi-line comment
        if i < len(sql) - 1 and sql[i:i+2] == '/*':
            # Skip until we find */
            i += 2
            while i < len(sql) - 1:
                if sql[i:i+2] == '*/':
                    i += 2
                    break
                i += 1
            continue

        # Check for single-line comment
        if i < len(sql) - 1 and sql[i:i+2] == '--':
            # Skip until end of line
            while i < len(sql) and sql[i] != '\n':
                i += 1
            if i < len(sql):
                result.append('\n')  # Preserve the newline
                i += 1
            continue

        result.append(sql[i])
        i += 1

    return ''.join(result)


def apply_migration(migration_file: Path) -> bool:
    """
    Apply a SQL migration file to the database.

    Args:
        migration_file: Path to .sql migration file

    Returns:
        True if successful, False otherwise
    """
    db = get_database()

    logger.info(f"Applying migration: {migration_file.name}")

    try:
        with open(migration_file, 'r') as f:
            sql_statements = f.read()

        with db.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("BEGIN")

            try:
                # Check if migration uses temp tables (requires single execution context)
                uses_temp_tables = 'TEMP TABLE' in sql_statements.upper()

                if uses_temp_tables:
                    cursor.executescript(sql_statements)
                else:
                    # Strip comments and split by semicolon
                    cleaned_sql = strip_sql_comments(sql_statements)
                    for statement in cleaned_sql.split(';'):
                        statement = statement.strip()
                        if statement:
                            cursor.execute(statement)

                # Record migration in the SAME transaction
                cursor.execute(
                    "INSERT INTO schema_migrations (migration_name, applied_at) VALUES (?, CURRENT_TIMESTAMP)",
                    (migration_file.name,)
                )

                conn.commit()
            except Exception:
                conn.rollback()
                raise

        logger.info(f"✓ Migration applied: {migration_file.name}")
        return True

    except Exception as e:
        logger.error(f"✗ Migration failed: {e}")
        return False


def main():
    migrations_dir = Path(__file__).parent

    migration_files = sorted(migrations_dir.glob("*.sql"))

    if not migration_files:
        logger.warning("No migration files found")
        return

    applied_migrations = get_applied_migrations()

    logger.info(f"Found {len(migration_files)} migration(s)")
    logger.info(f"Already applied: {len(applied_migrations)} migration(s)")

    pending_migrations = [f for f in migration_files if f.name not in applied_migrations]

    if not pending_migrations:
        logger.info("✓ No pending migrations")
        return

    logger.info(f"Pending: {len(pending_migrations)} migration(s)")

    for migration_file in pending_migrations:
        success = apply_migration(migration_file)
        if not success:
            logger.error(f"Migration failed, stopping at: {migration_file.name}")
            sys.exit(1)

    logger.info("✓ All migrations completed successfully")


if __name__ == "__main__":
    main()
