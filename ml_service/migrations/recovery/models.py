"""Immutable data models for database schema recovery framework.

Implements ADR-023 v1.1 classification and difference models.
All structures are frozen dataclasses to enforce immutability.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any


class DifferenceType(str, Enum):
    """Types of schema differences that can be detected."""
    MISSING_TABLE = "MISSING_TABLE"
    EXTRA_TABLE = "EXTRA_TABLE"
    MISSING_COLUMN = "MISSING_COLUMN"
    EXTRA_COLUMN = "EXTRA_COLUMN"
    COLUMN_TYPE_MISMATCH = "COLUMN_TYPE_MISMATCH"
    CONSTRAINT_MISMATCH = "CONSTRAINT_MISMATCH"
    MISSING_INDEX = "MISSING_INDEX"
    EXTRA_INDEX = "EXTRA_INDEX"
    INDEX_DEFINITION_MISMATCH = "INDEX_DEFINITION_MISMATCH"
    DEFAULT_VALUE_MISMATCH = "DEFAULT_VALUE_MISMATCH"
    NULLABILITY_MISMATCH = "NULLABILITY_MISMATCH"


class RecoveryClassification(str, Enum):
    """ADR-023 recovery classification taxonomy."""
    METADATA_DRIFT = "METADATA_DRIFT"
    SCHEMA_DRIFT = "SCHEMA_DRIFT"
    REPLAY_CONFLICT = "REPLAY_CONFLICT"
    SUPERSEDED_MIGRATION = "SUPERSEDED_MIGRATION"
    MISSING_MIGRATION = "MISSING_MIGRATION"
    DESTRUCTIVE_MIGRATION = "DESTRUCTIVE_MIGRATION"
    MANUAL_DATABASE_MODIFICATION = "MANUAL_DATABASE_MODIFICATION"
    UNKNOWN_STATE = "UNKNOWN_STATE"


class RecoveryRisk(str, Enum):
    """Risk levels for recovery decisions."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RecoveryRecommendation(str, Enum):
    """Recommended actions for recovery."""
    SAFE_SKIP = "SAFE_SKIP"
    FORCE_RECORD = "FORCE_RECORD"
    FORWARD_MIGRATION = "FORWARD_MIGRATION"
    MANUAL_PATCH = "MANUAL_PATCH"
    HALT = "HALT"


@dataclass(frozen=True)
class CheckConstraint:
    """Represents a CHECK constraint on a table."""
    name: str
    expression: str


@dataclass(frozen=True)
class ForeignKey:
    """Represents a foreign key constraint."""
    column: str
    referenced_table: str
    referenced_column: str
    on_delete: Optional[str] = None
    on_update: Optional[str] = None


@dataclass(frozen=True)
class ColumnSchema:
    """Immutable representation of a database column."""
    name: str
    data_type: str
    nullable: bool
    default_value: Optional[str] = None
    is_primary_key: bool = False

    def to_dict(self) -> dict:
        """Serialize to dictionary for JSON output."""
        return {
            "name": self.name,
            "data_type": self.data_type,
            "nullable": self.nullable,
            "default_value": self.default_value,
            "is_primary_key": self.is_primary_key,
        }


@dataclass(frozen=True)
class IndexSchema:
    """Immutable representation of a database index."""
    name: str
    table_name: str
    columns: tuple[str, ...]
    unique: bool
    partial: bool = False
    where_clause: Optional[str] = None

    def to_dict(self) -> dict:
        """Serialize to dictionary for JSON output."""
        return {
            "name": self.name,
            "table_name": self.table_name,
            "columns": list(self.columns),
            "unique": self.unique,
            "partial": self.partial,
            "where_clause": self.where_clause,
        }


@dataclass(frozen=True)
class TableSchema:
    """Immutable representation of a database table."""
    name: str
    columns: tuple[ColumnSchema, ...]
    primary_key: tuple[str, ...] = field(default_factory=tuple)
    check_constraints: tuple[CheckConstraint, ...] = field(default_factory=tuple)
    foreign_keys: tuple[ForeignKey, ...] = field(default_factory=tuple)
    indexes: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict:
        """Serialize to dictionary for JSON output."""
        return {
            "name": self.name,
            "columns": [col.to_dict() for col in self.columns],
            "primary_key": list(self.primary_key),
            "check_constraints": [
                {"name": cc.name, "expression": cc.expression}
                for cc in self.check_constraints
            ],
            "foreign_keys": [
                {
                    "column": fk.column,
                    "referenced_table": fk.referenced_table,
                    "referenced_column": fk.referenced_column,
                    "on_delete": fk.on_delete,
                    "on_update": fk.on_update,
                }
                for fk in self.foreign_keys
            ],
            "indexes": list(self.indexes),
        }


@dataclass(frozen=True)
class SchemaDifference:
    """Represents a detected structural difference between physical and target schema.

    Sprint 2.3A Phase 1: Raw structural differences only.
    No severity, classification, recommendation, or risk - those belong to Sprint 2.3B.
    """
    difference_type: DifferenceType
    target_migration: Optional[str] = None
    table_name: Optional[str] = None
    column_name: Optional[str] = None
    index_name: Optional[str] = None
    details: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Serialize to dictionary for JSON output."""
        return {
            "difference_type": self.difference_type.value,
            "target_migration": self.target_migration,
            "table_name": self.table_name,
            "column_name": self.column_name,
            "index_name": self.index_name,
            "details": self.details,
        }


@dataclass(frozen=True)
class DecisionContext:
    """Immutable context containing metadata ledger and migration file information.

    Sprint 2.3B: Eliminates database calls by encapsulating all static inputs
    required to determine recovery decisions.
    """
    applied_migration_names: tuple[str, ...]
    available_migration_files: tuple[str, ...]
    migration_checksums: Dict[str, str]


@dataclass(frozen=True)
class RecoveryDecision:
    """Immutable output representing a recovery decision for a single difference.

    Sprint 2.3B: Maps SchemaDifference to actionable recovery classification,
    risk level, and recommended action according to ADR-023.
    """
    difference: SchemaDifference
    classification: RecoveryClassification
    risk: RecoveryRisk
    recommendation: RecoveryRecommendation
    rationale: str
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize recovery decision to deterministic dictionary."""
        return {
            "difference": self.difference.to_dict(),
            "classification": self.classification.value,
            "risk": self.risk.value,
            "recommended_action": self.recommendation.value,
            "rationale": self.rationale,
            "details": self.details
        }
