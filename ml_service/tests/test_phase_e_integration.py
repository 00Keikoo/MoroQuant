"""
Integration Tests for Research Session Orchestrator

Verifies:
- Session state transitions are immutable
- Pipeline stages execute in correct order
- Stage failures are captured
- Complete pipeline integration
"""

from dataclasses import replace
from ml_service.research.models import ResearchSession
from ml_service.research.orchestrator import (
    ResearchSessionOrchestrator,
    ResearchSessionStatus,
)


class SnapshotResult:
    """Mock snapshot result."""
    def __init__(self, dataset_version_id):
        self.snapshot_id = "snap-123"
        self.dataset_version_id = dataset_version_id
        self.file_hash = "abc123"


class MockSnapshotEngine:
    """Mock snapshot engine for testing."""
    def __init__(self, should_fail=False):
        self.should_fail = should_fail
        self.called = False

    def create_snapshot(self, dataset_version_id):
        self.called = True
        if self.should_fail:
            raise Exception("Snapshot failed")
        return SnapshotResult(dataset_version_id)


class ReplayResult:
    """Mock replay result."""
    def __init__(self):
        self.replay_id = "replay-123"
        self.dataset_fingerprint = "def456"
        self.execution_config = {}
        self.random_seed = 42


class MockReplayEngine:
    def __init__(self, should_fail=False):
        self.should_fail = should_fail
        self.called = False

    def replay(self, snapshot_id):
        self.called = True
        if self.should_fail:
            raise Exception("Replay failed")
        return ReplayResult()


class ExperimentResult:
    """Mock experiment result."""
    def __init__(self):
        self.experiment_id = "exp-123"
        self.replay_fingerprint = "ghi789"
        self.strategy_config = {}
        self.model_config = {}
        self.random_seed = 42


class MockExperimentEngine:
    def __init__(self, should_fail=False):
        self.should_fail = should_fail
        self.called = False

    def run_experiment(self, session):
        self.called = True
        if self.should_fail:
            raise Exception("Experiment failed")
        return ExperimentResult()


class EvaluationResult:
    """Mock evaluation result."""
    def __init__(self):
        self.evaluation_id = "eval-123"
        self.experiment_fingerprint = "jkl012"
        self.metrics_config = {}


class MockEvaluationEngine:
    def __init__(self, should_fail=False):
        self.should_fail = should_fail
        self.called = False

    def evaluate(self, session):
        self.called = True
        if self.should_fail:
            raise Exception("Evaluation failed")
        return EvaluationResult()


class MockReportingEngine:
    def __init__(self, should_fail=False):
        self.should_fail = should_fail
        self.called = False
        self.passed_evaluation_result = None

    def generate_report(self, evaluation_result):
        self.called = True
        self.passed_evaluation_result = evaluation_result
        if self.should_fail:
            raise Exception("Reporting failed")
        return "mock_report"


class MockBenchmarkEngine:
    def __init__(self, should_fail=False):
        self.should_fail = should_fail
        self.called = False
        self.passed_report = None

    def benchmark(self, report):
        self.called = True
        self.passed_report = report
        if self.should_fail:
            raise Exception("Benchmark failed")
        return "mock_benchmark_result"


class MockPromotionEngine:
    def __init__(self, should_fail=False):
        self.should_fail = should_fail
        self.called = False
        self.passed_benchmark_result = None

    def evaluate_promotion(self, benchmark_result):
        self.called = True
        self.passed_benchmark_result = benchmark_result
        if self.should_fail:
            raise Exception("Promotion failed")
        return "mock_registry_proposal"


class MockRegistryService:
    def __init__(self):
        self.called = False
        self.last_proposal = None

    def get_version(self, model_version_id):
        self.called = True
        class MockCompositeFingerprint:
            value = "a" * 64
        class MockModelVersion:
            composite_fingerprint = MockCompositeFingerprint()
        return MockModelVersion()


class MockRepository:
    def __init__(self):
        self.sessions = []

    def save_session(self, session):
        self.sessions.append(session)


def test_session_immutability():
    """Session state transitions must be immutable."""
    session = ResearchSession(
        session_id="test-001",
        status=ResearchSessionStatus.PENDING,
        dataset_version_id="v1",
    )

    updated = replace(session, status=ResearchSessionStatus.SNAPSHOT)

    assert session.status == ResearchSessionStatus.PENDING, "Original unchanged"
    assert updated.status == ResearchSessionStatus.SNAPSHOT, "New state created"
    assert session.session_id == updated.session_id, "Session ID preserved"


def test_pipeline_stage_order():
    """Pipeline stages must execute in correct order."""
    snapshot_engine = MockSnapshotEngine()
    replay_engine = MockReplayEngine()
    experiment_engine = MockExperimentEngine()
    evaluation_engine = MockEvaluationEngine()
    reporting_engine = MockReportingEngine()
    benchmark_engine = MockBenchmarkEngine()
    promotion_engine = MockPromotionEngine()
    registry_service = MockRegistryService()
    repository = MockRepository()

    orchestrator = ResearchSessionOrchestrator(
        snapshot_engine=snapshot_engine,
        replay_engine=replay_engine,
        experiment_engine=experiment_engine,
        evaluation_engine=evaluation_engine,
        reporting_engine=reporting_engine,
        benchmark_engine=benchmark_engine,
        promotion_engine=promotion_engine,
        registry_service=registry_service,
        repository=repository,
    )

    session = ResearchSession(
        session_id="test-002",
        status=ResearchSessionStatus.PENDING,
        dataset_version_id="v1",
        config_snapshot=(("model_version_id", "model_v1"),),
    )

    final_session = orchestrator.execute_session(session)

    assert snapshot_engine.called, "Snapshot stage executed"
    assert replay_engine.called, "Replay stage executed"
    assert experiment_engine.called, "Experiment stage executed"
    assert evaluation_engine.called, "Evaluation stage executed"
    assert reporting_engine.called, "Reporting stage executed"
    assert benchmark_engine.called, "Benchmark stage executed"
    assert promotion_engine.called, "Promotion stage executed"
    assert final_session.status == ResearchSessionStatus.COMPLETED

    # Assert data flow:
    assert reporting_engine.passed_evaluation_result is not None
    assert benchmark_engine.passed_report == "mock_report"
    assert promotion_engine.passed_benchmark_result == "mock_benchmark_result"
    assert registry_service.last_proposal == "mock_registry_proposal"


def test_snapshot_failure_stops_pipeline():
    """Snapshot failure must stop pipeline and set FAILED/SNAPSHOT status."""
    snapshot_engine = MockSnapshotEngine(should_fail=True)
    replay_engine = MockReplayEngine()
    experiment_engine = MockExperimentEngine()
    evaluation_engine = MockEvaluationEngine()
    reporting_engine = MockReportingEngine()
    benchmark_engine = MockBenchmarkEngine()
    promotion_engine = MockPromotionEngine()
    registry_service = MockRegistryService()
    repository = MockRepository()

    orchestrator = ResearchSessionOrchestrator(
        snapshot_engine=snapshot_engine,
        replay_engine=replay_engine,
        experiment_engine=experiment_engine,
        evaluation_engine=evaluation_engine,
        reporting_engine=reporting_engine,
        benchmark_engine=benchmark_engine,
        promotion_engine=promotion_engine,
        registry_service=registry_service,
        repository=repository,
    )

    session = ResearchSession(
        session_id="test-003",
        status=ResearchSessionStatus.PENDING,
        dataset_version_id="v1",
    )

    final_session = orchestrator.execute_session(session)

    assert final_session.status == ResearchSessionStatus.FAILED_SNAPSHOT
    assert snapshot_engine.called, "Snapshot stage attempted"
    assert not replay_engine.called, "Replay stage skipped after failure"
    assert not experiment_engine.called, "Experiment stage skipped after failure"


def test_experiment_failure_stops_pipeline():
    """Experiment failure must stop pipeline and set FAILED/EXPERIMENT status."""
    snapshot_engine = MockSnapshotEngine()
    replay_engine = MockReplayEngine()
    experiment_engine = MockExperimentEngine(should_fail=True)
    evaluation_engine = MockEvaluationEngine()
    reporting_engine = MockReportingEngine()
    benchmark_engine = MockBenchmarkEngine()
    promotion_engine = MockPromotionEngine()
    registry_service = MockRegistryService()
    repository = MockRepository()

    orchestrator = ResearchSessionOrchestrator(
        snapshot_engine=snapshot_engine,
        replay_engine=replay_engine,
        experiment_engine=experiment_engine,
        evaluation_engine=evaluation_engine,
        reporting_engine=reporting_engine,
        benchmark_engine=benchmark_engine,
        promotion_engine=promotion_engine,
        registry_service=registry_service,
        repository=repository,
    )

    session = ResearchSession(
        session_id="test-004",
        status=ResearchSessionStatus.PENDING,
        dataset_version_id="v1",
    )

    final_session = orchestrator.execute_session(session)

    assert final_session.status == ResearchSessionStatus.FAILED_EXPERIMENT
    assert snapshot_engine.called, "Snapshot executed"
    assert replay_engine.called, "Replay executed"
    assert experiment_engine.called, "Experiment attempted"
    assert not evaluation_engine.called, "Evaluation skipped after failure"


def test_session_persistence():
    """Session state must be persisted at each stage."""
    snapshot_engine = MockSnapshotEngine()
    replay_engine = MockReplayEngine()
    experiment_engine = MockExperimentEngine()
    evaluation_engine = MockEvaluationEngine()
    reporting_engine = MockReportingEngine()
    benchmark_engine = MockBenchmarkEngine()
    promotion_engine = MockPromotionEngine()
    registry_service = MockRegistryService()
    repository = MockRepository()

    orchestrator = ResearchSessionOrchestrator(
        snapshot_engine=snapshot_engine,
        replay_engine=replay_engine,
        experiment_engine=experiment_engine,
        evaluation_engine=evaluation_engine,
        reporting_engine=reporting_engine,
        benchmark_engine=benchmark_engine,
        promotion_engine=promotion_engine,
        registry_service=registry_service,
        repository=repository,
    )

    session = ResearchSession(
        session_id="test-005",
        status=ResearchSessionStatus.PENDING,
        dataset_version_id="v1",
        config_snapshot=(("model_version_id", "model_v1"),),
    )

    orchestrator.execute_session(session)

    assert len(repository.sessions) > 0, "Session states persisted"

    statuses = [s.status for s in repository.sessions]
    assert ResearchSessionStatus.SNAPSHOT in statuses, "Snapshot state recorded"
    assert ResearchSessionStatus.REPLAY in statuses, "Replay state recorded"
    assert ResearchSessionStatus.EXPERIMENT in statuses, "Experiment state recorded"
    assert ResearchSessionStatus.COMPLETED in statuses, "Completed state recorded"


if __name__ == "__main__":
    print("Running integration tests...")

    try:
        test_session_immutability()
        print("✓ Session state is immutable")
    except AssertionError as e:
        print(f"✗ {e}")
        exit(1)

    try:
        test_pipeline_stage_order()
        print("✓ Pipeline stages execute in correct order")
    except AssertionError as e:
        print(f"✗ {e}")
        exit(1)

    try:
        test_snapshot_failure_stops_pipeline()
        print("✓ Snapshot failure stops pipeline correctly")
    except AssertionError as e:
        print(f"✗ {e}")
        exit(1)

    try:
        test_experiment_failure_stops_pipeline()
        print("✓ Experiment failure stops pipeline correctly")
    except AssertionError as e:
        print(f"✗ {e}")
        exit(1)

    try:
        test_session_persistence()
        print("✓ Session state is persisted at each stage")
    except AssertionError as e:
        print(f"✗ {e}")
        exit(1)

    print("\nAll integration tests passed!")
