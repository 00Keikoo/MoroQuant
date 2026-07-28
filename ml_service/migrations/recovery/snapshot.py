"""Immutable SchemaSnapshot representing complete database structure at a point in time.

Implements ADR-023 v1.1 read-only schema capture.
"""

from dataclasses import dataclass, field
from typing import Dict

from ml_service.migrations.recovery.models import TableSchema, IndexSchema


@dataclass(frozen=True)
class SchemaSnapshot:
    """Immutable representation of complete database schema at a specific timestamp.

    Properties are read-only post-initialization to prevent accidental mutation
    during validation passes.
    """
    database_path: str
    timestamp: int
    tables: Dict[str, TableSchema] = field(default_factory=dict)
    indexes: Dict[str, IndexSchema] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Serialize to dictionary for deterministic JSON output.

        Keys are sorted to ensure git-diff friendly output.
        """
        return {
            "database_path": self.database_path,
            "timestamp": self.timestamp,
            "tables": {
                name: table.to_dict()
                for name, table in sorted(self.tables.items())
            },
            "indexes": {
                name: index.to_dict()
                for name, index in sorted(self.indexes.items())
            },
        }
