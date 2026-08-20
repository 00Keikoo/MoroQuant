from unittest.mock import Mock
from ml_service.research import provenance
from ml_service.research.orchestrator import ResearchSessionOrchestrator
from ml_service.research.models import ResearchSession


def test_orchestrator_model_fingerprint_registry_identity():
    """Verify that same model artifact (registered in ModelRegistryService)
    produces same fingerprint, and different produces different.
    """
    registry_service = Mock()

    mv1 = Mock()
    mv1.composite_fingerprint = Mock()
    mv1.composite_fingerprint.value = "a" * 64

    mv2 = Mock()
    mv2.composite_fingerprint = Mock()
    mv2.composite_fingerprint.value = "b" * 64

    def get_version(mv_id):
        if mv_id == "model_v1":
            return mv1
        if mv_id == "model_v2":
            return mv2
        return None
    registry_service.get_version.side_effect = get_version

    orchestrator = ResearchSessionOrchestrator(
        snapshot_engine=Mock(),
        replay_engine=Mock(),
        experiment_engine=Mock(),
        evaluation_engine=Mock(),
        reporting_engine=Mock(),
        benchmark_engine=Mock(),
        promotion_engine=Mock(),
        registry_service=registry_service,
        repository=Mock()
    )

    session_a1 = ResearchSession(
        session_id="session_a1",
        status="PENDING",
        config_snapshot=(("model_version_id", "model_v1"),)
    )
    session_a2 = ResearchSession(
        session_id="session_a2",
        status="PENDING",
        config_snapshot=(("model_version_id", "model_v1"),)
    )
    session_b = ResearchSession(
        session_id="session_b",
        status="PENDING",
        config_snapshot=(("model_version_id", "model_v2"),)
    )

    fp_a1 = orchestrator._compute_model_fingerprint(session_a1)
    fp_a2 = orchestrator._compute_model_fingerprint(session_a2)
    fp_b = orchestrator._compute_model_fingerprint(session_b)

    assert fp_a1 == fp_a2, "Same model version must produce identical fingerprints"
    assert fp_a1 == "a" * 64, "Must match whitelisted CompositeFingerprint value"
    assert fp_a1 != fp_b, "Different model version must produce different fingerprints"
    assert fp_b == "b" * 64, "Must match whitelisted CompositeFingerprint value"


def test_dataset_fingerprint_deterministic():
    """Dataset fingerprint must be deterministic."""
    fp1 = provenance.dataset_fingerprint(
        dataset_version_id="v1",
        snapshot_id="snap1",
        file_hash="abc123",
    )
    fp2 = provenance.dataset_fingerprint(
        dataset_version_id="v1",
        snapshot_id="snap1",
        file_hash="abc123",
    )
    assert fp1 == fp2, "Same inputs must produce same fingerprint"

    fp3 = provenance.dataset_fingerprint(
        dataset_version_id="v1",
        snapshot_id="snap1",
        file_hash="xyz789",
    )
    assert fp1 != fp3, "Different inputs must produce different fingerprints"


def test_replay_fingerprint_deterministic():
    """Replay fingerprint must be deterministic."""
    fp1 = provenance.replay_fingerprint(
        dataset_fingerprint="abc123",
        execution_config={"slippage": 5.0, "commission": 0.1},
        random_seed=42,
    )
    fp2 = provenance.replay_fingerprint(
        dataset_fingerprint="abc123",
        execution_config={"slippage": 5.0, "commission": 0.1},
        random_seed=42,
    )
    assert fp1 == fp2, "Same inputs must produce same fingerprint"

    fp3 = provenance.replay_fingerprint(
        dataset_fingerprint="abc123",
        execution_config={"slippage": 5.0, "commission": 0.1},
        random_seed=99,
    )
    assert fp1 != fp3, "Different seed must produce different fingerprint"


def test_experiment_fingerprint_deterministic():
    """Experiment fingerprint must be deterministic."""
    fp1 = provenance.experiment_fingerprint(
        replay_fingerprint="abc123",
        strategy_config={"threshold": 0.5},
        model_config={"depth": 5},
        random_seed=42,
    )
    fp2 = provenance.experiment_fingerprint(
        replay_fingerprint="abc123",
        strategy_config={"threshold": 0.5},
        model_config={"depth": 5},
        random_seed=42,
    )
    assert fp1 == fp2, "Same inputs must produce same fingerprint"


def test_evaluation_fingerprint_deterministic():
    """Evaluation fingerprint must be deterministic."""
    fp1 = provenance.evaluation_fingerprint(
        experiment_fingerprint="abc123",
        metrics_config={"metrics": ["sharpe", "sortino"]},
    )
    fp2 = provenance.evaluation_fingerprint(
        experiment_fingerprint="abc123",
        metrics_config={"metrics": ["sharpe", "sortino"]},
    )
    assert fp1 == fp2, "Same inputs must produce same fingerprint"


def test_model_fingerprint_deterministic():
    """Model fingerprint must be deterministic."""
    fp1 = provenance.model_fingerprint(
        dataset_fingerprint="abc",
        feature_fingerprint="def",
        experiment_fingerprint="ghi",
        training_config={"epochs": 100},
        random_seed=42,
    )
    fp2 = provenance.model_fingerprint(
        dataset_fingerprint="abc",
        feature_fingerprint="def",
        experiment_fingerprint="ghi",
        training_config={"epochs": 100},
        random_seed=42,
    )
    assert fp1 == fp2, "Same inputs must produce same fingerprint"


def test_orchestrator_model_fingerprint_no_local_fallback():
    """Verify that if the model registry cannot resolve the requested model
    version, the orchestrator raises an error and does not compute a fallback.
    """
    import pytest
    registry_service = Mock()
    registry_service.get_version.return_value = None  # Registry cannot resolve it

    orchestrator = ResearchSessionOrchestrator(
        snapshot_engine=Mock(),
        replay_engine=Mock(),
        experiment_engine=Mock(),
        evaluation_engine=Mock(),
        reporting_engine=Mock(),
        benchmark_engine=Mock(),
        promotion_engine=Mock(),
        registry_service=registry_service,
        repository=Mock()
    )

    session = ResearchSession(
        session_id="session_err",
        status="PENDING",
        config_snapshot=(("model_version_id", "missing_version"),)
    )

    with pytest.raises(KeyError):
        orchestrator._compute_model_fingerprint(session)


def test_fingerprint_format():
    """Fingerprints must be valid SHA256 hex strings."""
    fp = provenance.dataset_fingerprint("v1", "snap1", "hash1")
    assert len(fp) == 64, "SHA256 produces 64 hex characters"
    assert all(c in "0123456789abcdef" for c in fp), "Must be valid hex"


if __name__ == "__main__":
    print("Running determinism tests...")

    try:
        test_dataset_fingerprint_deterministic()
        print("✓ Dataset fingerprint is deterministic")
    except AssertionError as e:
        print(f"✗ {e}")
        exit(1)

    try:
        test_replay_fingerprint_deterministic()
        print("✓ Replay fingerprint is deterministic")
    except AssertionError as e:
        print(f"✗ {e}")
        exit(1)

    try:
        test_experiment_fingerprint_deterministic()
        print("✓ Experiment fingerprint is deterministic")
    except AssertionError as e:
        print(f"✗ {e}")
        exit(1)

    try:
        test_evaluation_fingerprint_deterministic()
        print("✓ Evaluation fingerprint is deterministic")
    except AssertionError as e:
        print(f"✗ {e}")
        exit(1)

    try:
        test_model_fingerprint_deterministic()
        print("✓ Model fingerprint is deterministic")
    except AssertionError as e:
        print(f"✗ {e}")
        exit(1)

    try:
        test_fingerprint_format()
        print("✓ Fingerprint format is valid")
    except AssertionError as e:
        print(f"✗ {e}")
        exit(1)

    print("\nAll determinism tests passed!")
