"""Database Recovery Framework - Sprint 2.3A Phase 1

Read-only inspection, diagnostic, and reporting capabilities for database recovery.
Implements ADR-023 v1.1 Database Recovery & Migration Reconciliation Framework.

Sprint 2.3A: Immutable schema models and raw structural differences only.
No decision-making concepts (severity, classification, recommendation, risk).
"""

from ml_service.migrations.recovery.models import (
    ColumnSchema,
    IndexSchema,
    TableSchema,
    CheckConstraint,
    ForeignKey,
    SchemaDifference,
    DifferenceType,
)
from ml_service.migrations.recovery.snapshot import SchemaSnapshot

__all__ = [
    "ColumnSchema",
    "IndexSchema",
    "TableSchema",
    "CheckConstraint",
    "ForeignKey",
    "SchemaDifference",
    "DifferenceType",
    "SchemaSnapshot",
]
