"""Adapter for building ExperimentConfig from ResearchSession.

Provides clean semantic translation between orchestrator and experiment engine boundaries.
"""

from typing import List
from ml_service.research.models import ResearchSession
from ml_service.research.experiment_engine.types import ExperimentConfig, StrategyConfig


class ExperimentConfigAdapter:
    """Adapter for translating ResearchSession to ExperimentConfig."""

    @staticmethod
    def from_session(session: ResearchSession, experiment_id: str) -> ExperimentConfig:
        """Build ExperimentConfig from ResearchSession.config_snapshot.

        Args:
            session: ResearchSession containing configuration
            experiment_id: Unique experiment identifier

        Returns:
            ExperimentConfig with extracted strategy configurations

        Raises:
            ValueError: If required configuration fields are missing
        """
        if not session.snapshot_id:
            raise ValueError("ResearchSession missing snapshot_id required for experiment")

        # Extract strategy configs from config_snapshot
        config_dict = dict(session.config_snapshot)

        # Build strategy configurations
        configs: List[StrategyConfig] = []

        # Extract threshold parameters (defaults if not in config)
        threshold_long = config_dict.get('threshold_long', 0.5)
        threshold_short = config_dict.get('threshold_short', 0.5)
        enable_filter = config_dict.get('enable_filter', False)
        regime_filter = config_dict.get('regime_filter')

        # Create a single strategy config with extracted parameters
        # For multi-strategy experiments, this would iterate over strategy_configs list
        config_id = config_dict.get('config_id', 'default')

        configs.append(StrategyConfig(
            config_id=config_id,
            threshold_long=float(threshold_long),
            threshold_short=float(threshold_short),
            enable_filter=bool(enable_filter),
            regime_filter=regime_filter if isinstance(regime_filter, str) else None
        ))

        return ExperimentConfig(
            experiment_id=experiment_id,
            snapshot_id=session.snapshot_id,
            configs=configs
        )
