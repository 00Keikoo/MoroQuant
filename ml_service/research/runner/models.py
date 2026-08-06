from dataclasses import dataclass, field
from typing import Tuple, Dict, Any, Optional
from ml_service.research.replay_engine.types import ReplayResult
from ml_service.research.strategy.models import FeatureSnapshot, Signal
from ml_service.research.strategy.inference.models import InferenceResult
from ml_service.research.evaluation_engine.types import EvaluationResult
from ml_service.research.experiment.models import ExperimentRun

@dataclass(frozen=True)
class ResearchRunResult:
    """
    Immutable, deterministic result container for an end-to-end research run.
    """
    run_id: str
    dataset_snapshot_id: str
    replay_result: ReplayResult
    feature_snapshot: FeatureSnapshot
    inference_result: InferenceResult
    signals: Tuple[Signal, ...]
    evaluation_result: EvaluationResult
    experiment_run: ExperimentRun
    metadata: Tuple[Tuple[str, Any], ...] = field(default_factory=tuple)

    def to_dict(self) -> Dict[str, Any]:
        """Convert the result to a dictionary recursively."""
        def _convert(val: Any) -> Any:
            if hasattr(val, "to_dict"):
                return val.to_dict()
            if isinstance(val, tuple):
                return [_convert(x) for x in val]
            if isinstance(val, dict):
                return {k: _convert(v) for k, v in val.items()}
            return val

        return {
            "run_id": self.run_id,
            "dataset_snapshot_id": self.dataset_snapshot_id,
            "replay_result": _convert(self.replay_result),
            "feature_snapshot": _convert(self.feature_snapshot),
            "inference_result": _convert(self.inference_result),
            "signals": _convert(self.signals),
            "evaluation_result": _convert(self.evaluation_result),
            "experiment_run": _convert(self.experiment_run),
            "metadata": [list(item) for item in self.metadata]
        }
