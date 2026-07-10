"""Service layer for experiment engine."""

import pickle
from pathlib import Path
from typing import Optional

from ml_service.research.snapshot_engine import SnapshotService
from ml_service.research.replay_engine import ReplayService
from ml_service.research.experiment_engine.types import (
    ExperimentConfig,
    ExperimentResult,
    StrategyResult
)
from ml_service.research.experiment_engine.engine import apply_strategy_config


class ExperimentService:
    """Service for managing experiments."""

    def __init__(self, db_path: Optional[str] = None):
        """Initialize experiment service.

        Args:
            db_path: Optional database path for snapshot/replay services
        """
        self.snapshot_service = SnapshotService(db_path=db_path)
        self.replay_service = ReplayService(db_path=db_path)

    def run_experiment(self, experiment_config: ExperimentConfig, artifact_dir: Optional[str] = None) -> Optional[ExperimentResult]:
        """Run experiment with multiple strategy configurations using Decision Truth Layer.

        Args:
            experiment_config: Experiment configuration
            artifact_dir: Optional directory to store experiment artifact

        Returns:
            ExperimentResult if snapshot exists, None otherwise
        """
        snapshot = self.snapshot_service.get_snapshot(experiment_config.snapshot_id)
        if snapshot is None:
            return None

        base_threshold = 0.5
        replay_result = self.replay_service.run(
            snapshot,
            threshold_long=base_threshold,
            threshold_short=base_threshold
        )

        results = []
        for config in experiment_config.configs:
            strategy_result = apply_strategy_config(replay_result, snapshot, config)
            results.append(strategy_result)

        artifact_path = None
        if artifact_dir:
            artifact_path = self._serialize_artifact(experiment_config, results, replay_result, artifact_dir)

        return ExperimentResult(
            experiment_id=experiment_config.experiment_id,
            snapshot_id=experiment_config.snapshot_id,
            results=results,
            artifact_path=artifact_path
        )

    def _serialize_artifact(self, config: ExperimentConfig, results: list, replay_result, artifact_dir: str) -> str:
        """Serialize experiment artifact to model.bin."""
        artifact_path = Path(artifact_dir)
        artifact_path.mkdir(parents=True, exist_ok=True)

        model_file = artifact_path / "model.bin"

        artifact_data = {
            'experiment_id': config.experiment_id,
            'snapshot_id': config.snapshot_id,
            'configs': config.configs,
            'results': results,
            'replay_metadata': {
                'consistency_score': replay_result.consistency_score,
                'divergence_score': replay_result.divergence_score,
                'signal_reproduction_rate': replay_result.signal_reproduction_rate,
                'execution_alignment_rate': replay_result.execution_alignment_rate
            }
        }

        with open(model_file, 'wb') as f:
            pickle.dump(artifact_data, f)

        return str(model_file)
