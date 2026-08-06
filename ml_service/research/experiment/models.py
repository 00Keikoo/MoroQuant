from dataclasses import dataclass, field
from typing import Dict, Any, Tuple
import json
import hashlib
from ml_service.research.research_session import make_immutable

@dataclass(frozen=True)
class ExperimentRun:
    """
    Immutable model representing a single experiment run.
    Conforms to ADR-024 (immutable, deterministic, reproducible identity).
    """
    experiment_id: str
    model_version_id: str
    dataset_snapshot_id: str
    strategy_id: str
    feature_schema_version: str
    evaluation_summary: Tuple[Tuple[str, Any], ...] = field(default_factory=tuple)

    def __post_init__(self):
        # Convert evaluation_summary to immutable tuples recursively
        object.__setattr__(self, "evaluation_summary", make_immutable(self.evaluation_summary))
        
        # Validation checks
        if not self.experiment_id:
            raise ValueError("experiment_id cannot be empty")
        if not self.model_version_id:
            raise ValueError("model_version_id cannot be empty")
        if not self.dataset_snapshot_id:
            raise ValueError("dataset_snapshot_id cannot be empty")
        if not self.strategy_id:
            raise ValueError("strategy_id cannot be empty")
        if not self.feature_schema_version:
            raise ValueError("feature_schema_version cannot be empty")

    def to_dict(self) -> Dict[str, Any]:
        """Convert the ExperimentRun to a dictionary with sorted evaluation summary keys."""
        sorted_summary = sorted(self.evaluation_summary, key=lambda x: x[0])
        
        # Recursively convert inner tuples back to lists/dicts for JSON serialization
        def _convert(val: Any) -> Any:
            if isinstance(val, tuple):
                # If it's a tuple of 2-tuples, it might represent a dictionary
                if all(isinstance(x, tuple) and len(x) == 2 for x in val):
                    return {k: _convert(v) for k, v in val}
                return [_convert(x) for x in val]
            return val

        return {
            "experiment_id": self.experiment_id,
            "model_version_id": self.model_version_id,
            "dataset_snapshot_id": self.dataset_snapshot_id,
            "strategy_id": self.strategy_id,
            "feature_schema_version": self.feature_schema_version,
            "evaluation_summary": _convert(sorted_summary)
        }

    def serialize(self) -> str:
        """Returns a deterministic JSON string representation."""
        return json.dumps(self.to_dict(), sort_keys=True)

    def get_identity(self) -> str:
        """Generate a reproducible cryptographic identity hash (SHA-256)."""
        return hashlib.sha256(self.serialize().encode("utf-8")).hexdigest()
