"""Types for model registry."""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from enum import Enum


class ModelLifecycleState(Enum):
    """Model lifecycle states per ADR-013."""
    CANDIDATE = "CANDIDATE"
    VALIDATED = "VALIDATED"
    PRODUCTION = "PRODUCTION"
    ARCHIVED = "ARCHIVED"


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
        """Convert to dictionary for JSON serialization."""
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
