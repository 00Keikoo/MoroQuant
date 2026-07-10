"""Types for feature store."""

from dataclasses import dataclass, field
from typing import Dict, Any, List
from enum import Enum


class FeatureLifecycleState(Enum):
    """Feature dataset lifecycle state."""
    CREATED = "CREATED"
    COMPUTED = "COMPUTED"
    VALIDATED = "VALIDATED"
    FROZEN = "FROZEN"
    DEPRECATED = "DEPRECATED"
    ARCHIVED = "ARCHIVED"


@dataclass(frozen=True)
class FeatureDefinition:
    """Feature definition with mathematical specification."""
    feature_name: str
    description: str
    formula_ref: str
    created_at: str


@dataclass(frozen=True)
class FeatureVersion:
    """Parameterized version of a feature definition."""
    feature_version_id: str
    feature_name: str
    version: str
    parameters: Dict[str, Any]
    created_at: str


@dataclass(frozen=True)
class FeatureDatasetMetadata:
    """Metadata for computed feature dataset with lineage."""
    feature_dataset_id: str
    source_dataset_id: str
    feature_version_id: str
    fingerprint: str
    created_at: str
    lifecycle_state: FeatureLifecycleState
    storage_path: str
    is_frozen: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'feature_dataset_id': self.feature_dataset_id,
            'source_dataset_id': self.source_dataset_id,
            'feature_version_id': self.feature_version_id,
            'fingerprint': self.fingerprint,
            'created_at': self.created_at,
            'lifecycle_state': self.lifecycle_state.value,
            'storage_path': self.storage_path,
            'is_frozen': self.is_frozen
        }


@dataclass
class ValidationResult:
    """Result of feature validation."""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
