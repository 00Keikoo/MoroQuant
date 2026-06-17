#!/usr/bin/env python3
"""Execute database migrations for MoroQuant trading system."""

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ml_service.data.database import get_database
from ml_service.utils.logger import get_logger

logger = get_logger()


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

            # Split and execute statements (SQLite doesn't support executescript with foreign keys)
            for statement in sql_statements.split(';'):
                statement = statement.strip()
                if statement and not statement.startswith('--'):
                    cursor.execute(statement)

            conn.commit()

        logger.info(f"✓ Migration applied: {migration_file.name}")
        return True

    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            logger.warning(f"Migration already applied: {migration_file.name}")
            return True
        else:
            logger.error(f"✗ Migration failed: {e}")
            return False
    except Exception as e:
        logger.error(f"✗ Migration failed: {e}")
        return False


def main():
    migrations_dir = Path(__file__).parent

    migration_files = sorted(migrations_dir.glob("*.sql"))

    if not migration_files:
        logger.warning("No migration files found")
        return

    logger.info(f"Found {len(migration_files)} migration(s)")

    for migration_file in migration_files:
        success = apply_migration(migration_file)
        if not success:
            logger.error(f"Migration failed, stopping at: {migration_file.name}")
            sys.exit(1)

    logger.info("✓ All migrations completed successfully")


if __name__ == "__main__":
    main()
