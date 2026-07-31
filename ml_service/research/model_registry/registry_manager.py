"""Registry Manager layer for Model Registry business logic."""

import copy
from typing import Dict, List, Optional, Any
from ml_service.research.model_registry.model_types import (
    Model,
    ModelVersion,
    ModelLifecycleState
)
from ml_service.research.model_registry.service import ModelRegistryService


class RegistryManager:
    """Registry Manager governing semantic search, path resolution, and lineage traversal."""

    def __init__(self, service: ModelRegistryService):
        if not isinstance(service, ModelRegistryService):
            raise TypeError("Expected ModelRegistryService instance")
        self.service = service
        # In-memory store for model lineage metadata mappings
        self._lineages: Dict[str, Dict[str, str]] = {}

    def register_lineage(self, model_version_id: str, lineage: Dict[str, str]) -> None:
        """Register upstream lineage mapping for a model version."""
        if not self.service.exists("", version_id=model_version_id):
            raise ValueError(f"Associated ModelVersion '{model_version_id}' does not exist")
        self._lineages[model_version_id] = copy.deepcopy(lineage)

    def resolve_model(self, model_id: str) -> Optional[Model]:
        """Resolve a model family by ID."""
        return self.service.get_model(model_id)

    def resolve_version(self, model_version_id: str) -> Optional[ModelVersion]:
        """Resolve a specific model version."""
        return self.service.get_version(model_version_id)

    def resolve_latest_version(self, model_id: str) -> Optional[ModelVersion]:
        """Resolve the latest semantic version of a model family."""
        versions = self.service.get_versions(model_id)
        if not versions:
            return None
        # get_versions returns sorted versions, so the last is the latest
        return versions[-1]

    def resolve_production_version(self, model_id: str) -> Optional[ModelVersion]:
        """Resolve the active production model version for a model family."""
        versions = self.service.get_versions(model_id)
        for v in versions:
            if v.lifecycle_state == ModelLifecycleState.PRODUCTION:
                return v
        return None

    def list_versions(self, model_id: str) -> List[ModelVersion]:
        """List all versions for a model family sorted deterministically."""
        return self.service.get_versions(model_id)

    def list_models(self) -> List[Model]:
        """List all model families."""
        return self.service.list_models()

    def resolve_lineage(self, model_version_id: str) -> Optional[Dict[str, str]]:
        """Traverse and retrieve upstream lineage mappings."""
        lineage = self._lineages.get(model_version_id)
        return copy.deepcopy(lineage) if lineage else None

    def resolve_storage_path(self, model_version_id: str) -> Optional[str]:
        """Resolve physical bundle directory path for a model version."""
        artifact = self.service.get_artifact(model_version_id)
        return artifact.bundle_path if artifact else None

    def next_version(self, model_id: str, bump_type: str) -> str:
        """Calculate the next semantic version string for a model family."""
        if not self.service.exists(model_id):
            raise ValueError(f"Model family '{model_id}' does not exist")
            
        latest = self.resolve_latest_version(model_id)
        if not latest:
            return "1.0.0"

        major, minor, patch = map(int, latest.version.split("."))
        if bump_type == "major":
            return f"{major + 1}.0.0"
        elif bump_type == "minor":
            return f"{major}.{minor + 1}.0"
        elif bump_type == "patch":
            return f"{major}.{minor}.{patch + 1}"
        else:
            raise ValueError(f"Invalid bump_type: {bump_type}")
