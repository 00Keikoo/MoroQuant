"""
Research Session Orchestrator

Coordinates research pipeline stages over ResearchSession state.
Thin coordinator (<500 LOC) that invokes existing engines without implementing business logic.

Pipeline:
    Snapshot → Replay → Experiment → Evaluation → Reporting → Benchmark → Promotion → Registry
"""

from dataclasses import replace
from datetime import datetime
from typing import Any, Optional, Callable
import uuid

from ml_service.research.models import ResearchSession
from ml_service.research import provenance
from ml_service.research.model_identity.scanner import ModelArtifactScanner
from ml_service.research.model_lifecycle.lifecycle import LifecycleManager
from ml_service.research.model_lifecycle.models import LifecycleState
from ml_service.research.model_registry.model_types import ModelLifecycleState, PromotionRecord
from ml_service.research.model_registry.registry_manager import RegistryManager
from ml_service.research.promotion_engine.models import PromotionStatus
from ml_service.research.promotion_engine.benchmark_adapter import evaluate_with_benchmark


class ResearchSessionStatus:
    """Canonical session states."""
    PENDING = "PENDING"
    SNAPSHOT = "SNAPSHOT"
    REPLAY = "REPLAY"
    EXPERIMENT = "EXPERIMENT"
    EVALUATION = "EVALUATION"
    REPORTING = "REPORTING"
    BENCHMARK = "BENCHMARK"
    PROMOTION = "PROMOTION"
    COMPLETED = "COMPLETED"
    FAILED_SNAPSHOT = "FAILED/SNAPSHOT"
    FAILED_REPLAY = "FAILED/REPLAY"
    FAILED_EXPERIMENT = "FAILED/EXPERIMENT"
    FAILED_EVALUATION = "FAILED/EVALUATION"
    FAILED_REPORTING = "FAILED/REPORTING"
    FAILED_BENCHMARK = "FAILED/BENCHMARK"
    FAILED_PROMOTION = "FAILED/PROMOTION"


class ResearchSessionOrchestrator:
    """
    Orchestrates research pipeline over ResearchSession.

    Responsibilities:
    - Validate session state
    - Invoke existing stage engines in correct order
    - Receive stage results
    - Compute provenance fingerprints
    - Update immutable session state
    - Persist state transitions
    - Handle stage failures

    Does NOT implement:
    - Replay algorithms
    - Trading metrics
    - Benchmark scoring
    - Promotion policy
    - Governance policy
    - Registry business logic
    - Model training
    - Feature calculation

    Target: <500 LOC
    """

    def __init__(
        self,
        snapshot_engine,
        replay_engine,
        experiment_engine,
        evaluation_engine,
        reporting_engine,
        benchmark_engine,
        promotion_engine,
        registry_service,
        repository,
        scanner_factory: Optional[type] = None,
        lifecycle_manager_factory: Optional[Callable] = None,
        evaluate_with_benchmark_func: Optional[Callable] = None,
    ):
        self.snapshot_engine = snapshot_engine
        self.replay_engine = replay_engine
        self.experiment_engine = experiment_engine
        self.evaluation_engine = evaluation_engine
        self.reporting_engine = reporting_engine
        self.benchmark_engine = benchmark_engine
        self.promotion_engine = promotion_engine
        self.registry_service = registry_service
        self.repository = repository
        self.scanner_factory = scanner_factory or ModelArtifactScanner
        self.lifecycle_manager_factory = lifecycle_manager_factory or (lambda: LifecycleManager())
        self.evaluate_with_benchmark_func = evaluate_with_benchmark_func or evaluate_with_benchmark

    def execute_session(self, session: ResearchSession) -> ResearchSession:
        """
        Execute complete research pipeline over session.

        Pipeline stages:
        1. Snapshot - freeze dataset
        2. Replay - deterministic market replay
        3. Experiment - run strategies
        4. Evaluation - compute metrics
        5. Reporting - generate reports
        6. Benchmark - compare against baseline
        7. Promotion - governance decision
        8. Registry - metadata updates

        Args:
            session: Initial ResearchSession

        Returns:
            Final ResearchSession (COMPLETED or FAILED/*)
        """
        session = self._run_snapshot_stage(session)
        if session.status.startswith("FAILED"):
            return session

        session = self._run_replay_stage(session)
        if session.status.startswith("FAILED"):
            return session

        session = self._run_experiment_stage(session)
        if session.status.startswith("FAILED"):
            return session

        session, evaluation_result = self._run_evaluation_stage(session)
        if session.status.startswith("FAILED"):
            return session

        session, report = self._run_reporting_stage(session, evaluation_result)
        if session.status.startswith("FAILED"):
            return session

        session, benchmark_result = self._run_benchmark_stage(session, report)
        if session.status.startswith("FAILED"):
            return session

        session, registry_proposal = self._run_promotion_stage(session, benchmark_result)
        if session.status.startswith("FAILED"):
            return session

        session = self._run_registry_stage(session, registry_proposal)
        if session.status.startswith("FAILED"):
            return session

        session = replace(
            session,
            status=ResearchSessionStatus.COMPLETED,
            completed_at=datetime.utcnow().isoformat(),
        )
        self.repository.save_session(session)

        return session

    def _run_snapshot_stage(self, session: ResearchSession) -> ResearchSession:
        """
        Execute snapshot stage: freeze dataset.

        Returns:
            Updated session with dataset_fingerprint or FAILED/SNAPSHOT
        """
        try:
            session = replace(session, status=ResearchSessionStatus.SNAPSHOT)
            self.repository.save_session(session)

            snapshot_result = self.snapshot_engine.create_snapshot(
                dataset_version_id=session.dataset_version_id,
            )

            dataset_fingerprint = self._compute_dataset_fingerprint(snapshot_result)

            session = replace(
                session,
                status=ResearchSessionStatus.SNAPSHOT,
                snapshot_id=snapshot_result.snapshot_id,
                dataset_fingerprint=dataset_fingerprint,
            )
            self.repository.save_session(session)

            return session

        except Exception as e:
            session = replace(
                session,
                status=ResearchSessionStatus.FAILED_SNAPSHOT,
            )
            self.repository.save_session(session)
            return session

    def _run_replay_stage(self, session: ResearchSession) -> ResearchSession:
        """
        Execute replay stage: deterministic market replay.

        Returns:
            Updated session with replay_fingerprint or FAILED/REPLAY
        """
        try:
            session = replace(session, status=ResearchSessionStatus.REPLAY)
            self.repository.save_session(session)

            replay_result = self.replay_engine.replay(
                snapshot_id=session.snapshot_id,
            )

            replay_fingerprint = self._compute_replay_fingerprint(replay_result)

            session = replace(
                session,
                status=ResearchSessionStatus.REPLAY,
                replay_fingerprint=replay_fingerprint,
            )
            self.repository.save_session(session)

            return session

        except Exception as e:
            session = replace(
                session,
                status=ResearchSessionStatus.FAILED_REPLAY,
            )
            self.repository.save_session(session)
            return session

    def _run_experiment_stage(self, session: ResearchSession) -> ResearchSession:
        """
        Execute experiment stage: run strategies.

        Returns:
            Updated session with experiment_fingerprint or FAILED/EXPERIMENT
        """
        try:
            session = replace(session, status=ResearchSessionStatus.EXPERIMENT)
            self.repository.save_session(session)

            experiment_result = self.experiment_engine.run_experiment(
                session=session,
            )

            experiment_fingerprint = self._compute_experiment_fingerprint(experiment_result)

            session = replace(
                session,
                status=ResearchSessionStatus.EXPERIMENT,
                experiment_fingerprint=experiment_fingerprint,
            )
            self.repository.save_session(session)

            return session

        except Exception as e:
            session = replace(
                session,
                status=ResearchSessionStatus.FAILED_EXPERIMENT,
            )
            self.repository.save_session(session)
            return session

    def _run_evaluation_stage(self, session: ResearchSession) -> tuple[ResearchSession, Any]:
        """
        Execute evaluation stage: compute metrics.

        Returns:
            Tuple of (Updated session, evaluation_result)
        """
        try:
            session = replace(session, status=ResearchSessionStatus.EVALUATION)
            self.repository.save_session(session)

            evaluation_result = self.evaluation_engine.evaluate(
                session=session,
            )

            evaluation_fingerprint = self._compute_evaluation_fingerprint(evaluation_result)

            session = replace(
                session,
                status=ResearchSessionStatus.EVALUATION,
                evaluation_fingerprint=evaluation_fingerprint,
            )
            self.repository.save_session(session)

            return session, evaluation_result

        except Exception as e:
            session = replace(
                session,
                status=ResearchSessionStatus.FAILED_EVALUATION,
            )
            self.repository.save_session(session)
            return session, None

    def _run_reporting_stage(self, session: ResearchSession, evaluation_result: Any) -> tuple[ResearchSession, Any]:
        """
        Execute reporting stage: generate reports.

        Returns:
            Tuple of (Updated session, report)
        """
        try:
            session = replace(session, status=ResearchSessionStatus.REPORTING)
            self.repository.save_session(session)

            report = self.reporting_engine.generate_report(
                evaluation_result=evaluation_result,
            )

            return session, report

        except Exception as e:
            session = replace(
                session,
                status=ResearchSessionStatus.FAILED_REPORTING,
            )
            self.repository.save_session(session)
            return session, None

    def _run_benchmark_stage(self, session: ResearchSession, report: Any) -> tuple[ResearchSession, Any]:
        """
        Execute benchmark stage: compare against baseline.

        Returns:
            Tuple of (Updated session, benchmark_result)
        """
        try:
            session = replace(session, status=ResearchSessionStatus.BENCHMARK)
            self.repository.save_session(session)

            benchmark_result = self.benchmark_engine.benchmark(
                report=report,
            )

            return session, benchmark_result

        except Exception as e:
            session = replace(
                session,
                status=ResearchSessionStatus.FAILED_BENCHMARK,
            )
            self.repository.save_session(session)
            return session, None

    def _run_promotion_stage(self, session: ResearchSession, benchmark_result: Any) -> tuple[ResearchSession, Any]:
        """
        Execute promotion stage: governance decision.

        Promotion rejection is NOT a failure - it's a valid outcome.

        Returns:
            Tuple of (Updated session, registry_proposal)
        """
        try:
            session = replace(session, status=ResearchSessionStatus.PROMOTION)
            self.repository.save_session(session)

            artifact_path = self._resolve_artifact_path(session)

            model_identity = self._create_model_identity(artifact_path)
            lifecycle_record = self._evaluate_lifecycle(model_identity)

            registry_proposal = self.evaluate_with_benchmark_func(
                engine=self.promotion_engine,
                benchmark=benchmark_result,
                model_identity=model_identity,
                lifecycle_record=lifecycle_record,
            )

            return session, registry_proposal

        except Exception as e:
            session = replace(
                session,
                status=ResearchSessionStatus.FAILED_PROMOTION,
            )
            self.repository.save_session(session)
            return session, None

    def _run_registry_stage(self, session: ResearchSession, registry_proposal: Any) -> ResearchSession:
        """
        Execute registry stage: update metadata.

        Only mutates Registry if proposal status == APPROVED.

        Returns:
            Updated session with model_fingerprint
        """
        try:
            if registry_proposal.status == PromotionStatus.APPROVED:
                promotion_record = self._create_promotion_record(session, registry_proposal)
                self.registry_service.record_promotion(promotion_record)

            model_fingerprint = self._compute_model_fingerprint(session)

            session = replace(
                session,
                model_fingerprint=model_fingerprint,
            )
            self.repository.save_session(session)

            return session

        except Exception as e:
            session = replace(
                session,
                status=ResearchSessionStatus.FAILED_PROMOTION,
            )
            self.repository.save_session(session)
            return session

    def _compute_dataset_fingerprint(self, snapshot_result) -> str:
        """Compute deterministic dataset fingerprint."""
        return provenance.dataset_fingerprint(
            dataset_version_id=snapshot_result.dataset_version_id,
            snapshot_id=snapshot_result.snapshot_id,
            file_hash=getattr(snapshot_result, "file_hash", ""),
        )

    def _compute_replay_fingerprint(self, replay_result) -> str:
        """Compute deterministic replay fingerprint."""
        return provenance.replay_fingerprint(
            dataset_fingerprint=getattr(replay_result, "dataset_fingerprint", ""),
            execution_config=getattr(replay_result, "execution_config", {}),
            random_seed=getattr(replay_result, "random_seed", 0),
        )

    def _compute_experiment_fingerprint(self, experiment_result) -> str:
        """Compute deterministic experiment fingerprint."""
        return provenance.experiment_fingerprint(
            replay_fingerprint=getattr(experiment_result, "replay_fingerprint", ""),
            strategy_config=getattr(experiment_result, "strategy_config", {}),
            model_config=getattr(experiment_result, "model_config", {}),
            random_seed=getattr(experiment_result, "random_seed", 0),
        )

    def _compute_evaluation_fingerprint(self, evaluation_result) -> str:
        """Compute deterministic evaluation fingerprint."""
        return provenance.evaluation_fingerprint(
            experiment_fingerprint=getattr(evaluation_result, "experiment_fingerprint", ""),
            metrics_config=getattr(evaluation_result, "metrics_config", {}),
        )

    def _resolve_artifact_path(self, session: ResearchSession) -> str:
        """Resolve artifact path through RegistryManager."""
        model_version_id = None
        for key, val in session.config_snapshot:
            if key == "model_version_id":
                model_version_id = val
                break

        if not model_version_id:
            raise ValueError("ResearchSession missing model_version_id in config_snapshot")

        registry_manager = RegistryManager(self.registry_service)
        artifact_path = registry_manager.resolve_storage_path(model_version_id)

        if not artifact_path:
            raise ValueError(f"No artifact path found for model_version_id: {model_version_id}")

        return artifact_path

    def _create_model_identity(self, artifact_path: str):
        """Create ModelIdentity using ModelArtifactScanner."""
        from pathlib import Path
        artifact_path_obj = Path(artifact_path)
        model_directory = artifact_path_obj.parent
        scanner = self.scanner_factory(model_directory)
        return scanner.inspect(artifact_path_obj)

    def _evaluate_lifecycle(self, model_identity):
        """Evaluate model lifecycle using LifecycleManager."""
        lifecycle_manager = self.lifecycle_manager_factory()
        return lifecycle_manager.evaluate(model_identity)

    def _create_promotion_record(self, session: ResearchSession, registry_proposal) -> PromotionRecord:
        """Create PromotionRecord from session and proposal."""
        model_version_id = None
        for key, val in session.config_snapshot:
            if key == "model_version_id":
                model_version_id = val
                break

        if not model_version_id:
            raise ValueError("ResearchSession missing model_version_id in config_snapshot")

        previous_state = self._map_lifecycle_state_to_registry(
            LifecycleState(registry_proposal.current_state)
        )
        new_state = self._map_lifecycle_state_to_registry(
            LifecycleState(registry_proposal.proposed_state)
        )

        promotion_id = f"promo-{uuid.uuid4().hex[:12]}"
        promotion_reason = ", ".join(registry_proposal.reason_codes)

        return PromotionRecord(
            promotion_id=promotion_id,
            model_version_id=model_version_id,
            previous_state=previous_state,
            new_state=new_state,
            promoted_by="research_orchestrator",
            promoted_at=datetime.utcnow(),
            promotion_reason=promotion_reason,
            approval_reference=None,
        )

    def _map_lifecycle_state_to_registry(self, lifecycle_state: LifecycleState) -> ModelLifecycleState:
        """Map lifecycle domain state to registry domain state."""
        mapping = {
            LifecycleState.GOVERNANCE_READY: ModelLifecycleState.VALIDATED,
            LifecycleState.APPROVED: ModelLifecycleState.PRODUCTION,
            LifecycleState.VALIDATED: ModelLifecycleState.VALIDATED,
            LifecycleState.PRODUCTION: ModelLifecycleState.PRODUCTION,
        }

        if lifecycle_state not in mapping:
            raise ValueError(f"No canonical mapping for lifecycle state: {lifecycle_state.value}")

        return mapping[lifecycle_state]

    def _compute_model_fingerprint(self, session: ResearchSession) -> str:
        """Compute deterministic model fingerprint from session state, referencing registry."""
        model_version_id = getattr(session, "model_version_id", None)
        if not model_version_id and hasattr(session, "config_snapshot"):
            for key, val in session.config_snapshot:
                if key == "model_version_id":
                    model_version_id = val
                    break

        if not model_version_id:
            raise ValueError("ResearchSession missing model_version_id in config_snapshot or properties")

        model_version = self.registry_service.get_version(model_version_id)
        if not model_version:
            raise KeyError(f"Model version '{model_version_id}' not found in ModelRegistryService")

        if hasattr(model_version, "composite_fingerprint"):
            fp = model_version.composite_fingerprint
            if hasattr(fp, "value"):
                return fp.value
            return str(fp)
        elif isinstance(model_version, dict) and "composite_fingerprint" in model_version:
            return model_version["composite_fingerprint"]

        raise ValueError(f"Model version '{model_version_id}' does not contain a valid composite_fingerprint")
