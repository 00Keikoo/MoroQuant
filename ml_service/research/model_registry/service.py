"""Service layer for the Model Registry."""

import copy
from typing import List, Optional
from ml_service.research.model_registry.model_types import (
    Model,
    ModelVersion,
    ArtifactMetadata,
    EvaluationResult,
    PromotionRecord,
    ModelLifecycleState
)
from ml_service.research.model_registry.repository import (
    ModelRegistryRepository,
    ArtifactRepository,
    PromotionHistoryRepository
)


class ModelRegistryService:
    """Orchestrator service for Model Registry domain operations."""

    def __init__(
        self,
        registry_repository: Optional[ModelRegistryRepository] = None,
        artifact_repository: Optional[ArtifactRepository] = None,
        promotion_repository: Optional[PromotionHistoryRepository] = None
    ):
        self.registry_repo = registry_repository or ModelRegistryRepository()
        self.artifact_repo = artifact_repository or ArtifactRepository()
        self.promotion_repo = promotion_repository or PromotionHistoryRepository()

    # --- Registrations ---
    def register_model(self, model: Model) -> None:
        """Register a new Model family."""
        # Deep copy to maintain in-memory immutability
        model_copy = copy.deepcopy(model)
        model_copy.validate()
        self.registry_repo.save_model(model_copy)

    def register_version(self, version: ModelVersion) -> None:
        """Register a new ModelVersion."""
        if not self.registry_repo.model_exists(version.model_id):
            raise ValueError(f"Parent model '{version.model_id}' does not exist")
        version_copy = copy.deepcopy(version)
        version_copy.validate()
        self.registry_repo.save_version(version_copy)

    def register_artifact(self, artifact: ArtifactMetadata) -> None:
        """Register ArtifactMetadata bundle."""
        if not self.registry_repo.version_exists(artifact.model_version_id):
            raise ValueError(f"Associated ModelVersion '{artifact.model_version_id}' does not exist")
        artifact_copy = copy.deepcopy(artifact)
        artifact_copy.validate()
        self.artifact_repo.save_artifact(artifact_copy)

    def register_evaluation(self, evaluation: EvaluationResult) -> None:
        """Register or update an evaluation scorecard."""
        if not self.registry_repo.version_exists(evaluation.model_version_id):
            raise ValueError(f"Associated ModelVersion '{evaluation.model_version_id}' does not exist")
        evaluation_copy = copy.deepcopy(evaluation)
        evaluation_copy.validate()
        self.registry_repo.save_evaluation(evaluation_copy)

    def record_promotion(self, record: PromotionRecord) -> None:
        """Append promotion record events to promotion history."""
        version = self.registry_repo.get_version(record.model_version_id)
        if not version:
            raise ValueError(f"Associated ModelVersion '{record.model_version_id}' does not exist")
        
        record_copy = copy.deepcopy(record)
        record_copy.validate()
        
        # In-memory lifecycle state update on version
        self.registry_repo.update_version_state(record.model_version_id, record.new_state)
        self.promotion_repo.save_promotion_record(record_copy)

    # --- Retrievals ---
    def get_model(self, model_id: str) -> Optional[Model]:
        """Retrieve Model family by ID."""
        return self.registry_repo.get_model(model_id)

    def get_version(self, model_version_id: str) -> Optional[ModelVersion]:
        """Retrieve ModelVersion by version ID."""
        return self.registry_repo.get_version(model_version_id)

    def get_versions(self, model_id: str) -> List[ModelVersion]:
        """Retrieve all versions of a model sorted deterministically."""
        return self.registry_repo.list_versions_by_model(model_id)

    def get_evaluation(self, model_version_id: str) -> Optional[EvaluationResult]:
        """Retrieve evaluation scorecard by version ID."""
        return self.registry_repo.get_evaluation(model_version_id)

    def get_promotion_history(self, model_version_id: str) -> List[PromotionRecord]:
        """Retrieve append-only history of promotion events for a model version."""
        return self.promotion_repo.list_records_by_version(model_version_id)

    def get_artifact(self, model_version_id: str) -> Optional[ArtifactMetadata]:
        """Retrieve artifact metadata by version ID."""
        return self.artifact_repo.get_artifact(model_version_id)

    # --- Listings ---
    def list_models(self) -> List[Model]:
        """List all Model families sorted by model_id."""
        return self.registry_repo.list_models()

    def list_versions(self, state: Optional[ModelLifecycleState] = None) -> List[ModelVersion]:
        """List all ModelVersions, optionally filtered by state."""
        if state:
            return self.registry_repo.list_versions_by_state(state)
        # Combine all versions of all models sorted
        all_models = self.registry_repo.list_models()
        all_versions = []
        for model in all_models:
            all_versions.extend(self.registry_repo.list_versions_by_model(model.model_id))
        return sorted(all_versions)

    # --- Existential Check ---
    def exists(self, model_id: str, version_id: Optional[str] = None) -> bool:
        """Check presence of model or version."""
        if version_id:
            return self.registry_repo.version_exists(version_id)
        return self.registry_repo.model_exists(model_id)

    # --- Deletion ---
    def delete(self, model_id: str, version_id: Optional[str] = None) -> None:
        """Delete model or individual version, performing cascade cleanup."""
        if version_id:
            # Delete version evaluation and artifact if they exist
            if self.artifact_repo.artifact_exists(version_id):
                self.artifact_repo.delete_artifact(version_id)
            self.registry_repo.delete_version(version_id)
        else:
            # First delete all artifact bundles associated with model versions
            versions = self.registry_repo.list_versions_by_model(model_id)
            for v in versions:
                if self.artifact_repo.artifact_exists(v.model_version_id):
                    self.artifact_repo.delete_artifact(v.model_version_id)
            # Delete model cascading to versions
            self.registry_repo.delete_model(model_id)
