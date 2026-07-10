"""Types for dataset manager."""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum


class LifecycleState(Enum):
    """Dataset lifecycle state."""
    DRAFT = "DRAFT"
    VALIDATED = "VALIDATED"
    FROZEN = "FROZEN"
    DEPRECATED = "DEPRECATED"
    ARCHIVED = "ARCHIVED"


@dataclass(frozen=True)
class TimeBounds:
    """Time bounds for dataset."""
    start_time: str
    end_time: str


@dataclass(frozen=True)
class DatasetSchema:
    """Dataset schema definition."""
    features: List[str]
    targets: List[str]
    data_types: Dict[str, str]


@dataclass(frozen=True)
class DatasetMetadata:
    """Dataset metadata with immutability guarantees."""
    dataset_id: str
    version: str
    fingerprint: str
    snapshot_id: str
    created_at: str
    time_bounds: TimeBounds
    schema: DatasetSchema
    lifecycle_state: LifecycleState
    storage_path: str
    preprocessing: Optional[Dict[str, Any]] = None
    is_frozen: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'dataset_id': self.dataset_id,
            'version': self.version,
            'fingerprint': self.fingerprint,
            'snapshot_id': self.snapshot_id,
            'created_at': self.created_at,
            'time_bounds': {
                'start_time': self.time_bounds.start_time,
                'end_time': self.time_bounds.end_time
            },
            'schema': {
                'features': self.schema.features,
                'targets': self.schema.targets,
                'data_types': self.schema.data_types
            },
            'lifecycle_state': self.lifecycle_state.value,
            'storage_path': self.storage_path,
            'preprocessing': self.preprocessing,
            'is_frozen': self.is_frozen
        }


@dataclass
class ValidationResult:
    """Result of dataset validation."""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
