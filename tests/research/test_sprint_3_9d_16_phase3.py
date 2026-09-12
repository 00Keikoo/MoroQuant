"""Sprint 3.9D-16 Phase 3: Orchestrator + Registry Integration Tests

Tests proving the canonical architecture:
API -> artifact_path -> ModelIdentity -> ModelLifecycleRecord -> evaluate_with_benchmark()
-> RegistryProposal -> PromotionRecord -> record_promotion()
"""

import pytest
import uuid
from pathlib import Path
from datetime import datetime
from dataclasses import replace

from ml_service.research.orchestrator import ResearchSessionOrchestrator, ResearchSessionStatus
from ml_service.research.models import ResearchSession
from ml_service.research.promotion_engine.models import RegistryProposal, PromotionStatus
from ml_service.research.model_lifecycle.models import LifecycleState, ModelLifecycleRecord
from ml_service.research.model_identity.models import ModelIdentity
from ml_service.research.model_registry.model_types import (
    ModelLifecycleState,
    PromotionRecord,
    CompositeFingerprint,
)
from ml_service.research.model_registry.service import ModelRegistryService


class MockEngine:
    def __init__(self):
        self.calls = []

    def create_snapshot(self, dataset_version_id):
        self.calls.append(("create_snapshot", dataset_version_id))

        class Snap:
            def __init__(self):
                self.snapshot_id = "snap-test"
                self.dataset_version_id = dataset_version_id
                self.file_hash = "hash-test"
        return Snap()

    def replay(self, snapshot_id):
        self.calls.append(("replay", snapshot_id))

        class Rep:
            def __init__(self):
                self.replay_id = "replay-test"
                self.dataset_fingerprint = "fp-test"
                self.execution_config = {}
                self.random_seed = 42
        return Rep()

    def run_experiment(self, session):
        self.calls.append(("run_experiment", session.session_id))

        class Exp:
            def __init__(self):
                self.experiment_id = "exp-test"
                self.replay_fingerprint = "fp-test"
                self.strategy_config = {}
                self.model_config = {}
                self.random_seed = 42
        return Exp()

    def evaluate(self, session):
        self.calls.append(("evaluate", session.session_id))

        class Eval:
            def __init__(self):
                self.evaluation_id = "eval-test"
                self.experiment_fingerprint = "fp-test"
                self.metrics_config = {}
        return Eval()

    def generate_report(self, evaluation_result):
        self.calls.append(("generate_report", evaluation_result.evaluation_id))
        return "report-test"

    def benchmark(self, report):
        self.calls.append(("benchmark", report))

        class MockBenchmarkResult:
            def __init__(self):
                self.benchmark_id = "bench-test"
                self.winner = "exp-winner"
                self.ranking = ("exp-winner", "exp-baseline")
                self.scores = (("exp-winner", 1.5), ("exp-baseline", 0.8))
                self.metrics = (("average_cohort_score", 1.15), ("highest_score", 1.5))
                self.compared_experiments = ("exp-winner", "exp-baseline")
        return MockBenchmarkResult()


class MockPromotionEngine:
    def __init__(self, return_status=PromotionStatus.APPROVED):
        self.return_status = return_status
        self.last_call_args = None

    def evaluate(self, model_identity, lifecycle_record, audit_report):
        from ml_service.research.promotion_engine.models import PromotionScore

        self.last_call_args = {
            "model_identity": model_identity,
            "lifecycle_record": lifecycle_record,
            "audit_report": audit_report,
        }

        score = PromotionScore(
            model_id="test-model-id",
            validation_score=0.8,
            calibration_score=0.9,
            lifecycle_score=0.85,
            governance_score=0.95,
            total_score=0.8 * 0.30 + 0.9 * 0.20 + 0.85 * 0.30 + 0.95 * 0.20,
        )

        return RegistryProposal(
            model_id="test-model-id",
            symbol=model_identity.symbol,
            asset_class=model_identity.asset_class,
            current_state=lifecycle_record.current_state,
            proposed_state=LifecycleState.APPROVED,
            status=self.return_status,
            score=score,
            reason_codes=("governance_ready", "benchmark_passed"),
        )


class MockRegistryService(ModelRegistryService):
    def __init__(self, artifact_path_override=None):
        # Don't call super().__init__() to avoid requiring repositories
        self.promotions = []
        self.last_proposal = None
        self.artifact_path_override = artifact_path_override
        self.get_artifact_called = False

    def get_version(self, model_version_id):
        class ModelVersion:
            composite_fingerprint = CompositeFingerprint("a" * 64)
        return ModelVersion()

    def get_artifact(self, model_version_id):
        self.get_artifact_called = True
        class ArtifactMetadata:
            def __init__(self, path):
                self.bundle_path = path
        if self.artifact_path_override:
            return ArtifactMetadata(self.artifact_path_override)
        return ArtifactMetadata(f"/mock/artifacts/{model_version_id}")

    def record_promotion(self, record):
        record.validate()
        self.promotions.append(record)


class MockRepository:
    def __init__(self):
        self.sessions = {}

    def save_session(self, session):
        self.sessions[session.session_id] = session


class MockModelArtifactScanner:
    def __init__(self, model_directory):
        self.model_directory = model_directory

    def inspect(self, artifact_path):
        return ModelIdentity(
            artifact_path=str(artifact_path),
            symbol="BTCUSD",
            timeframe="1h",
            model_type="xgboost",
            asset_class="crypto",
            feature_count=10,
            feature_fingerprint="feature-fp-test",
            trained_at="2026-09-01T00:00:00Z",
            validation_available=True,
            calibration_available=True,
            sample_count=1000,
            lifecycle_status="GOVERNANCE_READY",
        )


@pytest.fixture
def mock_artifact_path(tmp_path):
    """Create a mock artifact directory with a valid model file."""
    artifact_dir = tmp_path / "artifacts"
    artifact_dir.mkdir()

    model_file = artifact_dir / "BTCUSD_1h_xgboost_crypto_20260901.pkl"

    import pickle
    model_data = {
        "metadata": {
            "feature_cols": ["feature1", "feature2"],
            "validation": {"sharpe": 1.5},
            "n_samples": 1000,
        }
    }
    with open(model_file, "wb") as f:
        pickle.dump(model_data, f)

    calibration_file = artifact_dir / "BTCUSD_1h_xgboost_crypto_20260901_calibration.pkl"
    with open(calibration_file, "wb") as f:
        pickle.dump({"calibration": "data"}, f)

    return str(model_file)


def create_test_orchestrator(promotion_engine):
    """Helper to create orchestrator with proper mock dependencies."""
    engine = MockEngine()
    registry = MockRegistryService()
    repository = MockRepository()

    def mock_evaluate_adapter(engine, benchmark, model_identity, lifecycle_record):
        return promotion_engine.evaluate(model_identity, lifecycle_record, {})

    def mock_lifecycle_factory():
        class MockLifecycleManager:
            def evaluate(self, model):
                return ModelLifecycleRecord(
                    artifact_path=model.artifact_path,
                    symbol=model.symbol,
                    asset_class=model.asset_class,
                    current_state=LifecycleState.GOVERNANCE_READY,
                    previous_state=None,
                    reason="evaluation complete",
                    timestamp="2026-09-04T00:00:00Z",
                )
        return MockLifecycleManager()

    return ResearchSessionOrchestrator(
        snapshot_engine=engine,
        replay_engine=engine,
        experiment_engine=engine,
        evaluation_engine=engine,
        reporting_engine=engine,
        benchmark_engine=engine,
        promotion_engine=promotion_engine,
        registry_service=registry,
        repository=repository,
        scanner_factory=MockModelArtifactScanner,
        lifecycle_manager_factory=mock_lifecycle_factory,
        evaluate_with_benchmark_func=mock_evaluate_adapter,
    ), engine, registry, repository


def test_artifact_path_resolution_from_registry(mock_artifact_path):
    """Test that artifact_path is resolved through RegistryManager.resolve_storage_path()."""
    promotion_engine = MockPromotionEngine()
    # Use mock registry that returns the actual artifact path
    engine = MockEngine()
    registry = MockRegistryService(artifact_path_override=mock_artifact_path)
    repository = MockRepository()

    def mock_evaluate_adapter(engine, benchmark, model_identity, lifecycle_record):
        return promotion_engine.evaluate(model_identity, lifecycle_record, {})

    def mock_lifecycle_factory():
        class MockLifecycleManager:
            def evaluate(self, model):
                return ModelLifecycleRecord(
                    artifact_path=model.artifact_path,
                    symbol=model.symbol,
                    asset_class=model.asset_class,
                    current_state=LifecycleState.GOVERNANCE_READY,
                    previous_state=None,
                    reason="evaluation complete",
                    timestamp="2026-09-04T00:00:00Z",
                )
        return MockLifecycleManager()

    orchestrator = ResearchSessionOrchestrator(
        snapshot_engine=engine,
        replay_engine=engine,
        experiment_engine=engine,
        evaluation_engine=engine,
        reporting_engine=engine,
        benchmark_engine=engine,
        promotion_engine=promotion_engine,
        registry_service=registry,
        repository=repository,
        scanner_factory=MockModelArtifactScanner,
        lifecycle_manager_factory=mock_lifecycle_factory,
        evaluate_with_benchmark_func=mock_evaluate_adapter,
    )

    session = ResearchSession(
        session_id="session-test",
        status=ResearchSessionStatus.PENDING,
        dataset_version_id="dataset-v1",
        config_snapshot=(
            ("model_version_id", "test-model-v1.0.0"),
        ),
    )

    final_session = orchestrator.execute_session(session)

    assert registry.get_artifact_called, "Registry.get_artifact() must be called to resolve artifact path"
    assert final_session.status == ResearchSessionStatus.COMPLETED
    assert final_session.model_fingerprint == "a" * 64


def test_promotion_uses_evaluate_with_benchmark(mock_artifact_path):
    """Test that promotion stage uses evaluate_with_benchmark(), not evaluate_promotion()."""
    engine = MockEngine()
    promotion_engine = MockPromotionEngine()
    registry = MockRegistryService(artifact_path_override=mock_artifact_path)
    repository = MockRepository()

    orchestrator = ResearchSessionOrchestrator(
        snapshot_engine=engine,
        replay_engine=engine,
        experiment_engine=engine,
        evaluation_engine=engine,
        reporting_engine=engine,
        benchmark_engine=engine,
        promotion_engine=promotion_engine,
        registry_service=registry,
        repository=repository,
    )

    session = ResearchSession(
        session_id="session-test",
        status=ResearchSessionStatus.PENDING,
        dataset_version_id="dataset-v1",
        config_snapshot=(
            ("model_version_id", "test-model-v1.0.0"),
        ),
    )

    final_session = orchestrator.execute_session(session)

    assert registry.get_artifact_called, "Registry.get_artifact() must be called to resolve artifact path"
    assert promotion_engine.last_call_args is not None
    assert isinstance(promotion_engine.last_call_args["model_identity"], ModelIdentity)
    assert isinstance(promotion_engine.last_call_args["lifecycle_record"], ModelLifecycleRecord)
    assert "audit_report" in promotion_engine.last_call_args


def test_model_identity_from_scanner(mock_artifact_path):
    """Test that ModelIdentity comes from ModelArtifactScanner.inspect()."""
    engine = MockEngine()
    promotion_engine = MockPromotionEngine()
    registry = MockRegistryService(artifact_path_override=mock_artifact_path)
    repository = MockRepository()

    orchestrator = ResearchSessionOrchestrator(
        snapshot_engine=engine,
        replay_engine=engine,
        experiment_engine=engine,
        evaluation_engine=engine,
        reporting_engine=engine,
        benchmark_engine=engine,
        promotion_engine=promotion_engine,
        registry_service=registry,
        repository=repository,
    )

    session = ResearchSession(
        session_id="session-test",
        status=ResearchSessionStatus.PENDING,
        dataset_version_id="dataset-v1",
        config_snapshot=(
            ("model_version_id", "test-model-v1.0.0"),
        ),
    )

    final_session = orchestrator.execute_session(session)

    assert registry.get_artifact_called, "Registry.get_artifact() must be called to resolve artifact path"
    model_identity = promotion_engine.last_call_args["model_identity"]
    assert model_identity.symbol == "BTCUSD"
    assert model_identity.asset_class == "crypto"
    assert model_identity.validation_available is True
    assert model_identity.calibration_available is True


def test_lifecycle_record_from_manager(mock_artifact_path):
    """Test that ModelLifecycleRecord comes from LifecycleManager.evaluate()."""
    engine = MockEngine()
    promotion_engine = MockPromotionEngine()
    registry = MockRegistryService(artifact_path_override=mock_artifact_path)
    repository = MockRepository()

    orchestrator = ResearchSessionOrchestrator(
        snapshot_engine=engine,
        replay_engine=engine,
        experiment_engine=engine,
        evaluation_engine=engine,
        reporting_engine=engine,
        benchmark_engine=engine,
        promotion_engine=promotion_engine,
        registry_service=registry,
        repository=repository,
    )

    session = ResearchSession(
        session_id="session-test",
        status=ResearchSessionStatus.PENDING,
        dataset_version_id="dataset-v1",
        config_snapshot=(
            ("model_version_id", "test-model-v1.0.0"),
        ),
    )

    final_session = orchestrator.execute_session(session)

    assert registry.get_artifact_called, "Registry.get_artifact() must be called to resolve artifact path"
    lifecycle_record = promotion_engine.last_call_args["lifecycle_record"]
    assert lifecycle_record.current_state == LifecycleState.GOVERNANCE_READY
    assert lifecycle_record.symbol == "BTCUSD"
    assert lifecycle_record.asset_class == "crypto"


def test_approved_promotion_records_to_registry(mock_artifact_path):
    """Test that APPROVED proposal constructs PromotionRecord and calls record_promotion()."""
    engine = MockEngine()
    promotion_engine = MockPromotionEngine(return_status=PromotionStatus.APPROVED)
    registry = MockRegistryService(artifact_path_override=mock_artifact_path)
    repository = MockRepository()

    orchestrator = ResearchSessionOrchestrator(
        snapshot_engine=engine,
        replay_engine=engine,
        experiment_engine=engine,
        evaluation_engine=engine,
        reporting_engine=engine,
        benchmark_engine=engine,
        promotion_engine=promotion_engine,
        registry_service=registry,
        repository=repository,
    )

    session = ResearchSession(
        session_id="session-test",
        status=ResearchSessionStatus.PENDING,
        dataset_version_id="dataset-v1",
        config_snapshot=(
            ("model_version_id", "test-model-v1.0.0"),
        ),
    )

    final_session = orchestrator.execute_session(session)

    assert registry.get_artifact_called, "Registry.get_artifact() must be called to resolve artifact path"
    assert len(registry.promotions) == 1

    promotion_record = registry.promotions[0]
    assert promotion_record.model_version_id == "test-model-v1.0.0"
    assert promotion_record.previous_state == ModelLifecycleState.VALIDATED
    assert promotion_record.new_state == ModelLifecycleState.PRODUCTION
    assert promotion_record.promoted_by == "research_orchestrator"
    assert promotion_record.promotion_reason == "governance_ready, benchmark_passed"
    assert promotion_record.approval_reference is None
    assert promotion_record.promotion_id.startswith("promo-")


def test_rejected_promotion_does_not_record(mock_artifact_path):
    """Test that REJECTED proposal completes session without calling record_promotion()."""
    engine = MockEngine()
    promotion_engine = MockPromotionEngine(return_status=PromotionStatus.REJECTED)
    registry = MockRegistryService(artifact_path_override=mock_artifact_path)
    repository = MockRepository()

    orchestrator = ResearchSessionOrchestrator(
        snapshot_engine=engine,
        replay_engine=engine,
        experiment_engine=engine,
        evaluation_engine=engine,
        reporting_engine=engine,
        benchmark_engine=engine,
        promotion_engine=promotion_engine,
        registry_service=registry,
        repository=repository,
    )

    session = ResearchSession(
        session_id="session-test",
        status=ResearchSessionStatus.PENDING,
        dataset_version_id="dataset-v1",
        config_snapshot=(
            ("model_version_id", "test-model-v1.0.0"),
        ),
    )

    final_session = orchestrator.execute_session(session)

    assert registry.get_artifact_called, "Registry.get_artifact() must be called to resolve artifact path"
    assert final_session.status == ResearchSessionStatus.COMPLETED
    assert len(registry.promotions) == 0


def test_lifecycle_state_mapping():
    """Test explicit lifecycle state mapping between domains."""
    engine = MockEngine()
    promotion_engine = MockPromotionEngine()
    registry = MockRegistryService()
    repository = MockRepository()

    orchestrator = ResearchSessionOrchestrator(
        snapshot_engine=engine,
        replay_engine=engine,
        experiment_engine=engine,
        evaluation_engine=engine,
        reporting_engine=engine,
        benchmark_engine=engine,
        promotion_engine=promotion_engine,
        registry_service=registry,
        repository=repository,
    )

    assert orchestrator._map_lifecycle_state_to_registry(LifecycleState.GOVERNANCE_READY) == ModelLifecycleState.VALIDATED
    assert orchestrator._map_lifecycle_state_to_registry(LifecycleState.APPROVED) == ModelLifecycleState.PRODUCTION
    assert orchestrator._map_lifecycle_state_to_registry(LifecycleState.VALIDATED) == ModelLifecycleState.VALIDATED
    assert orchestrator._map_lifecycle_state_to_registry(LifecycleState.PRODUCTION) == ModelLifecycleState.PRODUCTION


def test_unknown_lifecycle_state_fails(mock_artifact_path):
    """Test that unknown lifecycle state fails explicitly without silent fallback."""
    engine = MockEngine()
    promotion_engine = MockPromotionEngine()
    registry = MockRegistryService()
    repository = MockRepository()

    orchestrator = ResearchSessionOrchestrator(
        snapshot_engine=engine,
        replay_engine=engine,
        experiment_engine=engine,
        evaluation_engine=engine,
        reporting_engine=engine,
        benchmark_engine=engine,
        promotion_engine=promotion_engine,
        registry_service=registry,
        repository=repository,
    )

    with pytest.raises(ValueError, match="No canonical mapping for lifecycle state"):
        orchestrator._map_lifecycle_state_to_registry(LifecycleState.DISCOVERED)


def test_registry_failure_marks_session_failed(mock_artifact_path):
    """Test that record_promotion() exception marks session as FAILED/PROMOTION."""
    engine = MockEngine()
    promotion_engine = MockPromotionEngine(return_status=PromotionStatus.APPROVED)

    class FailingRegistry:
        def get_version(self, model_version_id):
            class ModelVersion:
                composite_fingerprint = CompositeFingerprint("a" * 64)
            return ModelVersion()

        def get_artifact(self, model_version_id):
            class ArtifactMetadata:
                def __init__(self, path):
                    self.bundle_path = path
            return ArtifactMetadata(mock_artifact_path)

        def record_promotion(self, record):
            raise RuntimeError("Registry service unavailable")

    registry = FailingRegistry()
    repository = MockRepository()

    orchestrator = ResearchSessionOrchestrator(
        snapshot_engine=engine,
        replay_engine=engine,
        experiment_engine=engine,
        evaluation_engine=engine,
        reporting_engine=engine,
        benchmark_engine=engine,
        promotion_engine=promotion_engine,
        registry_service=registry,
        repository=repository,
    )

    session = ResearchSession(
        session_id="session-test",
        status=ResearchSessionStatus.PENDING,
        dataset_version_id="dataset-v1",
        config_snapshot=(
            ("model_version_id", "test-model-v1.0.0"),
        ),
    )

    final_session = orchestrator.execute_session(session)

    assert final_session.status == ResearchSessionStatus.FAILED_PROMOTION


def test_canonical_fingerprint_path_unchanged(mock_artifact_path):
    """Test that model_fingerprint comes from canonical Registry path."""
    engine = MockEngine()
    promotion_engine = MockPromotionEngine()
    registry = MockRegistryService(artifact_path_override=mock_artifact_path)
    repository = MockRepository()

    orchestrator = ResearchSessionOrchestrator(
        snapshot_engine=engine,
        replay_engine=engine,
        experiment_engine=engine,
        evaluation_engine=engine,
        reporting_engine=engine,
        benchmark_engine=engine,
        promotion_engine=promotion_engine,
        registry_service=registry,
        repository=repository,
    )

    session = ResearchSession(
        session_id="session-test",
        status=ResearchSessionStatus.PENDING,
        dataset_version_id="dataset-v1",
        config_snapshot=(
            ("model_version_id", "test-model-v1.0.0"),
        ),
    )

    final_session = orchestrator.execute_session(session)

    assert registry.get_artifact_called, "Registry.get_artifact() must be called to resolve artifact path"
    assert final_session.model_fingerprint == "a" * 64


def test_missing_model_version_id_fails(mock_artifact_path):
    """Test that missing model_version_id fails explicitly."""
    engine = MockEngine()
    promotion_engine = MockPromotionEngine()
    registry = MockRegistryService(artifact_path_override=mock_artifact_path)
    repository = MockRepository()

    orchestrator = ResearchSessionOrchestrator(
        snapshot_engine=engine,
        replay_engine=engine,
        experiment_engine=engine,
        evaluation_engine=engine,
        reporting_engine=engine,
        benchmark_engine=engine,
        promotion_engine=promotion_engine,
        registry_service=registry,
        repository=repository,
    )

    session = ResearchSession(
        session_id="session-test",
        status=ResearchSessionStatus.PENDING,
        dataset_version_id="dataset-v1",
        config_snapshot=(),
    )

    final_session = orchestrator.execute_session(session)

    assert final_session.status == ResearchSessionStatus.FAILED_PROMOTION
