#!/usr/bin/env python3
"""Repair schema_migrations table by detecting already-applied migrations."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import sqlite3
from data.database import get_database
from utils.logger import get_logger

logger = get_logger()


MIGRATION_DETECTORS = {
    "014_add_signal_lifecycle.sql": lambda cursor: _check_column(cursor, "signals", "signal_status"),
    "015_dedup_signals_unique_index.sql": lambda cursor: _check_index(cursor, "idx_unique_signal"),
    "016_trading_mode_manager.sql": lambda cursor: _check_table(cursor, "trading_system_state"),
    "017_create_paper_account.sql": lambda cursor: _check_table(cursor, "paper_account"),
    "018_create_paper_positions.sql": lambda cursor: _check_table(cursor, "paper_positions"),
    "019_paper_equity_history.sql": lambda cursor: _check_table(cursor, "paper_equity_history"),
    "020_execution_metadata.sql": lambda cursor: _check_column(cursor, "paper_positions", "confidence"),
    "021_execution_intelligence.sql": lambda cursor: _check_column(cursor, "paper_positions", "mae"),
    "022_execution_policy_refinement.sql": lambda cursor: _check_column(cursor, "paper_positions", "execution_policy"),
}


def _check_table(cursor, table_name: str) -> bool:
    """Check if a table exists."""
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,)
    )
    return cursor.fetchone() is not None


def _check_column(cursor, table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    if not _check_table(cursor, table_name):
        return False
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    return column_name in columns


def _check_index(cursor, index_name: str) -> bool:
    """Check if an index exists."""
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name=?",
        (index_name,)
    )
    return cursor.fetchone() is not None


def get_recorded_migrations() -> set:
    """Get migrations already recorded in schema_migrations."""
    db = get_database()

    with db.get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT migration_name FROM schema_migrations")
            return {row[0] for row in cursor.fetchall()}
        except sqlite3.OperationalError:
            return set()


def detect_applied_migration(migration_name: str) -> bool:
    """
    Detect if a migration has been applied by checking database schema.

    Args:
        migration_name: Name of the migration file

    Returns:
        True if migration artifacts exist in schema
    """
    db = get_database()

    detector = MIGRATION_DETECTORS.get(migration_name)
    if not detector:
        return False

    with db.get_connection() as conn:
        cursor = conn.cursor()
        try:
            return detector(cursor)
        except Exception as e:
            logger.error(f"Detection failed for {migration_name}: {e}")
            return False


def record_migration(migration_name: str) -> bool:
    """
    Record a migration in schema_migrations.

    Args:
        migration_name: Name of the migration file

    Returns:
        True if successful
    """
    db = get_database()

    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO schema_migrations (migration_name, applied_at) VALUES (?, CURRENT_TIMESTAMP)",
                (migration_name,)
            )
            conn.commit()
        return True
    except Exception as e:
        logger.error(f"Failed to record {migration_name}: {e}")
        return False


def repair_schema_migrations() -> None:
    """
    Repair schema_migrations by detecting and recording already-applied migrations.

    Does NOT execute migrations - only updates tracking table.
    """
    logger.warning("Starting schema_migrations repair")

    recorded = get_recorded_migrations()
    logger.warning(f"Currently recorded: {len(recorded)} migrations")

    migrations_to_check = sorted(MIGRATION_DETECTORS.keys())

    repaired = []
    already_recorded = []
    not_applied = []

    for migration_name in migrations_to_check:
        if migration_name in recorded:
            already_recorded.append(migration_name)
            continue

        if detect_applied_migration(migration_name):
            if record_migration(migration_name):
                repaired.append(migration_name)
                logger.warning(f"✓ Recorded: {migration_name}")
            else:
                logger.error(f"✗ Failed to record: {migration_name}")
        else:
            not_applied.append(migration_name)

    print("\n=== Repair Summary ===")
    print(f"Already recorded: {len(already_recorded)}")
    print(f"Repaired: {len(repaired)}")
    print(f"Not applied: {len(not_applied)}")

    if repaired:
        print("\nRepaired migrations:")
        for m in repaired:
            print(f"  ✓ {m}")

    if not_applied:
        print("\nNot applied (will run on next migration):")
        for m in not_applied:
            print(f"  - {m}")


def main():
    try:
        repair_schema_migrations()
    except Exception as e:
        logger.error(f"Repair failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
