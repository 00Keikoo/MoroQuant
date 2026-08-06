import pytest
from datetime import datetime
from ml_service.research.models import DatasetSnapshot
from ml_service.research.snapshot_engine.types import Snapshot
from ml_service.research.strategy.features.feature_context_service import FeatureContextService
from ml_service.research.strategy.features.context import FeatureContext
from ml_service.research.strategy.features.interfaces import FeatureBuilder
from ml_service.research.strategy.models import FeatureSnapshot
from ml_service.research.strategy.inference.interfaces import ModelInferenceBackend
from ml_service.research.strategy.inference.models import Prediction, ModelMetadata
from ml_service.research.strategy.inference.adapter import MLInferenceAdapter
from ml_service.research.strategy.signal.generator import DefaultSignalGenerator
from ml_service.research.experiment.tracker import DefaultExperimentTracker
from ml_service.research.runner import ResearchRunner

class MockFeatureBuilder(FeatureBuilder):
    def initialize(self, symbol: str) -> FeatureContext:
        return FeatureContext(symbol=symbol, timestamp="2026-07-06T22:00:00Z", window=())
    def update(self, context: FeatureContext, snapshot) -> FeatureContext:
        return FeatureContext(symbol=context.symbol, timestamp=snapshot.timestamp.isoformat(), window=context.window + (snapshot,))
    def build(self, context: FeatureContext) -> FeatureSnapshot:
        return FeatureSnapshot(timestamp=context.timestamp, features=(("feature1", 12.34),), schema_version="1.0.0")

class MockInferenceBackend(ModelInferenceBackend):
    def load_model(self, bundle_path: str) -> None:
        pass
    def predict(self, features: FeatureSnapshot, model_version_id: str) -> Prediction:
        return Prediction(
            timestamp=features.timestamp,
            model_version_id=model_version_id,
            direction="LONG",
            probability=0.75,
            outputs=(("prob", 0.75),)
        )

@pytest.fixture
def runner_setup():
    builder = MockFeatureBuilder()
    feature_service = FeatureContextService(builder)

    # Setup ML Inference Adapter
    backend = MockInferenceBackend()
    metadata = ModelMetadata(
        model_id="test-model",
        model_version_id="model-v1",
        framework="xgboost",
        feature_schema=("feature1",),
        fingerprint="a" * 64
    )
    
    # Mock model registry service or create model version for adapter validation
    from unittest.mock import MagicMock
    from ml_service.research.model_registry.model_types import ModelVersion, ModelLifecycleState, CompositeFingerprint
    
    mock_model_version = ModelVersion(
        model_version_id="model-v1",
        model_id="test-model",
        version="1.0.0",
        lifecycle_state=ModelLifecycleState.VALIDATED,
        composite_fingerprint=CompositeFingerprint("a" * 64),
        created_at=datetime.utcnow()
    )
    
    # Registry needs to mock get_version and get_artifact
    registry = MagicMock()
    registry.get_version.return_value = mock_model_version
    
    from ml_service.research.model_registry.model_types import ArtifactMetadata
    mock_artifact = ArtifactMetadata(
        model_version_id="model-v1",
        bundle_path="/tmp/bundle",
        manifest_checksum="a" * 64,
        size_bytes=100,
        permissions="444"
    )
    registry.get_artifact.return_value = mock_artifact
    
    inference_adapter = MLInferenceAdapter(registry, backends={"xgboost": backend})
    
    signal_generator = DefaultSignalGenerator(entry_threshold=0.6, exit_threshold=0.5)
    tracker = DefaultExperimentTracker()

    runner = ResearchRunner(
        feature_service=feature_service,
        inference_adapter=inference_adapter,
        signal_generator=signal_generator,
        tracker=tracker
    )
    
    dataset_snapshot = DatasetSnapshot(
        dataset_version_id="DS_1.0.0",
        fingerprint="b" * 64,
        file_path="/tmp/ds_1.parquet",
        is_frozen=True,
        created_at="2026-07-06T22:00:00Z"
    )

    snapshot = Snapshot(
        snapshot_id="snap-1",
        timestamp="2026-07-06T22:00:00Z",
        trades=[
            {"signal_id": "sig-1", "direction": "LONG"}
        ],
        signals=[
            {
                "id": "sig-1",
                "symbol": "BTCUSDT",
                "prob_long": 0.75,
                "prob_short": 0.25,
                "prob_neutral": 0.0,
                "regime": "TRENDING",
                "features": {"f1": 1.0}
            }
        ]
    )

    config = {
        "run_id": "run-1",
        "experiment_id": "exp-1",
        "model_version_id": "model-v1",
        "strategy_id": "strat-1",
        "threshold_long": 0.5,
        "threshold_short": 0.5,
        "snapshot": snapshot
    }

    return runner, dataset_snapshot, config

def test_deterministic_replay(runner_setup):
    """Verify that executing the runner twice with the exact same configuration yields identical replay metrics."""
    runner, dataset_snapshot, config = runner_setup
    
    res1 = runner.run(dataset_snapshot, config)
    
    # Re-initialize context state and tracker for second run
    runner.feature_service.reset()
    runner.tracker._runs.clear()
    res2 = runner.run(dataset_snapshot, config)
    
    assert res1.replay_result.signal_reproduction_rate == res2.replay_result.signal_reproduction_rate
    assert res1.replay_result.consistency_score == res2.replay_result.consistency_score
    assert len(res1.replay_result.decisions) == len(res2.replay_result.decisions)

def test_pipeline_ordering(runner_setup):
    """Verify pipeline step sequences and data flows correctly."""
    runner, dataset_snapshot, config = runner_setup
    
    res = runner.run(dataset_snapshot, config)
    
    # 1. DatasetSnapshot metadata matched
    assert res.dataset_snapshot_id == dataset_snapshot.dataset_version_id
    
    # 2. Replay generated decisions
    assert len(res.replay_result.decisions) == 1
    assert res.replay_result.decisions[0]["signal_id"] == "sig-1"
    
    # 3. Feature snapshot constructed from FeatureContext
    assert res.feature_snapshot.schema_version == "1.0.0"
    
    # 4. Inference yielded prediction
    assert res.inference_result.prediction.model_version_id == "model-v1"
    
    # 5. Signal generator ran over prediction
    assert len(res.signals) == 1
    assert res.signals[0].confidence == 0.75
    
    # 6. Evaluation completed & logged
    assert res.evaluation_result.experiment_id == "exp-1"
    assert res.evaluation_result.best_strategy_id == "strat-1"
    
    # 7. ExperimentTracker recorded the run
    tracked_run = runner.tracker.get_run("exp-1")
    assert tracked_run is not None
    assert tracked_run.model_version_id == "model-v1"

def test_dependency_isolation(runner_setup):
    """Verify that no database operations are invoked during execution (ADR-024 compliance)."""
    import inspect
    from ml_service.research.runner import runner as runner_mod
    
    source = inspect.getsource(runner_mod)
    assert "sqlite" not in source.lower()
    assert "db" not in source.lower()
    assert "execute(" not in source.lower()
    assert "insert into" not in source.lower()

def test_experiment_fingerprint_consistency(runner_setup):
    """Verify that experiment run identity fingerprints are reproducible and consistent."""
    runner, dataset_snapshot, config = runner_setup
    res = runner.run(dataset_snapshot, config)
    
    identity1 = res.experiment_run.get_identity()
    identity2 = res.experiment_run.get_identity()
    
    assert identity1 == identity2
    assert len(identity1) == 64
