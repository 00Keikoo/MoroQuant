import pytest
from dataclasses import FrozenInstanceError
import json

from ml_service.research.models import (
    DatasetSnapshot,
    FeatureSnapshot,
    ResearchRun,
    ResearchExperiment,
    ResearchSession
)

def test_dataset_snapshot_lifecycle():
    # Construction
    snapshot = DatasetSnapshot(
        dataset_version_id="DS_1.0.0",
        fingerprint="abcd1234hash",
        file_path="/storage/datasets/DS_1.0.0.parquet",
        is_frozen=True,
        created_at="2026-07-31T12:00:00Z"
    )

    # Type verification
    assert snapshot.dataset_version_id == "DS_1.0.0"
    assert snapshot.is_frozen is True

    # Immutability
    with pytest.raises(FrozenInstanceError):
        snapshot.is_frozen = False  # type: ignore

    # Serialization
    d = snapshot.to_dict()
    assert d == {
        "dataset_version_id": "DS_1.0.0",
        "fingerprint": "abcd1234hash",
        "file_path": "/storage/datasets/DS_1.0.0.parquet",
        "is_frozen": True,
        "created_at": "2026-07-31T12:00:00Z"
    }

    # Equality & Hashing
    snapshot2 = DatasetSnapshot(
        dataset_version_id="DS_1.0.0",
        fingerprint="abcd1234hash",
        file_path="/storage/datasets/DS_1.0.0.parquet",
        is_frozen=True,
        created_at="2026-07-31T12:00:00Z"
    )
    assert snapshot == snapshot2
    assert hash(snapshot) == hash(snapshot2)
    assert {snapshot, snapshot2} == {snapshot}


def test_feature_snapshot_lifecycle():
    snapshot = FeatureSnapshot(
        feature_dataset_id="fds_v1_ds_1",
        source_dataset_id="DS_1.0.0",
        fingerprint="xyz5678hash",
        file_path="/storage/features/fds_v1_ds_1.parquet",
        is_frozen=True,
        created_at="2026-07-31T12:05:00Z"
    )

    assert snapshot.feature_dataset_id == "fds_v1_ds_1"

    # Immutability
    with pytest.raises(FrozenInstanceError):
        snapshot.fingerprint = "mutated"  # type: ignore

    # Serialization
    d = snapshot.to_dict()
    assert d == {
        "feature_dataset_id": "fds_v1_ds_1",
        "source_dataset_id": "DS_1.0.0",
        "fingerprint": "xyz5678hash",
        "file_path": "/storage/features/fds_v1_ds_1.parquet",
        "is_frozen": True,
        "created_at": "2026-07-31T12:05:00Z"
    }


def test_research_run_deterministic_ordering_and_defaults():
    # Empty collections test
    run_empty = ResearchRun(
        run_id="RUN_001",
        experiment_id="EXP_001",
        status="COMPLETED"
    )
    assert run_empty.hyperparameters == ()
    assert run_empty.metrics == ()
    assert run_empty.model_binary_path is None

    # Deterministic sorting in to_dict
    hparams = (
        ("learning_rate", 0.01),
        ("batch_size", 32),
        ("epochs", 10)
    )
    metrics = (
        ("sharpe", 1.8),
        ("ece", 0.03),
        ("brier", 0.15)
    )
    run = ResearchRun(
        run_id="RUN_001",
        experiment_id="EXP_001",
        status="COMPLETED",
        hyperparameters=hparams,
        metrics=metrics,
        model_binary_path="/storage/models/m1.json",
        created_at="2026-07-31T12:10:00Z",
        completed_at="2026-07-31T12:15:00Z"
    )

    serialized = run.to_dict()
    # verify hyperparameters are sorted alphabetically by key ("batch_size", "epochs", "learning_rate")
    assert serialized["hyperparameters"] == [
        ["batch_size", 32],
        ["epochs", 10],
        ["learning_rate", 0.01]
    ]
    # verify metrics are sorted alphabetically by key ("brier", "ece", "sharpe")
    assert serialized["metrics"] == [
        ["brier", 0.15],
        ["ece", 0.03],
        ["sharpe", 1.8]
    ]


def test_nested_models_and_session_serialization():
    # Construct nested structure: Run -> Experiment -> Session
    run_b = ResearchRun(
        run_id="RUN_B",
        experiment_id="EXP_01",
        status="COMPLETED",
        metrics=(("sharpe", 1.9),)
    )
    run_a = ResearchRun(
        run_id="RUN_A",
        experiment_id="EXP_01",
        status="COMPLETED",
        metrics=(("sharpe", 1.5),)
    )

    exp_2 = ResearchExperiment(
        experiment_id="EXP_02",
        session_id="SESS_01",
        status="ACTIVE",
        hypothesis_config=(("model_type", "xgboost"),)
    )
    exp_1 = ResearchExperiment(
        experiment_id="EXP_01",
        session_id="SESS_01",
        status="EVALUATED",
        hypothesis_config=(("model_type", "lstm"),),
        runs=(run_b, run_a)  # unsorted on purpose
    )

    session = ResearchSession(
        session_id="SESS_01",
        status="COMPLETED",
        config_snapshot=(("symbol", "BTCUSDT"), ("timeframe", "1h")),
        experiments=(exp_2, exp_1)  # unsorted on purpose
    )

    # Immutability validation at all levels
    with pytest.raises(FrozenInstanceError):
        session.experiments[1].runs[0].status = "FAILED"  # type: ignore

    # Verify deterministic sorting of runs and experiments in serialized output
    d = session.to_dict()
    
    # 1. Config snapshot should be sorted alphabetically: symbol, timeframe
    assert d["config_snapshot"] == [
        ["symbol", "BTCUSDT"],
        ["timeframe", "1h"]
    ]

    # 2. Experiments should be sorted by experiment_id: EXP_01, EXP_02
    assert d["experiments"][0]["experiment_id"] == "EXP_01"
    assert d["experiments"][1]["experiment_id"] == "EXP_02"

    # 3. Runs inside EXP_01 should be sorted by run_id: RUN_A, RUN_B
    assert d["experiments"][0]["runs"][0]["run_id"] == "RUN_A"
    assert d["experiments"][0]["runs"][1]["run_id"] == "RUN_B"

    # 4. JSON serialization deterministic output
    json_str = session.serialize()
    loaded = json.loads(json_str)
    assert loaded["experiments"][0]["experiment_id"] == "EXP_01"
    assert loaded["experiments"][0]["runs"][0]["run_id"] == "RUN_A"
