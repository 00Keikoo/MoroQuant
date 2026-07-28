"""Schema inspector for database schema recovery framework.

Implements read-only table, column, index, and foreign key discovery for schema snapshot capture.
"""

import time
import sqlite3
from typing import Tuple

from ml_service.data.database import Database
from ml_service.migrations.recovery.models import TableSchema, ColumnSchema, IndexSchema, ForeignKey
from ml_service.migrations.recovery.snapshot import SchemaSnapshot


class SchemaInspector:
    """Read-only database inspector to capture the physical schema state.

    This class is part of the ADR-023 v1.1 Database Recovery Framework.
    """

    def __init__(self, db: Database) -> None:
        """Initialize the SchemaInspector with a Database instance.

        Args:
            db: Database instance to inspect.
        """
        self.db = db

    def _return_tables(self, conn: sqlite3.Connection) -> Tuple[str, ...]:
        """Query sqlite_master to discover all user tables.

        Excludes internal SQLite tables (e.g. sqlite_sequence) and returns
        the table names sorted alphabetically.

        Args:
            conn: Read-only sqlite3 Connection.

        Returns:
            Sorted tuple of table names.
        """
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name != 'sqlite_sequence'"
        )
        rows = cursor.fetchall()
        tables = [row[0] for row in rows]
        return tuple(sorted(tables))

    def _capture_columns(self, conn: sqlite3.Connection, table_name: str) -> Tuple[Tuple[ColumnSchema, ...], Tuple[str, ...]]:
        """Retrieve column schemas and primary key columns for a table using PRAGMA table_info.

        Args:
            conn: Read-only sqlite3 Connection.
            table_name: Name of the table.

        Returns:
            A tuple containing:
              - Tuple of ColumnSchema objects.
              - Tuple of primary key column names in the correct order.
        """
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        rows = cursor.fetchall()
        columns = []
        pk_cols = []
        for row in rows:
            # row format: (cid, name, type, notnull, dflt_value, pk)
            is_pk = bool(row[5])
            columns.append(
                ColumnSchema(
                    name=row[1],
                    data_type=row[2],
                    nullable=row[3] == 0,
                    default_value=row[4],
                    is_primary_key=is_pk,
                )
            )
            if row[5] > 0:
                pk_cols.append((row[5], row[1]))

        pk_cols.sort()
        primary_key = tuple(col_name for _, col_name in pk_cols)
        return tuple(columns), primary_key

    def _capture_indexes(self, conn: sqlite3.Connection, table_name: str) -> Tuple[IndexSchema, ...]:
        """Retrieve index schemas for a table using PRAGMA index_list and index_info.

        Args:
            conn: Read-only sqlite3 Connection.
            table_name: Name of the table.

        Returns:
            Tuple of IndexSchema objects sorted alphabetically by index name.
        """
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA index_list({table_name})")
        index_rows = cursor.fetchall()

        index_schemas = []
        for row in index_rows:
            # row format: (seq, name, unique, origin, partial)
            idx_name = row[1]
            
            # Exclude SQLite internal auto-indexes
            if idx_name.startswith("sqlite_"):
                continue
                
            unique = bool(row[2])
            partial = bool(row[4])

            # Query columns for this index
            info_cursor = conn.cursor()
            info_cursor.execute(f"PRAGMA index_info({idx_name})")
            info_rows = info_cursor.fetchall()

            # Sort by seqno (row[0]) to preserve correct column ordering within the index
            sorted_info = sorted(info_rows, key=lambda x: x[0])
            columns = tuple(col_row[2] for col_row in sorted_info if col_row[2] is not None)

            index_schemas.append(
                IndexSchema(
                    name=idx_name,
                    table_name=table_name,
                    columns=columns,
                    unique=unique,
                    partial=partial,
                    where_clause=None,
                )
            )

        # Sort index schemas by name to preserve deterministic ordering
        index_schemas.sort(key=lambda x: x.name)
        return tuple(index_schemas)

    def _capture_foreign_keys(self, conn: sqlite3.Connection, table_name: str) -> Tuple[ForeignKey, ...]:
        """Retrieve foreign keys for a table using PRAGMA foreign_key_list.

        Args:
            conn: Read-only sqlite3 Connection.
            table_name: Name of the table.

        Returns:
            Tuple of ForeignKey objects sorted by local column name and referenced table.
        """
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA foreign_key_list({table_name})")
        fk_rows = cursor.fetchall()

        foreign_keys = []
        for row in fk_rows:
            # row format: (id, seq, table, from, to, on_update, on_delete, match)
            foreign_keys.append(
                ForeignKey(
                    column=row[3],
                    referenced_table=row[2],
                    referenced_column=row[4],
                    on_update=row[5],
                    on_delete=row[6],
                )
            )

        # Sort foreign keys to ensure deterministic ordering
        foreign_keys.sort(key=lambda x: (x.column, x.referenced_table, x.referenced_column))
        return tuple(foreign_keys)

    def capture_snapshot(self) -> SchemaSnapshot:
        """Capture the physical schema snapshot of the database.

        Populates table names, column definitions, index schemas, and foreign keys.

        Returns:
            SchemaSnapshot of the database.
        """
        db_uri = f"file:{self.db.db_path}?mode=ro"
        conn = sqlite3.connect(db_uri, uri=True)
        try:
            tables_list = self._return_tables(conn)
            tables_dict = {}
            all_indexes = {}
            for name in tables_list:
                cols, primary_key = self._capture_columns(conn, name)
                idxs = self._capture_indexes(conn, name)
                idx_names = tuple(idx.name for idx in idxs)
                fks = self._capture_foreign_keys(conn, name)

                tables_dict[name] = TableSchema(
                    name=name,
                    columns=cols,
                    primary_key=primary_key,
                    check_constraints=(),
                    foreign_keys=fks,
                    indexes=idx_names,
                )

                for idx in idxs:
                    all_indexes[idx.name] = idx

            return SchemaSnapshot(
                database_path=str(self.db.db_path),
                timestamp=int(time.time()),
                tables=tables_dict,
                indexes=all_indexes,
            )
        finally:
            conn.close()
