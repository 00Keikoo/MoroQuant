from typing import Dict, List, Optional, Any, Tuple, Union
from ml_service.research.models import ResearchSession, ResearchExperiment, DatasetSnapshot, FeatureSnapshot, ResearchRun
from ml_service.research.research_service import ResearchService
from ml_service.research.dataset_service import DatasetService
from ml_service.research.feature_service import FeatureService
from ml_service.research.experiment_service import ExperimentService

class ResearchOrchestrator:
    """
    Orchestrates the entire research session lifecycle by composing specialized services:
    ResearchService, DatasetService, FeatureService, and ExperimentService.
    Provides a unified entry point (single public API) for executing a complete research workflow.
    """
    def __init__(
        self,
        research_service: ResearchService,
        dataset_service: DatasetService,
        feature_service: FeatureService,
        experiment_service: ExperimentService
    ) -> None:
        self.research_service = research_service
        self.dataset_service = dataset_service
        self.feature_service = feature_service
        self.experiment_service = experiment_service

    def execute_workflow(
        self,
        session_config: Dict[str, Any],
        snapshot_id: str,
        dataset_version_id: str,
        dataset_fingerprint: str,
        dataset_file_path: str,
        feature_dataset_id: str,
        feature_fingerprint: str,
        feature_file_path: str,
        experiment_id: str,
        hypothesis_config: Dict[str, Any],
        runs: Tuple[ResearchRun, ...] = (),
        best_run_id: Optional[str] = None
    ) -> ResearchSession:
        """
        Coordinates the complete research lifecycle sequentially:
        1. Initializes research session (CREATED state).
        2. Registers dataset snapshot.
        3. Registers feature snapshot.
        4. Creates experiment (INITIALIZED state).
        5. Starts session (RUNNING state) & transitions experiment to ACTIVE.
        6. Completes experiment (transitions to EVALUATED state with runs).
        7. Completes research session (COMPLETED state, linking the evaluated experiment and best run).
        
        Implements fail-fast validation and error propagation.
        """
        session_id = session_config.get("session_id")
        
        # 1. Initialize research session
        session = self.research_service.create_session(
            config=session_config,
            session_id=session_id,
            snapshot_id=snapshot_id
        )
        session_id = session.session_id

        try:
            # 2. Register dataset snapshot
            self.dataset_service.create_snapshot(
                dataset_version_id=dataset_version_id,
                fingerprint=dataset_fingerprint,
                file_path=dataset_file_path,
                is_frozen=True
            )

            # 3. Register feature snapshot
            self.feature_service.create_snapshot(
                feature_dataset_id=feature_dataset_id,
                source_dataset_id=dataset_version_id,
                fingerprint=feature_fingerprint,
                file_path=feature_file_path,
                is_frozen=True
            )

            # 4. Create experiment
            self.experiment_service.create_experiment(
                session_id=session_id,
                hypothesis_config=hypothesis_config,
                experiment_id=experiment_id
            )

            # 5. Start session & start experiment
            session = self.research_service.start_session(session_id)
            experiment = self.experiment_service.start_experiment(experiment_id)

            # 6. Complete experiment
            experiment = self.experiment_service.complete_experiment(
                experiment_id=experiment_id,
                runs=runs
            )

            # 7. Complete research session
            session = self.research_service.complete_session(
                session_id=session_id,
                best_run_id=best_run_id,
                experiments=(experiment,)
            )
            return session

        except Exception as e:
            # Fail-fast and transition session to FAILED if it was running
            if self.research_service.has_session(session_id):
                curr_session = self.research_service.get_session(session_id)
                if curr_session.status == "RUNNING":
                    exps = ()
                    if self.experiment_service.has_experiment(experiment_id):
                        exps = (self.experiment_service.get_experiment(experiment_id),)
                    self.research_service.fail_session(session_id, experiments=exps)
            raise e
