import datetime
import uuid
from typing import Dict, Tuple, Optional, Any, Union, List
from dataclasses import replace

from ml_service.research.models import ResearchRun
from ml_service.research.research_session import make_immutable

class ResearchRunManager:
    """
    Manages the lifecycle, state transitions, and validation of Research Runs.
    Enforces immutability, determinism, and strict state transition rules.
    """
    def __init__(self) -> None:
        self._runs: Dict[str, ResearchRun] = {}

    def get_run(self, run_id: str) -> ResearchRun:
        """Retrieves a run by its ID. Raises KeyError if not found."""
        if run_id not in self._runs:
            raise KeyError(f"Run with ID '{run_id}' not found.")
        return self._runs[run_id]

    def exists(self, run_id: str) -> bool:
        """Checks if a run exists by its ID."""
        return run_id in self._runs

    def list_runs(self) -> List[ResearchRun]:
        """Returns a list of all runs sorted by run_id for deterministic ordering."""
        return sorted(self._runs.values(), key=lambda r: r.run_id)

    def create_run(
        self,
        experiment_id: str,
        hyperparameters: Union[Dict[str, Any], Tuple[Tuple[str, Union[str, int, float, bool, None]], ...]] = (),
        run_id: Optional[str] = None,
        created_at: Optional[str] = None,
        session_id: str = ""
    ) -> ResearchRun:
        """
        Creates and registers a new ResearchRun in 'CREATED' status.
        Ensures config is converted to a sorted, deterministic, immutable tuple.
        """
        if run_id is None:
            run_id = str(uuid.uuid4())

        if created_at is None:
            created_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

        immutable_config = make_immutable(hyperparameters)
        # Verify it's a tuple of (key, value) pairs
        if not isinstance(immutable_config, tuple) or not all(isinstance(x, tuple) and len(x) == 2 for x in immutable_config):
            if isinstance(immutable_config, tuple):
                normalized_config = tuple(sorted((f"param_{i}", x) for i, x in enumerate(immutable_config)))
            else:
                normalized_config = (("config", immutable_config),)
        else:
            normalized_config = immutable_config

        run = ResearchRun(
            run_id=run_id,
            experiment_id=experiment_id,
            status="CREATED",
            session_id=session_id,
            hyperparameters=normalized_config,
            metrics=(),
            model_binary_path=None,
            created_at=created_at,
            completed_at=None
        )

        self._runs[run_id] = run
        return run

    def start_run(self, run_id: str) -> ResearchRun:
        """
        Transitions a run from 'CREATED' to 'RUNNING'.
        Raises ValueError for invalid state transitions.
        """
        run = self.get_run(run_id)
        if run.status != "CREATED":
            raise ValueError(f"Cannot start run '{run_id}' in status '{run.status}'. Only 'CREATED' is valid.")

        updated_run = replace(run, status="RUNNING")
        self._runs[run_id] = updated_run
        return updated_run

    def complete_run(
        self,
        run_id: str,
        metrics: Union[Dict[str, float], Tuple[Tuple[str, float], ...]] = (),
        model_binary_path: Optional[str] = None,
        completed_at: Optional[str] = None
    ) -> ResearchRun:
        """
        Transitions a run from 'RUNNING' to 'COMPLETED'.
        Raises ValueError for invalid state transitions.
        """
        run = self.get_run(run_id)
        if run.status != "RUNNING":
            raise ValueError(f"Cannot complete run '{run_id}' in status '{run.status}'. Only 'RUNNING' is valid.")

        if completed_at is None:
            completed_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

        immutable_metrics = make_immutable(metrics)
        if not isinstance(immutable_metrics, tuple) or not all(isinstance(x, tuple) and len(x) == 2 for x in immutable_metrics):
            if isinstance(immutable_metrics, tuple):
                normalized_metrics = tuple(sorted((f"metric_{i}", x) for i, x in enumerate(immutable_metrics)))
            else:
                normalized_metrics = (("metric", immutable_metrics),)
        else:
            normalized_metrics = immutable_metrics

        updated_run = replace(
            run,
            status="COMPLETED",
            metrics=normalized_metrics,
            model_binary_path=model_binary_path,
            completed_at=completed_at
        )
        self._runs[run_id] = updated_run
        return updated_run

    def fail_run(self, run_id: str, completed_at: Optional[str] = None) -> ResearchRun:
        """
        Transitions a run from 'RUNNING' to 'FAILED'.
        Raises ValueError for invalid state transitions.
        """
        run = self.get_run(run_id)
        if run.status != "RUNNING":
            raise ValueError(f"Cannot fail run '{run_id}' in status '{run.status}'. Only 'RUNNING' is valid.")

        if completed_at is None:
            completed_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

        updated_run = replace(
            run,
            status="FAILED",
            completed_at=completed_at
        )
        self._runs[run_id] = updated_run
        return updated_run

    def cancel_run(self, run_id: str, completed_at: Optional[str] = None) -> ResearchRun:
        """
        Transitions a run from 'CREATED' or 'RUNNING' to 'CANCELLED'.
        Raises ValueError for invalid state transitions.
        """
        run = self.get_run(run_id)
        if run.status not in ("CREATED", "RUNNING"):
            raise ValueError(f"Cannot cancel run '{run_id}' in status '{run.status}'. Only 'CREATED' or 'RUNNING' are valid.")

        if completed_at is None:
            completed_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

        updated_run = replace(
            run,
            status="CANCELLED",
            completed_at=completed_at
        )
        self._runs[run_id] = updated_run
        return updated_run
