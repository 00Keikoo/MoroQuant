"""Orchestrator Integration Test for SQLite Repository

Tests that the canonical ResearchSessionOrchestrator can persist sessions
through lifecycle transitions using the SQLite repository.
"""

import tempfile
from pathlib import Path
from datetime import datetime
from typing import Any
from dataclasses import dataclass

from ml_service.bootstrap.research_database import bootstrap_research_tables
from ml_service.research.research_repository import ResearchRepository
from ml_service.research.models import ResearchSession
from ml_service.research.orchestrator import ResearchSessionOrchestrator


@dataclass
class MockSnapshotResult:
    """Mock snapshot engine result."""
    snapshot_id: str
    dataset_version_id: str
    fingerprint: str


@dataclass
class MockReplayResult:
    """Mock replay engine result."""
    replay_id: str
    fingerprint: str


@dataclass
class MockExperimentResult:
    """Mock experiment engine result."""
    experiment_id: str
    fingerprint: str


@dataclass
class MockEvaluationResult:
    """Mock evaluation engine result."""
    evaluation_id: str
    fingerprint: str


@dataclass
class MockReport:
    """Mock report."""
    report_id: str


@dataclass
class MockBenchmarkResult:
    """Mock benchmark result."""
    benchmark_id: str


@dataclass
class MockRegistryProposal:
    """Mock registry proposal."""
    proposal_id: str


class MockSnapshotEngine:
    """Mock snapshot engine for orchestrator testing."""
    def create_snapshot(self, dataset_version_id: str) -> MockSnapshotResult:
        return MockSnapshotResult(
            snapshot_id=f"snap_{dataset_version_id}",
            dataset_version_id=dataset_version_id,
            fingerprint=f"fp_dataset_{dataset_version_id}"
        )


class MockReplayEngine:
    """Mock replay engine for orchestrator testing."""
    def replay(self, snapshot_id: str) -> MockReplayResult:
        return MockReplayResult(
            replay_id=f"replay_{snapshot_id}",
            fingerprint=f"fp_replay_{snapshot_id}"
        )


class MockExperimentEngine:
    """Mock experiment engine for orchestrator testing."""
    def run_experiment(self, session: ResearchSession) -> MockExperimentResult:
        return MockExperimentResult(
            experiment_id=f"exp_{session.session_id}",
            fingerprint=f"fp_experiment_{session.session_id}"
        )


class MockEvaluationEngine:
    """Mock evaluation engine for orchestrator testing."""
    def evaluate(self, session: ResearchSession) -> MockEvaluationResult:
        return MockEvaluationResult(
            evaluation_id=f"eval_{session.session_id}",
            fingerprint=f"fp_evaluation_{session.session_id}"
        )


class MockReportingEngine:
    """Mock reporting engine for orchestrator testing."""
    def generate_report(self, evaluation_result: Any) -> MockReport:
        return MockReport(report_id=f"report_{evaluation_result.evaluation_id}")


class MockBenchmarkEngine:
    """Mock benchmark engine for orchestrator testing."""
    def benchmark(self, report: Any) -> MockBenchmarkResult:
        return MockBenchmarkResult(benchmark_id=f"benchmark_{report.report_id}")


class MockPromotionEngine:
    """Mock promotion engine for orchestrator testing."""
    def evaluate_promotion(self, benchmark_result: Any) -> MockRegistryProposal:
        return MockRegistryProposal(proposal_id=f"proposal_{benchmark_result.benchmark_id}")


@dataclass
class MockModelVersion:
    """Mock model version with composite fingerprint."""
    composite_fingerprint: str


class MockRegistryService:
    """Mock registry service for orchestrator testing."""
    def __init__(self):
        self.last_proposal = None

    def get_version(self, model_version_id: str):
        """Return mock model version."""
        return MockModelVersion(composite_fingerprint=f"fp_model_{model_version_id}")

    def register(self, proposal: Any) -> None:
        pass


class TestOrchestratorPersistenceIntegration:
    """Test real orchestrator with SQLite repository persistence."""

    def test_orchestrator_executes_full_lifecycle_with_sqlite_persistence(self):
        """Verify the canonical orchestrator persists session state through complete lifecycle."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "test.db")
            bootstrap_research_tables(db_path)

            repository = ResearchRepository(db_path)

            orchestrator = ResearchSessionOrchestrator(
                snapshot_engine=MockSnapshotEngine(),
                replay_engine=MockReplayEngine(),
                experiment_engine=MockExperimentEngine(),
                evaluation_engine=MockEvaluationEngine(),
                reporting_engine=MockReportingEngine(),
                benchmark_engine=MockBenchmarkEngine(),
                promotion_engine=MockPromotionEngine(),
                registry_service=MockRegistryService(),
                repository=repository,
            )

            initial_session = ResearchSession(
                session_id="orchestrator_integration_001",
                status="PENDING",
                config_snapshot=(("symbol", "EURUSD"), ("timeframe", "1h"), ("model_version_id", "model_v1")),
                dataset_version_id="ds_001",
                created_at=datetime.utcnow().isoformat()
            )

            final_session = orchestrator.execute_session(initial_session)

            assert final_session.status == "COMPLETED"
            assert final_session.completed_at is not None

            fresh_repository = ResearchRepository(db_path)
            reloaded_session = fresh_repository.get_session("orchestrator_integration_001")

            assert reloaded_session.session_id == "orchestrator_integration_001"
            assert reloaded_session.status == "COMPLETED"
            assert reloaded_session.dataset_fingerprint is not None
            assert reloaded_session.replay_fingerprint is not None
            assert reloaded_session.experiment_fingerprint is not None
            assert reloaded_session.evaluation_fingerprint is not None
            assert reloaded_session.completed_at is not None

    def test_orchestrator_persists_failed_state(self):
        """Verify orchestrator persists FAILED states when engines raise exceptions."""

        class FailingExperimentEngine:
            """Mock engine that always fails."""
            def run_experiment(self, session: ResearchSession):
                raise RuntimeError("Experiment failed")

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "test.db")
            bootstrap_research_tables(db_path)

            repository = ResearchRepository(db_path)

            orchestrator = ResearchSessionOrchestrator(
                snapshot_engine=MockSnapshotEngine(),
                replay_engine=MockReplayEngine(),
                experiment_engine=FailingExperimentEngine(),
                evaluation_engine=MockEvaluationEngine(),
                reporting_engine=MockReportingEngine(),
                benchmark_engine=MockBenchmarkEngine(),
                promotion_engine=MockPromotionEngine(),
                registry_service=MockRegistryService(),
                repository=repository,
            )

            initial_session = ResearchSession(
                session_id="failed_session_001",
                status="PENDING",
                config_snapshot=(("symbol", "GBPUSD"), ("model_version_id", "model_v2")),
                dataset_version_id="ds_002",
                created_at=datetime.utcnow().isoformat()
            )

            final_session = orchestrator.execute_session(initial_session)

            assert final_session.status == "FAILED/EXPERIMENT"

            fresh_repository = ResearchRepository(db_path)
            reloaded_session = fresh_repository.get_session("failed_session_001")

            assert reloaded_session.status == "FAILED/EXPERIMENT"
            assert reloaded_session.dataset_fingerprint is not None
            assert reloaded_session.replay_fingerprint is not None
