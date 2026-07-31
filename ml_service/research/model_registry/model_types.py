"""Domain models for the Model Registry."""

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
import re
import json
import hashlib


class ModelLifecycleState(Enum):
    """Model lifecycle states per Sprint 3.6 specifications."""
    DRAFT = "DRAFT"
    CANDIDATE = "CANDIDATE"
    VALIDATED = "VALIDATED"
    PRODUCTION = "PRODUCTION"
    ARCHIVED = "ARCHIVED"


class PromotionState(Enum):
    """Promotion state enum mapping model status."""
    DRAFT = "DRAFT"
    CANDIDATE = "CANDIDATE"
    VALIDATED = "VALIDATED"
    PRODUCTION = "PRODUCTION"
    ARCHIVED = "ARCHIVED"


class ArtifactType(Enum):
    """Standardized artifact types within a model bundle."""
    BINARY = "BINARY"
    METADATA = "METADATA"
    MANIFEST = "MANIFEST"
    EXPLAINABILITY = "EXPLAINABILITY"
    METRICS = "METRICS"
    LOG = "LOG"
    ENVIRONMENT = "ENVIRONMENT"


@dataclass(frozen=True)
class CompositeFingerprint:
    """Valided Composite Checksum string value object."""
    value: str

    def __post_init__(self):
        if not isinstance(self.value, str):
            raise TypeError("Composite fingerprint value must be a string")
        if not re.match(r"^[0-9a-fA-F]{64}$", self.value):
            raise ValueError(f"Invalid composite fingerprint format: {self.value}")

    @classmethod
    def calculate(
        cls,
        binary_hash: str,
        hyperparameters: Dict[str, Any],
        dataset_fingerprint: str,
        feature_fingerprint: str,
        git_commit: str,
        environment_info: Dict[str, Any],
        algorithm_version: str
    ) -> "CompositeFingerprint":
        """Deterministic calculation of composite fingerprint using SHA-256."""
        hparams_str = json.dumps(hyperparameters, sort_keys=True)
        env_str = json.dumps(environment_info, sort_keys=True)
        
        raw_payload = (
            f"{binary_hash}:{hparams_str}:{dataset_fingerprint}:"
            f"{feature_fingerprint}:{git_commit}:{env_str}:{algorithm_version}"
        )
        
        fingerprint = hashlib.sha256(raw_payload.encode("utf-8")).hexdigest()
        return cls(value=fingerprint)


@dataclass(frozen=True)
class Model:
    """Immutable Model family aggregate root."""
    model_id: str
    name: str
    description: str
    created_at: datetime

    def __post_init__(self):
        if not self.model_id:
            raise ValueError("model_id cannot be empty")
        if not self.name:
            raise ValueError("name cannot be empty")
        if not isinstance(self.created_at, datetime):
            raise TypeError("created_at must be a datetime instance")

    def validate(self) -> None:
        """Validate invariant rules."""
        if not re.match(r"^[a-zA-Z0-9_\-]+$", self.model_id):
            raise ValueError("model_id must be alphanumeric with dashes or underscores")

    def serialize(self) -> Dict[str, Any]:
        """Canonical dictionary serialization."""
        return {
            "model_id": self.model_id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at.isoformat()
        }

    def __lt__(self, other: "Model") -> bool:
        if not isinstance(other, Model):
            return NotImplemented
        return self.model_id < other.model_id


@dataclass(frozen=True)
class ModelVersion:
    """Immutable ModelVersion definition."""
    model_version_id: str
    model_id: str
    version: str
    lifecycle_state: ModelLifecycleState
    composite_fingerprint: CompositeFingerprint
    created_at: datetime

    def __post_init__(self):
        if not self.model_version_id:
            raise ValueError("model_version_id cannot be empty")
        if not self.model_id:
            raise ValueError("model_id cannot be empty")
        if not self.version:
            raise ValueError("version cannot be empty")
        if not isinstance(self.lifecycle_state, ModelLifecycleState):
            raise TypeError("lifecycle_state must be a ModelLifecycleState instance")
        if not isinstance(self.composite_fingerprint, CompositeFingerprint):
            raise TypeError("composite_fingerprint must be a CompositeFingerprint instance")
        if not isinstance(self.created_at, datetime):
            raise TypeError("created_at must be a datetime instance")

    def validate(self) -> None:
        """Validate structural semantics and versioning format."""
        if not re.match(r"^\d+\.\d+\.\d+$", self.version):
            raise ValueError(f"Invalid semantic version format: {self.version}")
        expected_id = f"{self.model_id}_v{self.version}"
        if self.model_version_id != expected_id:
            raise ValueError(f"model_version_id '{self.model_version_id}' does not match expected pattern '{expected_id}'")

    def serialize(self) -> Dict[str, Any]:
        """Canonical serialization."""
        return {
            "model_version_id": self.model_version_id,
            "model_id": self.model_id,
            "version": self.version,
            "lifecycle_state": self.lifecycle_state.value,
            "composite_fingerprint": self.composite_fingerprint.value,
            "created_at": self.created_at.isoformat()
        }

    def _parse_version(self) -> List[int]:
        return [int(x) for x in self.version.split(".")]

    def __lt__(self, other: "ModelVersion") -> bool:
        if not isinstance(other, ModelVersion):
            return NotImplemented
        if self.model_id != other.model_id:
            return self.model_id < other.model_id
        return self._parse_version() < other._parse_version()


@dataclass(frozen=True)
class ArtifactMetadata:
    """Immutable metadata representation for the Artifact Bundle."""
    model_version_id: str
    bundle_path: str
    manifest_checksum: str
    size_bytes: int
    permissions: str
    is_frozen: bool = False

    def __post_init__(self):
        if not self.model_version_id:
            raise ValueError("model_version_id cannot be empty")
        if not self.bundle_path:
            raise ValueError("bundle_path cannot be empty")
        if not self.manifest_checksum:
            raise ValueError("manifest_checksum cannot be empty")
        if self.size_bytes < 0:
            raise ValueError("size_bytes cannot be negative")

    def validate(self) -> None:
        """Validate files structure invariants."""
        if not re.match(r"^[0-9a-fA-F]{64}$", self.manifest_checksum):
            raise ValueError("manifest_checksum must be a valid 64-character SHA-256 hash")
        if not re.match(r"^[0-7]{3,4}$", self.permissions):
            raise ValueError("permissions must be a valid octal notation string (e.g. '444')")

    def serialize(self) -> Dict[str, Any]:
        """Canonical serialization."""
        return {
            "model_version_id": self.model_version_id,
            "bundle_path": self.bundle_path,
            "manifest_checksum": self.manifest_checksum,
            "size_bytes": self.size_bytes,
            "permissions": self.permissions,
            "is_frozen": self.is_frozen
        }

    def __lt__(self, other: "ArtifactMetadata") -> bool:
        if not isinstance(other, ArtifactMetadata):
            return NotImplemented
        return self.model_version_id < other.model_version_id


@dataclass(frozen=True)
class EvaluationResult:
    """Immutable evaluation metrics scorecard entity."""
    model_version_id: str
    sharpe_ratio: float
    max_drawdown: float
    ece: float
    brier_score: float
    win_rate: float
    profit_factor: float
    sortino_ratio: float
    trade_count: int
    is_approved: bool
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None

    def __post_init__(self):
        if not self.model_version_id:
            raise ValueError("model_version_id cannot be empty")
        if self.trade_count < 0:
            raise ValueError("trade_count cannot be negative")
        if not (0.0 <= self.win_rate <= 1.0):
            raise ValueError("win_rate must be between 0.0 and 1.0")
        if self.profit_factor < 0:
            raise ValueError("profit_factor cannot be negative")
        if self.is_approved and not self.approved_by:
            raise ValueError("approved_by is required when is_approved is True")

    def validate(self) -> None:
        """Evaluate quality gate limits."""
        if self.max_drawdown > 0:
            raise ValueError("max_drawdown must be negative or zero")

    def serialize(self) -> Dict[str, Any]:
        """Canonical serialization."""
        return {
            "model_version_id": self.model_version_id,
            "sharpe_ratio": self.sharpe_ratio,
            "max_drawdown": self.max_drawdown,
            "ece": self.ece,
            "brier_score": self.brier_score,
            "win_rate": self.win_rate,
            "profit_factor": self.profit_factor,
            "sortino_ratio": self.sortino_ratio,
            "trade_count": self.trade_count,
            "is_approved": self.is_approved,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None
        }

    def __lt__(self, other: "EvaluationResult") -> bool:
        if not isinstance(other, EvaluationResult):
            return NotImplemented
        return self.sharpe_ratio < other.sharpe_ratio


@dataclass(frozen=True)
class PromotionRecord:
    """Immutable promotion ledger entry."""
    promotion_id: str
    model_version_id: str
    previous_state: ModelLifecycleState
    new_state: ModelLifecycleState
    promoted_by: str
    promoted_at: datetime
    promotion_reason: Optional[str] = None
    approval_reference: Optional[str] = None

    def __post_init__(self):
        if not self.promotion_id:
            raise ValueError("promotion_id cannot be empty")
        if not self.model_version_id:
            raise ValueError("model_version_id cannot be empty")
        if not isinstance(self.previous_state, ModelLifecycleState):
            raise TypeError("previous_state must be a ModelLifecycleState instance")
        if not isinstance(self.new_state, ModelLifecycleState):
            raise TypeError("new_state must be a ModelLifecycleState instance")
        if not self.promoted_by:
            raise ValueError("promoted_by cannot be empty")
        if not isinstance(self.promoted_at, datetime):
            raise TypeError("promoted_at must be a datetime instance")

    def validate(self) -> None:
        """Validate logical state transitions."""
        valid_transitions = {
            ModelLifecycleState.DRAFT: [ModelLifecycleState.CANDIDATE, ModelLifecycleState.ARCHIVED],
            ModelLifecycleState.CANDIDATE: [ModelLifecycleState.VALIDATED, ModelLifecycleState.ARCHIVED],
            ModelLifecycleState.VALIDATED: [ModelLifecycleState.PRODUCTION, ModelLifecycleState.ARCHIVED],
            ModelLifecycleState.PRODUCTION: [ModelLifecycleState.ARCHIVED],
            ModelLifecycleState.ARCHIVED: []
        }
        if self.new_state not in valid_transitions.get(self.previous_state, []):
            raise ValueError(f"Invalid lifecycle transition: {self.previous_state.value} -> {self.new_state.value}")

    def serialize(self) -> Dict[str, Any]:
        """Canonical serialization."""
        return {
            "promotion_id": self.promotion_id,
            "model_version_id": self.model_version_id,
            "previous_state": self.previous_state.value,
            "new_state": self.new_state.value,
            "promoted_by": self.promoted_by,
            "promoted_at": self.promoted_at.isoformat(),
            "promotion_reason": self.promotion_reason,
            "approval_reference": self.approval_reference
        }

    def __lt__(self, other: "PromotionRecord") -> bool:
        if not isinstance(other, PromotionRecord):
            return NotImplemented
        return self.promoted_at < other.promoted_at


# --- Registry Events ---

@dataclass(frozen=True)
class RegistryEvent:
    """Base Event structure for all model registry activities."""
    event_id: str
    timestamp: datetime

    def __post_init__(self):
        if not self.event_id:
            raise ValueError("event_id cannot be empty")
        if not isinstance(self.timestamp, datetime):
            raise TypeError("timestamp must be a datetime instance")

    def serialize(self) -> Dict[str, Any]:
        """Canonical serialization wrapper."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        data["event_type"] = self.__class__.__name__
        return data


@dataclass(frozen=True)
class ModelRegistered(RegistryEvent):
    """Fired when a new Model identifier family is created."""
    model_id: str
    symbol: str
    algorithm: str


@dataclass(frozen=True)
class CandidateCreated(RegistryEvent):
    """Fired when a new version candidate is written to DRAFT/CANDIDATE status."""
    model_version_id: str
    composite_fingerprint: str
    run_id: str


@dataclass(frozen=True)
class ValidationPassed(RegistryEvent):
    """Fired when quality check gates are successfully completed."""
    model_version_id: str
    reviewer: str
    sharpe_ratio: float


@dataclass(frozen=True)
class PromotionCompleted(RegistryEvent):
    """Fired on successful promotion state transition."""
    model_version_id: str
    previous_state: ModelLifecycleState
    new_state: ModelLifecycleState
    promoter: str
    reason: str

    def serialize(self) -> Dict[str, Any]:
        res = super().serialize()
        res["previous_state"] = self.previous_state.value
        res["new_state"] = self.new_state.value
        return res


@dataclass(frozen=True)
class RollbackCompleted(RegistryEvent):
    """Fired on active model version rollback activities."""
    demoted_version_id: str
    promoted_version_id: str
    operator: str


@dataclass(frozen=True)
class Archived(RegistryEvent):
    """Fired when a model is retired to ARCHIVED status."""
    model_version_id: str
    reason: str


# --- Backward Compatibility Structures ---
# These structures maintain code safety for existing service/repository classes
# until they are refactored in future sprints.

@dataclass(frozen=True)
class ModelLineage:
    """Complete upstream lineage per ADR-013."""
    snapshot_id: str
    dataset_id: str
    feature_dataset_id: str
    experiment_id: str
    best_config_id: str


@dataclass(frozen=True)
class ModelEvaluation:
    """Quantitative metrics per ADR-013 promotion policy."""
    sharpe_ratio: float
    max_drawdown: float
    ece: float
    brier_score: float
    win_rate: float
    profit_factor: float
    sortino_ratio: float
    trade_count: int
    is_approved: bool = False
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None


@dataclass
class ModelVersionMetadata:
    """Model version metadata per contract specification."""
    model_version_id: str
    model_id: str
    version: str
    lifecycle_state: ModelLifecycleState
    fingerprint: str
    storage_path: str
    hyperparameters: Dict[str, Any]
    lineage: ModelLineage
    created_at: str
    symbol: str
    timeframe: str
    algorithm: str
    evaluation: Optional[ModelEvaluation] = None
    is_frozen: bool = False
    promoted_at: Optional[str] = None
    promoted_by: Optional[str] = None
    git_commit: Optional[str] = None
    git_tag: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'model_version_id': self.model_version_id,
            'model_id': self.model_id,
            'version': self.version,
            'lifecycle_state': self.lifecycle_state.value,
            'fingerprint': self.fingerprint,
            'storage_path': self.storage_path,
            'hyperparameters': self.hyperparameters,
            'lineage': {
                'snapshot_id': self.lineage.snapshot_id,
                'dataset_id': self.lineage.dataset_id,
                'feature_dataset_id': self.lineage.feature_dataset_id,
                'experiment_id': self.lineage.experiment_id,
                'best_config_id': self.lineage.best_config_id
            },
            'created_at': self.created_at,
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'algorithm': self.algorithm,
            'evaluation': {
                'sharpe_ratio': self.evaluation.sharpe_ratio,
                'max_drawdown': self.evaluation.max_drawdown,
                'ece': self.evaluation.ece,
                'brier_score': self.evaluation.brier_score,
                'win_rate': self.evaluation.win_rate,
                'profit_factor': self.evaluation.profit_factor,
                'sortino_ratio': self.evaluation.sortino_ratio,
                'trade_count': self.evaluation.trade_count,
                'is_approved': self.evaluation.is_approved,
                'approved_by': self.evaluation.approved_by,
                'approved_at': self.evaluation.approved_at
            } if self.evaluation else None,
            'is_frozen': self.is_frozen,
            'promoted_at': self.promoted_at,
            'promoted_by': self.promoted_by,
            'git_commit': self.git_commit,
            'git_tag': self.git_tag
        }


@dataclass
class PromotionRequest:
    """Model promotion request."""
    model_version_id: str
    promoter: str
    notes: Optional[str] = None


@dataclass
class RegistrationRequest:
    """Model registration request."""
    model_id: str
    version_bump: str
    storage_path: str
    hyperparameters: Dict[str, Any]
    lineage: Dict[str, str]
    symbol: str
    timeframe: str
    algorithm: str
    git_commit: Optional[str] = None
    git_tag: Optional[str] = None


@dataclass
class ValidationResult:
    """Result of validation check."""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
