#!/usr/bin/env python3
"""Execute database migrations for MoroQuant trading system."""

import sys
from pathlib import Path

# Add ml_service directory to path BEFORE any imports so legacy imports work
sys.path.insert(0, str(Path(__file__).parent.parent))

import sqlite3
from data.database import get_database
from utils.logger import get_logger

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


def record_migration(migration_name: str) -> None:
    """
    Record a successfully applied migration in schema_migrations table.

    Args:
        migration_name: Name of the migration file
    """
    db = get_database()

    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO schema_migrations (migration_name, applied_at) VALUES (?, CURRENT_TIMESTAMP)",
            (migration_name,)
        )
        conn.commit()


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

            # Check if migration uses temp tables (requires single execution context)
            uses_temp_tables = 'TEMP TABLE' in sql_statements.upper()

            if uses_temp_tables:
                # Execute as a single script to preserve temp table context
                cursor.executescript(sql_statements)
            else:
                # Split and execute statements individually
                for statement in sql_statements.split(';'):
                    statement = statement.strip()
                    if statement and not statement.startswith('--'):
                        cursor.execute(statement)

            conn.commit()

        # Record successful migration
        record_migration(migration_file.name)

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
