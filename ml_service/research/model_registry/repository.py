"""In-memory repository layer for the Model Registry."""

import copy
from typing import Dict, List, Optional, Any
from ml_service.research.model_registry.model_types import (
    Model,
    ModelVersion,
    ArtifactMetadata,
    EvaluationResult,
    PromotionRecord,
    ModelLifecycleState
)


class ModelRegistryRepository:
    """Pure in-memory repository for Model, ModelVersion, and EvaluationResult aggregates."""

    def __init__(self):
        self._models: Dict[str, Model] = {}
        self._versions: Dict[str, ModelVersion] = {}
        self._evaluations: Dict[str, EvaluationResult] = {}

    # --- Model Operations ---
    def save_model(self, model: Model) -> None:
        """Save a model family, rejecting duplicates."""
        if not isinstance(model, Model):
            raise TypeError("Expected Model instance")
        if model.model_id in self._models:
            raise ValueError(f"Model with id '{model.model_id}' already exists")
        self._models[model.model_id] = copy.deepcopy(model)

    def get_model(self, model_id: str) -> Optional[Model]:
        """Retrieve a model family by ID."""
        model = self._models.get(model_id)
        return copy.deepcopy(model) if model else None

    def model_exists(self, model_id: str) -> bool:
        """Check if model exists."""
        return model_id in self._models

    def delete_model(self, model_id: str) -> None:
        """Delete a model family and all its associated versions/evaluations."""
        if model_id not in self._models:
            raise KeyError(f"Model '{model_id}' not found")
        
        # Cascade delete versions and evaluations
        associated_versions = [
            vid for vid, v in self._versions.items() if v.model_id == model_id
        ]
        for vid in associated_versions:
            self.delete_version(vid)
            
        del self._models[model_id]

    def list_models(self) -> List[Model]:
        """List all models sorted by model_id."""
        return sorted([copy.deepcopy(m) for m in self._models.values()])

    # --- ModelVersion Operations ---
    def save_version(self, version: ModelVersion) -> None:
        """Save a model version, rejecting duplicates and checking fingerprint uniqueness."""
        if not isinstance(version, ModelVersion):
            raise TypeError("Expected ModelVersion instance")
        
        if version.model_version_id in self._versions:
            raise ValueError(f"ModelVersion with id '{version.model_version_id}' already exists")
        
        # Validate composite fingerprint uniqueness
        for existing in self._versions.values():
            if existing.composite_fingerprint.value == version.composite_fingerprint.value:
                raise ValueError(
                    f"ModelVersion with composite fingerprint '{version.composite_fingerprint.value}' already exists"
                )
                
        self._versions[version.model_version_id] = copy.deepcopy(version)

    def get_version(self, model_version_id: str) -> Optional[ModelVersion]:
        """Retrieve a model version."""
        version = self._versions.get(model_version_id)
        return copy.deepcopy(version) if version else None

    def version_exists(self, model_version_id: str) -> bool:
        """Check if version exists."""
        return model_version_id in self._versions

    def update_version_state(self, model_version_id: str, new_state: ModelLifecycleState) -> None:
        """Update lifecycle state of an existing version."""
        if model_version_id not in self._versions:
            raise KeyError(f"ModelVersion '{model_version_id}' not found")
        
        old_version = self._versions[model_version_id]
        # Since ModelVersion is frozen, reconstruct it with the new state
        updated = ModelVersion(
            model_version_id=old_version.model_version_id,
            model_id=old_version.model_id,
            version=old_version.version,
            lifecycle_state=new_state,
            composite_fingerprint=old_version.composite_fingerprint,
            created_at=old_version.created_at
        )
        self._versions[model_version_id] = updated

    def delete_version(self, model_version_id: str) -> None:
        """Delete version and its evaluation."""
        if model_version_id not in self._versions:
            raise KeyError(f"ModelVersion '{model_version_id}' not found")
        
        if model_version_id in self._evaluations:
            del self._evaluations[model_version_id]
            
        del self._versions[model_version_id]

    def list_versions_by_model(self, model_id: str) -> List[ModelVersion]:
        """List versions for a specific model, sorted deterministically."""
        versions = [
            copy.deepcopy(v) for v in self._versions.values() if v.model_id == model_id
        ]
        return sorted(versions)

    def list_versions_by_state(self, state: ModelLifecycleState) -> List[ModelVersion]:
        """List all versions in a specific lifecycle state."""
        versions = [
            copy.deepcopy(v) for v in self._versions.values() if v.lifecycle_state == state
        ]
        return sorted(versions)

    # --- EvaluationResult Operations ---
    def save_evaluation(self, evaluation: EvaluationResult) -> None:
        """Save/overwrite evaluation result for a version."""
        if not isinstance(evaluation, EvaluationResult):
            raise TypeError("Expected EvaluationResult instance")
        # Ensure model version exists
        if evaluation.model_version_id not in self._versions:
            raise ValueError(f"Associated ModelVersion '{evaluation.model_version_id}' does not exist")
            
        self._evaluations[evaluation.model_version_id] = copy.deepcopy(evaluation)

    def get_evaluation(self, model_version_id: str) -> Optional[EvaluationResult]:
        """Retrieve evaluation result by model version ID."""
        evaluation = self._evaluations.get(model_version_id)
        return copy.deepcopy(evaluation) if evaluation else None

    def evaluation_exists(self, model_version_id: str) -> bool:
        """Check if evaluation exists."""
        return model_version_id in self._evaluations


class ArtifactRepository:
    """Pure in-memory repository for ArtifactMetadata bundles."""

    def __init__(self):
        self._artifacts: Dict[str, ArtifactMetadata] = {}

    def save_artifact(self, artifact: ArtifactMetadata) -> None:
        """Save artifact metadata, rejecting duplicates."""
        if not isinstance(artifact, ArtifactMetadata):
            raise TypeError("Expected ArtifactMetadata instance")
        if artifact.model_version_id in self._artifacts:
            raise ValueError(f"Artifact for version '{artifact.model_version_id}' already exists")
            
        self._artifacts[artifact.model_version_id] = copy.deepcopy(artifact)

    def get_artifact(self, model_version_id: str) -> Optional[ArtifactMetadata]:
        """Retrieve artifact metadata by model version ID."""
        artifact = self._artifacts.get(model_version_id)
        return copy.deepcopy(artifact) if artifact else None

    def artifact_exists(self, model_version_id: str) -> bool:
        """Check if artifact metadata exists."""
        return model_version_id in self._artifacts

    def delete_artifact(self, model_version_id: str) -> None:
        """Delete artifact metadata."""
        if model_version_id not in self._artifacts:
            raise KeyError(f"Artifact for version '{model_version_id}' not found")
        del self._artifacts[model_version_id]


class PromotionHistoryRepository:
    """Pure in-memory repository for append-only PromotionRecord events."""

    def __init__(self):
        self._records: Dict[str, PromotionRecord] = {}

    def save_promotion_record(self, record: PromotionRecord) -> None:
        """Save a promotion history record. Cannot overwrite or update."""
        if not isinstance(record, PromotionRecord):
            raise TypeError("Expected PromotionRecord instance")
        
        # Verify promotion_id uniqueness (Event Sourcing append-only invariant)
        if record.promotion_id in self._records:
            raise ValueError(f"PromotionRecord with promotion_id '{record.promotion_id}' already exists")
            
        self._records[record.promotion_id] = copy.deepcopy(record)

    def get_promotion_record(self, promotion_id: str) -> Optional[PromotionRecord]:
        """Retrieve promotion record by ID."""
        record = self._records.get(promotion_id)
        return copy.deepcopy(record) if record else None

    def list_records_by_version(self, model_version_id: str) -> List[PromotionRecord]:
        """List promotion history for a model version sorted chronologically."""
        records = [
            copy.deepcopy(r) for r in self._records.values() if r.model_version_id == model_version_id
        ]
        return sorted(records)
