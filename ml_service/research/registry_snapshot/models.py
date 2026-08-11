"""
Registry Snapshot Models
Sprint 3.9D-5

Immutable representation of registry state and diffs.
"""

from dataclasses import dataclass
from ml_service.research.model_identity import ModelIdentity


@dataclass(frozen=True)
class RegistrySnapshot:
    snapshot_id: str
    created_at: str
    total_models: int
    models: tuple[ModelIdentity, ...]
    summary: dict


@dataclass(frozen=True)
class RegistryDiff:
    added_models: tuple[ModelIdentity, ...]
    removed_models: tuple[ModelIdentity, ...]
    modified_models: tuple[tuple[ModelIdentity, ModelIdentity], ...]
