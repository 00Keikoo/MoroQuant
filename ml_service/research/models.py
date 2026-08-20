from dataclasses import dataclass, field, asdict
from typing import Tuple, Optional, Any, Dict, Union
import json

@dataclass(frozen=True)
class DatasetSnapshot:
    dataset_version_id: str
    fingerprint: str
    file_path: str
    is_frozen: bool
    created_at: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dataset_version_id": self.dataset_version_id,
            "fingerprint": self.fingerprint,
            "file_path": self.file_path,
            "is_frozen": self.is_frozen,
            "created_at": self.created_at
        }

@dataclass(frozen=True)
class FeatureSnapshot:
    feature_dataset_id: str
    source_dataset_id: str
    fingerprint: str
    file_path: str
    is_frozen: bool
    created_at: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "feature_dataset_id": self.feature_dataset_id,
            "source_dataset_id": self.source_dataset_id,
            "fingerprint": self.fingerprint,
            "file_path": self.file_path,
            "is_frozen": self.is_frozen,
            "created_at": self.created_at
        }

@dataclass(frozen=True)
class ResearchRun:
    run_id: str
    experiment_id: str
    status: str
    session_id: str = ""
    hyperparameters: Tuple[Tuple[str, Union[str, int, float, bool, None]], ...] = field(default_factory=tuple)
    metrics: Tuple[Tuple[str, float], ...] = field(default_factory=tuple)
    model_binary_path: Optional[str] = None
    created_at: str = ""
    completed_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        # Enforce sorted keys for hyperparameters and metrics to ensure deterministic order
        sorted_hparams = sorted(self.hyperparameters, key=lambda x: x[0])
        sorted_metrics = sorted(self.metrics, key=lambda x: x[0])
        return {
            "run_id": self.run_id,
            "experiment_id": self.experiment_id,
            "status": self.status,
            "session_id": self.session_id,
            "hyperparameters": [list(item) for item in sorted_hparams],
            "metrics": [list(item) for item in sorted_metrics],
            "model_binary_path": self.model_binary_path,
            "created_at": self.created_at,
            "completed_at": self.completed_at
        }

@dataclass(frozen=True)
class ResearchExperiment:
    experiment_id: str
    session_id: str
    status: str
    hypothesis_config: Tuple[Tuple[str, Union[str, int, float, bool, None]], ...] = field(default_factory=tuple)
    runs: Tuple[ResearchRun, ...] = field(default_factory=tuple)
    created_at: str = ""
    completed_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        sorted_hypothesis = sorted(self.hypothesis_config, key=lambda x: x[0])
        # Sort runs by run_id for deterministic ordering
        sorted_runs = sorted(self.runs, key=lambda r: r.run_id)
        return {
            "experiment_id": self.experiment_id,
            "session_id": self.session_id,
            "status": self.status,
            "hypothesis_config": [list(item) for item in sorted_hypothesis],
            "runs": [run.to_dict() for run in sorted_runs],
            "created_at": self.created_at,
            "completed_at": self.completed_at
        }

@dataclass(frozen=True)
class ResearchSession:
    session_id: str
    status: str
    config_snapshot: Tuple[Tuple[str, Union[str, int, float, bool, None]], ...] = field(default_factory=tuple)
    snapshot_id: Optional[str] = None
    dataset_version_id: Optional[str] = None
    feature_dataset_id: Optional[str] = None
    best_run_id: Optional[str] = None
    experiments: Tuple[ResearchExperiment, ...] = field(default_factory=tuple)
    created_at: str = ""
    completed_at: Optional[str] = None
    dataset_fingerprint: Optional[str] = None
    feature_fingerprint: Optional[str] = None
    replay_fingerprint: Optional[str] = None
    experiment_fingerprint: Optional[str] = None
    evaluation_fingerprint: Optional[str] = None
    model_fingerprint: Optional[str] = None
    random_seed: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        sorted_config = sorted(self.config_snapshot, key=lambda x: x[0])
        sorted_experiments = sorted(self.experiments, key=lambda e: e.experiment_id)
        return {
            "session_id": self.session_id,
            "status": self.status,
            "config_snapshot": [list(item) for item in sorted_config],
            "snapshot_id": self.snapshot_id,
            "dataset_version_id": self.dataset_version_id,
            "feature_dataset_id": self.feature_dataset_id,
            "best_run_id": self.best_run_id,
            "experiments": [exp.to_dict() for exp in sorted_experiments],
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "dataset_fingerprint": self.dataset_fingerprint,
            "feature_fingerprint": self.feature_fingerprint,
            "replay_fingerprint": self.replay_fingerprint,
            "experiment_fingerprint": self.experiment_fingerprint,
            "evaluation_fingerprint": self.evaluation_fingerprint,
            "model_fingerprint": self.model_fingerprint,
            "random_seed": self.random_seed,
        }

    def serialize(self) -> str:
        """Returns a deterministic JSON string serialization."""
        return json.dumps(self.to_dict(), sort_keys=True)
