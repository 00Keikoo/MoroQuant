"""Service layer for experiment engine."""

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

    def run_experiment(self, experiment_config: ExperimentConfig) -> Optional[ExperimentResult]:
        """Run experiment with multiple strategy configurations using Decision Truth Layer.

        Args:
            experiment_config: Experiment configuration

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

        return ExperimentResult(
            experiment_id=experiment_config.experiment_id,
            snapshot_id=experiment_config.snapshot_id,
            results=results
        )
