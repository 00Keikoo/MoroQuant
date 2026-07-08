"""Shared database connection management for repositories."""

import sqlite3
from pathlib import Path
from typing import Optional


def get_db_path(db_path: Optional[str] = None) -> Path:
    """Get the database path for repositories.

    Args:
        db_path: Optional override path for testing

    Returns:
        Path to the database file
    """
    if db_path is not None:
        return Path(db_path)

    return Path(__file__).parent.parent / "storage" / "database.db"


def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Get a database connection with Row factory.

    Args:
        db_path: Optional override path for testing

    Returns:
        Database connection configured with Row factory
    """
    path = get_db_path(db_path)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn
