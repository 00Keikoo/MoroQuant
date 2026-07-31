import datetime
import uuid
from typing import Dict, Tuple, Optional, Any, Union
from dataclasses import replace

from ml_service.research.models import ResearchExperiment, ResearchRun
from ml_service.research.research_session import make_immutable

class ResearchExperimentManager:
    """
    Manages the lifecycle, state transitions, and validation of Research Experiments.
    Enforces immutability, determinism, and strict state transition rules.
    """
    def __init__(self) -> None:
        self._experiments: Dict[str, ResearchExperiment] = {}

    def get_experiment(self, experiment_id: str) -> ResearchExperiment:
        """Retrieves an experiment by its ID. Raises KeyError if not found."""
        if experiment_id not in self._experiments:
            raise KeyError(f"Experiment with ID '{experiment_id}' not found.")
        return self._experiments[experiment_id]

    def create_experiment(
        self,
        session_id: str,
        hypothesis_config: Union[Dict[str, Any], Tuple[Tuple[str, Union[str, int, float, bool, None]], ...]],
        experiment_id: Optional[str] = None,
        created_at: Optional[str] = None
    ) -> ResearchExperiment:
        """
        Creates and registers a new ResearchExperiment in 'INITIALIZED' status.
        Ensures hypothesis_config is converted to a sorted, deterministic, immutable tuple.
        """
        if experiment_id is None:
            experiment_id = str(uuid.uuid4())
        
        if created_at is None:
            created_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

        immutable_config = make_immutable(hypothesis_config)
        # Verify it's a tuple of (key, value) pairs
        if not isinstance(immutable_config, tuple) or not all(isinstance(x, tuple) and len(x) == 2 for x in immutable_config):
            if isinstance(immutable_config, tuple):
                normalized_config = tuple(sorted((f"param_{i}", x) for i, x in enumerate(immutable_config)))
            else:
                normalized_config = (("config", immutable_config),)
        else:
            normalized_config = immutable_config

        experiment = ResearchExperiment(
            experiment_id=experiment_id,
            session_id=session_id,
            status="INITIALIZED",
            hypothesis_config=normalized_config,
            runs=(),
            created_at=created_at,
            completed_at=None
        )

        self._experiments[experiment_id] = experiment
        return experiment

    def start_experiment(self, experiment_id: str) -> ResearchExperiment:
        """
        Transitions an experiment from 'INITIALIZED' to 'ACTIVE'.
        Raises ValueError for invalid state transitions.
        """
        experiment = self.get_experiment(experiment_id)
        if experiment.status != "INITIALIZED":
            raise ValueError(f"Cannot start experiment '{experiment_id}' in status '{experiment.status}'. Only 'INITIALIZED' is valid.")

        updated_experiment = replace(experiment, status="ACTIVE")
        self._experiments[experiment_id] = updated_experiment
        return updated_experiment

    def complete_experiment(
        self,
        experiment_id: str,
        runs: Tuple[ResearchRun, ...] = (),
        completed_at: Optional[str] = None
    ) -> ResearchExperiment:
        """
        Transitions an experiment from 'ACTIVE' to 'EVALUATED'.
        Raises ValueError for invalid state transitions.
        """
        experiment = self.get_experiment(experiment_id)
        if experiment.status != "ACTIVE":
            raise ValueError(f"Cannot complete experiment '{experiment_id}' in status '{experiment.status}'. Only 'ACTIVE' is valid.")

        if completed_at is None:
            completed_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

        runs_tuple = tuple(runs)

        updated_experiment = replace(
            experiment,
            status="EVALUATED",
            runs=runs_tuple,
            completed_at=completed_at
        )
        self._experiments[experiment_id] = updated_experiment
        return updated_experiment

    def fail_experiment(
        self,
        experiment_id: str,
        runs: Tuple[ResearchRun, ...] = (),
        completed_at: Optional[str] = None
    ) -> ResearchExperiment:
        """
        Transitions an experiment from 'ACTIVE' to 'FAILED'.
        Raises ValueError for invalid state transitions.
        """
        experiment = self.get_experiment(experiment_id)
        if experiment.status != "ACTIVE":
            raise ValueError(f"Cannot fail experiment '{experiment_id}' in status '{experiment.status}'. Only 'ACTIVE' is valid.")

        if completed_at is None:
            completed_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

        runs_tuple = tuple(runs)

        updated_experiment = replace(
            experiment,
            status="FAILED",
            runs=runs_tuple,
            completed_at=completed_at
        )
        self._experiments[experiment_id] = updated_experiment
        return updated_experiment

    def cancel_experiment(
        self,
        experiment_id: str,
        completed_at: Optional[str] = None
    ) -> ResearchExperiment:
        """
        Transitions an experiment from 'INITIALIZED' or 'ACTIVE' to 'CANCELLED'.
        Raises ValueError for invalid state transitions.
        """
        experiment = self.get_experiment(experiment_id)
        if experiment.status not in ("INITIALIZED", "ACTIVE"):
            raise ValueError(f"Cannot cancel experiment '{experiment_id}' in status '{experiment.status}'. Only 'INITIALIZED' or 'ACTIVE' are valid.")

        if completed_at is None:
            completed_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

        updated_experiment = replace(
            experiment,
            status="CANCELLED",
            completed_at=completed_at
        )
        self._experiments[experiment_id] = updated_experiment
        return updated_experiment
