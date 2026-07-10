"""Service layer for model registry."""

import hashlib
import json
import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from ml_service.research.model_registry.repository import ModelRegistryRepository
from ml_service.research.model_registry.model_types import (
    ModelVersionMetadata,
    ModelLineage,
    ModelEvaluation,
    ModelLifecycleState,
    ValidationResult,
    RegistrationRequest
)


class ModelRegistryService:
    """Model promotion, versioning, and activation flow per ADR-013."""

    def __init__(self, repository: Optional[ModelRegistryRepository] = None):
        self.repository = repository or ModelRegistryRepository()

    def _compute_fingerprint(self, storage_path: str, hyperparameters: Dict[str, Any]) -> str:
        """Compute SHA256 fingerprint per contract specification."""
        model_path = Path(storage_path) / "model.bin"

        if not model_path.exists():
            raise FileNotFoundError(f"Model binary not found: {model_path}")

        with open(model_path, 'rb') as f:
            model_hash = hashlib.sha256(f.read()).hexdigest()

        params_str = json.dumps(hyperparameters, sort_keys=True)
        params_hash = hashlib.sha256(params_str.encode()).hexdigest()

        combined = model_hash + params_hash
        fingerprint = hashlib.sha256(combined.encode()).hexdigest()

        return fingerprint

    def _generate_version(self, model_id: str, version_bump: str) -> str:
        """Generate next semantic version."""
        versions = self.repository.list_versions_by_model(model_id)

        if not versions:
            return "1.0.0"

        latest = versions[0].version
        major, minor, patch = map(int, latest.split('.'))

        if version_bump == "major":
            return f"{major + 1}.0.0"
        elif version_bump == "minor":
            return f"{major}.{minor + 1}.0"
        elif version_bump == "patch":
            return f"{major}.{minor}.{patch + 1}"
        else:
            raise ValueError(f"Invalid version_bump: {version_bump}")

    def _validate_lineage(self, lineage: ModelLineage) -> ValidationResult:
        """Validate lineage references exist."""
        errors = []

        if not lineage.snapshot_id:
            errors.append("snapshot_id is required")
        if not lineage.dataset_id:
            errors.append("dataset_id is required")
        if not lineage.feature_dataset_id:
            errors.append("feature_dataset_id is required")
        if not lineage.experiment_id:
            errors.append("experiment_id is required")
        if not lineage.best_config_id:
            errors.append("best_config_id is required")

        return ValidationResult(is_valid=len(errors) == 0, errors=errors)

    def _validate_transition(
        self,
        current_state: ModelLifecycleState,
        new_state: ModelLifecycleState
    ) -> ValidationResult:
        """Validate lifecycle state transition per ADR-013."""
        valid_transitions = {
            ModelLifecycleState.CANDIDATE: [ModelLifecycleState.VALIDATED, ModelLifecycleState.ARCHIVED],
            ModelLifecycleState.VALIDATED: [ModelLifecycleState.PRODUCTION, ModelLifecycleState.ARCHIVED],
            ModelLifecycleState.PRODUCTION: [ModelLifecycleState.ARCHIVED],
            ModelLifecycleState.ARCHIVED: []
        }

        if new_state not in valid_transitions.get(current_state, []):
            return ValidationResult(
                is_valid=False,
                errors=[f"Invalid transition: {current_state.value} -> {new_state.value}"]
            )

        return ValidationResult(is_valid=True)

    def register_candidate(self, request: RegistrationRequest) -> ModelVersionMetadata:
        """Register new model candidate."""
        if not self.repository.model_exists(request.model_id):
            self.repository.save_model(
                model_id=request.model_id,
                name=request.model_id,
                description=f"Model for {request.symbol} {request.timeframe} using {request.algorithm}",
                created_at=datetime.utcnow().isoformat()
            )

        version = self._generate_version(request.model_id, request.version_bump)
        model_version_id = f"{request.model_id}_v{version}"

        fingerprint = self._compute_fingerprint(request.storage_path, request.hyperparameters)

        if self.repository.fingerprint_exists(fingerprint):
            raise ValueError(f"Model with fingerprint {fingerprint} already exists")

        lineage = ModelLineage(
            snapshot_id=request.lineage['snapshot_id'],
            dataset_id=request.lineage['dataset_id'],
            feature_dataset_id=request.lineage['feature_dataset_id'],
            experiment_id=request.lineage['experiment_id'],
            best_config_id=request.lineage['best_config_id']
        )

        validation = self._validate_lineage(lineage)
        if not validation.is_valid:
            raise ValueError(f"Lineage validation failed: {', '.join(validation.errors)}")

        metadata = ModelVersionMetadata(
            model_version_id=model_version_id,
            model_id=request.model_id,
            version=version,
            lifecycle_state=ModelLifecycleState.CANDIDATE,
            fingerprint=fingerprint,
            storage_path=request.storage_path,
            hyperparameters=request.hyperparameters,
            lineage=lineage,
            created_at=datetime.utcnow().isoformat(),
            symbol=request.symbol,
            timeframe=request.timeframe,
            algorithm=request.algorithm,
            git_commit=request.git_commit,
            git_tag=request.git_tag
        )

        self.repository.save_version(metadata)
        self.repository.save_lineage(model_version_id, lineage)

        return metadata

    def evaluate_and_validate(
        self,
        model_version_id: str,
        evaluation: ModelEvaluation,
        reviewer: str
    ) -> bool:
        """Validate model and promote to VALIDATED state."""
        metadata = self.repository.get_version(model_version_id)
        if not metadata:
            raise ValueError(f"Model version not found: {model_version_id}")

        validation = self._validate_transition(
            metadata.lifecycle_state,
            ModelLifecycleState.VALIDATED
        )
        if not validation.is_valid:
            raise ValueError(f"Cannot validate: {', '.join(validation.errors)}")

        quality_check = self._check_quality_gate(evaluation)
        if not quality_check.is_valid:
            raise ValueError(f"Quality gate failed: {', '.join(quality_check.errors)}")

        evaluation_approved = ModelEvaluation(
            sharpe_ratio=evaluation.sharpe_ratio,
            max_drawdown=evaluation.max_drawdown,
            ece=evaluation.ece,
            brier_score=evaluation.brier_score,
            win_rate=evaluation.win_rate,
            profit_factor=evaluation.profit_factor,
            sortino_ratio=evaluation.sortino_ratio,
            trade_count=evaluation.trade_count,
            is_approved=True,
            approved_by=reviewer,
            approved_at=datetime.utcnow().isoformat()
        )

        self.repository.save_evaluation(model_version_id, evaluation_approved)
        self.repository.update_lifecycle_state(
            model_version_id,
            ModelLifecycleState.VALIDATED,
            promoted_by=reviewer,
            promoted_at=datetime.utcnow().isoformat()
        )

        self._freeze_artifacts(metadata.storage_path)
        self.repository.set_frozen(model_version_id, True)

        return True

    def _check_quality_gate(self, evaluation: ModelEvaluation) -> ValidationResult:
        """Check quality gate per ADR-013 promotion policy."""
        errors = []

        if evaluation.sharpe_ratio < 1.5:
            errors.append(f"Sharpe ratio {evaluation.sharpe_ratio:.2f} < 1.5")

        if evaluation.max_drawdown < -0.15:
            errors.append(f"Max drawdown {evaluation.max_drawdown:.2%} worse than -15%")

        if evaluation.ece >= 0.05:
            errors.append(f"ECE {evaluation.ece:.4f} >= 0.05")

        if evaluation.brier_score >= 0.22:
            errors.append(f"Brier score {evaluation.brier_score:.4f} >= 0.22")

        if evaluation.trade_count < 100:
            errors.append(f"Trade count {evaluation.trade_count} < 100")

        return ValidationResult(is_valid=len(errors) == 0, errors=errors)

    def _freeze_artifacts(self, storage_path: str) -> None:
        """Apply write lock to model artifacts per ADR-013."""
        path = Path(storage_path)
        if not path.exists():
            return

        for file in path.glob("*"):
            if file.is_file():
                os.chmod(file, 0o444)

    def promote_to_production(
        self,
        model_version_id: str,
        promoter: str
    ) -> None:
        """Promote model to PRODUCTION with automatic demotion of existing production model."""
        metadata = self.repository.get_version(model_version_id)
        if not metadata:
            raise ValueError(f"Model version not found: {model_version_id}")

        validation = self._validate_transition(
            metadata.lifecycle_state,
            ModelLifecycleState.PRODUCTION
        )
        if not validation.is_valid:
            raise ValueError(f"Cannot promote to production: {', '.join(validation.errors)}")

        current_production = self.repository.get_production_model(
            metadata.symbol,
            metadata.timeframe,
            metadata.algorithm
        )

        if current_production and current_production.model_version_id != model_version_id:
            self.repository.update_lifecycle_state(
                current_production.model_version_id,
                ModelLifecycleState.ARCHIVED,
                promoted_by=promoter,
                promoted_at=datetime.utcnow().isoformat()
            )

        self.repository.update_lifecycle_state(
            model_version_id,
            ModelLifecycleState.PRODUCTION,
            promoted_by=promoter,
            promoted_at=datetime.utcnow().isoformat()
        )

    def archive_model(self, model_version_id: str, archiver: str) -> None:
        """Archive model version."""
        metadata = self.repository.get_version(model_version_id)
        if not metadata:
            raise ValueError(f"Model version not found: {model_version_id}")

        validation = self._validate_transition(
            metadata.lifecycle_state,
            ModelLifecycleState.ARCHIVED
        )
        if not validation.is_valid:
            raise ValueError(f"Cannot archive: {', '.join(validation.errors)}")

        self.repository.update_lifecycle_state(
            model_version_id,
            ModelLifecycleState.ARCHIVED,
            promoted_by=archiver,
            promoted_at=datetime.utcnow().isoformat()
        )

    def get_model(self, model_version_id: str) -> Optional[ModelVersionMetadata]:
        """Get model version metadata."""
        return self.repository.get_version(model_version_id)

    def list_models_by_state(self, state: ModelLifecycleState) -> List[ModelVersionMetadata]:
        """List all models in a specific state."""
        return self.repository.list_by_state(state)

    def get_production_model(
        self,
        symbol: str,
        timeframe: str,
        algorithm: str
    ) -> Optional[ModelVersionMetadata]:
        """Get current production model for symbol/timeframe/algorithm."""
        return self.repository.get_production_model(symbol, timeframe, algorithm)

    def get_lineage_chain(self, model_version_id: str) -> Dict[str, Any]:
        """Get complete lineage chain."""
        return self.repository.get_lineage_chain(model_version_id)

    def find_models_by_dataset(self, dataset_id: str) -> List[str]:
        """Find all models using a specific dataset."""
        return self.repository.find_models_by_dataset(dataset_id)

    def find_models_by_feature_dataset(self, feature_dataset_id: str) -> List[str]:
        """Find all models using a specific feature dataset."""
        return self.repository.find_models_by_feature_dataset(feature_dataset_id)

    def find_models_by_experiment(self, experiment_id: str) -> List[str]:
        """Find all models from a specific experiment."""
        return self.repository.find_models_by_experiment(experiment_id)
