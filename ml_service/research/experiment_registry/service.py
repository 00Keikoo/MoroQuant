"""Service API for experiment registry."""

from typing import List, Optional

from ml_service.research.experiment_engine.types import ExperimentResult, StrategyConfig
from ml_service.research.experiment_registry.types import StoredExperiment, ComparisonResult
from ml_service.research.experiment_registry import registry


class ExperimentRegistryService:
    """Public API for experiment registry operations."""

    def save(self, experiment_result: ExperimentResult, configs: Optional[List[StrategyConfig]] = None):
        """Save experiment with optional configs.

        Args:
            experiment_result: Experiment result to save
            configs: Optional strategy configs used in experiment
        """
        if configs:
            registry.save_experiment_with_configs(experiment_result, configs)
        else:
            registry.save_experiment(experiment_result)

    def load(self, experiment_id: str) -> Optional[StoredExperiment]:
        """Load experiment by ID.

        Args:
            experiment_id: Experiment ID to load

        Returns:
            StoredExperiment if found, None otherwise
        """
        return registry.load_experiment(experiment_id)

    def list_all(self) -> List[StoredExperiment]:
        """List all experiments.

        Returns:
            List of stored experiments
        """
        return registry.list_experiments()

    def compare(self, base_id: str, compare_id: str) -> Optional[ComparisonResult]:
        """Compare two experiments.

        Args:
            base_id: Base experiment ID
            compare_id: Comparison experiment ID

        Returns:
            ComparisonResult if both experiments exist, None otherwise
        """
        return registry.compare_experiments(base_id, compare_id)
